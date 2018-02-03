#!/usr/bin/perl -T
# $Id: volumes_admin.cgi,v 1.19 2006/02/02 12:13:46 jarnold Exp $
##
## Copyright (C) 2k3 Technologies, 2006
##
## $Id: Conf.pm,v 1.25 2004/03/22 05:04:44 jarnold Exp $

use strict;
use lib '..';
use CGI::Carp 'fatalsToBrowser'; # for testing
use CGI;
use CGI::Session;
use DBI;
use HTML::Template;
use SWINV::Conf;
use SWINV::Verify;
use URI::Escape;

my $C = new SWINV::Conf;
my $Q = new CGI;
my %F = $Q->Vars();
my $session = new CGI::Session(undef, $Q, {Directory=>'/usr/local/Apache2/tmp'});

$C->encode_html(\%F);

my $sth;
my $size_x;
my $size_y;

my %modes = (
	add=>\&do_add,
	view=>\&do_view,
	modify=>\&do_modify,
	delete=>\&do_delete,
	cancelmod=>\&do_cancelmod,
	default=>\&do_default
);

if(defined($F{mode}) && exists($modes{$F{mode}})) {
	$modes{$F{mode}}->();
}
else {
	$modes{'default'}->();
}

$SWINV::Conf::DBH->disconnect() if $SWINV::Conf::DBH;
exit;

#############################################################
# Subroutines
#############################################################

sub do_default {
	if ($session->param("~logged_in")) {
		show_default();
	} else {
	  show_login();
	}
}

sub show_default {
	my $template = $C->tmpl('admin_volumes');
	print $Q->header(-type=>'text/html');
	print $template->output();
}

sub show_login {
	my $template = $C->tmpl('login');
	print $Q->header(-type=>'text/html');
	print $template->output();
}

sub do_add {
	unless($ENV{'REQUEST_METHOD'} eq 'POST') {
		show_add();
	}
	else {
		my %error = ();
		unless(vrfy_string(\$F{'vol_desc'})) {
			$error{vol_desc_error} = "Either you didn't enter a description for the binder or it contained invalid characters";
		}
		unless(vrfy_int(\$F{'sheets'})) {
			$error{sheets_error} = "You must enter a value for the number of sheets in the binder";
		}
		unless(vrfy_int(\$F{'slots'})) {
			$error{slots_error} = "You must enter a value for the number of slots per sheet";
		}

		unless(vrfy_int(\$F{'pouches'})) {
			$error{pouches_error} = "You must enter a value for the number of pouches (if any) in the binder.  If none, enter 0";
		}

		if(%error) {
    	$error{'vol_desc'} = $F{'vol_desc'};
			$error{'sheets'} = $F{'sheets'};
			$error{'slots'} = $F{'slots'};
			$error{'pouches'} = $F{'pouches'};
			show_add(\%error);
		}
		else {

      my $query = "insert into volumes (vol_desc,sheets,slots,pouches) VALUES (?,?,?,?)";
	    $sth = $C->db_query($query,[$F{'vol_desc'},$F{'sheets'},$F{'slots'},$F{'pouches'}]);
			$sth->finish();

			show_success("Volume: $F{'vol_desc'} has been added successfully.");
		}
	}
}

sub do_view {
	my $query1 = "SELECT COUNT(*) FROM volumes";
	my @dbp = ();

	$sth = $C->db_query($query1,\@dbp);
	my $numrows = $sth->fetchrow;

	my $numpages = int($numrows / $C->rpp_volumes());
	if($numrows % $C->rpp_volumes()) {
		$numpages ++;
	}
	$sth->finish;

	my $query = "select id,vol_desc,sheets,slots,pouches from volumes";
	my $start = $F{'s'} || 0; # s = starting row
	$query .= " LIMIT $start, " . $C->rpp_volumes();

	$sth = $C->db_query($query,\@dbp);

	my @volumes = ();
	while(my $row = $sth->fetchrow_hashref) {
    $row->{vol_id} = $row->{id};
    delete($row->{id});    
		push(@volumes,$row);
	}
	$sth->finish;

	my $next = $start + $C->rpp_volumes();
	my $prev = $start - $C->rpp_volumes();
	# make sure we don't do a previous out of range
	$prev = 0 unless $prev > -1;
	# don't show the previous button unless there are previous items
	my $show_prev = 1 unless $start == 0;
	# don't show next button unless there are more items
	my $show_next = 1 unless $next >= $numrows;
	# page loop
	my @pages = ();
	my $qstring;

	my $pageon = int($start / $C->rpp_volumes()) + 1;
	if($pageon < 1) {
		$pageon = 1;
	}
	my $startpage = $pageon - 5;
	if($startpage < 1) {
		$startpage = 1;
	}

	my $endpage = $startpage + $C->rpp_volumes() - 1;
	if($endpage > $numpages) {
		$startpage = $startpage - ($endpage - $numpages);
		$endpage = $numpages;
	}
	if($startpage < 1) { $startpage = 1; }
	my $count = $startpage - 1;

	foreach($startpage .. $endpage) {
		my $tp = 0;
		if($_ eq $pageon) {
			$tp = 1;
		}
		push(@pages,{s=>$C->rpp_volumes() * $count,page=>$_,tp=>$tp});
		$count ++;
	}
	$sth->finish();
	show_view(\@volumes,\$next,\$prev,\$show_next,\$show_prev,\@pages,\$qstring);

}

# ---------------------------------------------------------------------
# Modify an existing volume.
# 02/12/2006 - jarnold
# ---------------------------------------------------------------------
sub do_modify {
	die "No volume id passed to modify" unless $F{'vol_id'};

	my $query = "select id,vol_desc,sheets,slots,pouches from volumes where id = ?";
	$sth = $C->db_query($query,[$F{'vol_id'}]);
	my $vol_info = $sth->fetchrow_hashref;
	$vol_info->{vol_id} = $vol_info->{id};
	delete($vol_info->{id});
	$sth->finish;
  # show the update screen if the user clicked modify from the view screen
	if(!defined($F{'update'})) {
		show_modify($vol_info);
	}
	else { # updates defined
		die "No volume id passed to modify" unless $F{'vol_id'};
		my %error = ();

		unless(vrfy_string(\$F{'vol_desc'})) {
			$error{vol_desc_error} = "Either you didn't enter a description for the binder or it contained invalid characters";
		}
		unless(vrfy_int(\$F{'sheets'})) {
			$error{sheets_error} = "You must enter a value for the number of sheets in the binder";
		}
		unless(vrfy_int(\$F{'slots'})) {
			$error{slots_error} = "You must enter a value for the number of slots per sheet";
		}

		unless(vrfy_int(\$F{'pouches'})) {
			$error{pouches_error} = "You must enter a value for the number of pouches (if any) in the binder.  If none, enter 0";
		}

		if(%error) {
    	$error{'vol_desc'} = $F{'vol_desc'};
			$error{'sheets'} = $F{'sheets'};
			$error{'slots'} = $F{'slots'};
			$error{'pouches'} = $F{'pouches'};
			show_add(\%error);
		}
		else { # execute the update
      my $query = "update volumes set vol_desc=?,sheets=?,slots=?,pouches=? where id=?";
			$sth = $C->db_query($query,[$F{'vol_desc'},$F{'sheets'},$F{'slots'},$F{'pouches'},$F{'vol_id'}]);
			$sth->finish();
			show_success("'$F{'vol_desc'}' has been modified");
	  } 
	} # end updates defined
}

sub do_delete {
	die "No vol_id passed to do_delete()!" unless $F{'vol_id'};

	my $sth = $C->db_query("select vol_desc from volumes where id=?",[$F{'vol_id'}]);
	my $vol_desc = $sth->fetchrow();

	$sth->finish;

	if(!$F{'confirm'}) {
    show_delete({vol_desc=>$vol_desc});
	}
	else {
		$sth = $C->db_query("delete from volumes where id = ?",[$F{'vol_id'}]);
		$sth->finish();

		show_success("Volume: '$vol_desc' has been deleted");
	}
}

sub show_add {
	my $error = shift;

	my $template = $C->tmpl('admin_volumes_add');
	$template->param(%$error) if $error;
	print $Q->header(-type=>'text/html');
	print $template->output();
}

sub show_modify {
	my $params = shift;
  my $template = $C->tmpl('admin_volumes_modify');
	$template->param(%$params) if $params;
	print $Q->header(-type=>'text/html');
	print $template->output();
}

sub show_confirm_modify {
	my ($params,$warnings) = @_;
	delete($params->{update});
	my $template = $C->tmpl('admin_library_confirm_modify');
	$template->param(%$params);
	$template->param(warnings=>$warnings);

	print $Q->header();
	print $template->output();
}

sub show_delete {
	my $params = shift;
	die "No vol_id passed to show_delete()!" unless $F{'vol_id'};

	my $template = $C->tmpl('admin_volumes_delete');
	$template->param(vol_id=>$F{'vol_id'});
	$template->param(%$params);
	print $Q->header(-type=>'text/html');
	print $template->output();
}

# ---------------------------------------------------------------------
# Display the admin view of all volumes
# 02/08/06 - jarnold
# ---------------------------------------------------------------------
sub show_view {
	# all these are refs
	my($list,$next,$prev,$show_next,$show_prev,$pages,$qstring) = @_;

	my $template = $C->tmpl('admin_volumes_list');
	$template->param(volumes=>$list);	#loop
	#$template->param(pulldown=>$pulldown); #loop
	$template->param('next'=>$$next);
	$template->param(prev=>$$prev);
	$template->param(show_next=>$$show_next);
	$template->param(show_prev=>$$show_prev);
	$template->param(pages=>$pages); #loop
	$template->param(qstring=>$$qstring);

	print $Q->header(-type=>'text/html');
	print $template->output();
}

sub show_success {
	my $msg = shift;
	my $template = $C->tmpl('admin_success');
	$template->param(msg=>$msg);
	print $Q->header(-type=>'text/html');
	print $template->output;
}

##
sub show_error {
  my $msg = shift;
  my $template = $C->tmpl('admin_error_user');
  $template->param(msg=>$msg);
  print $Q->header();
  print $template->output();
  exit;
}
