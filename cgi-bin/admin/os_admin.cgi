#!/usr/bin/perl -T
# $Id: os_admin.cgi,v 1.19 2006/02/02 12:13:46 jarnold Exp $
##
## Copyright (C) 2k3 Technologies, 2006
##
## $Id: Conf.pm,v 1.25 2004/03/22 05:04:44 jarnold Exp $

use strict;
use lib '..';
use CGI::Carp 'fatalsToBrowser'; # for testing
use CGI;
use DBI;
use HTML::Template;
use SWINV::Conf;
use SWINV::Verify;
use URI::Escape;

my $C = new SWINV::Conf;
my $Q = new CGI;
my %F = $Q->Vars();

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
	show_default();
}

sub show_default {
	my $template = $C->tmpl('admin_os');
	print $Q->header(-type=>'text/html');
	print $template->output();
}

sub do_add {
	unless($ENV{'REQUEST_METHOD'} eq 'POST') {
		show_add();
	}
	else {
		my %error = ();
		unless(vrfy_string(\$F{'os_name'})) {
			$error{name_error} = "Either you didn't enter a name for the OS or it contained invalid characters";
		}
		unless(vrfy_string(\$F{'mfr'})) {
			$error{mfr_error} = "Either you didn't enter a manufacturer for the OS or it contained invalid characters";
		}

		if(%error) {
			$error{'os_name'} = $F{'os_name'};
			$error{'mfr'} = $F{'mfr'};
			show_add(\%error);
		}
		else {
			my $query = "insert into os (os_name,os_mfr) VALUES (?,?)";
	    $sth = $C->db_query($query,[$F{'os_name'},$F{'mfr'}]);
			$sth->finish();

			show_success("OS <b>$F{'os_name'}</b> has been successfully added to SIMS.");
		}
	}
}

sub do_view {
	my $query1 = "select count(*) from os";
	my @dbp = ();

	$sth = $C->db_query($query1,\@dbp);
	my $numrows = $sth->fetchrow;

	my $numpages = int($numrows / $C->rpp_os());
	if($numrows % $C->rpp_os()) {
		$numpages ++;
	}
	$sth->finish;

	my $query = "select id,os_name,os_mfr from os order by os_name";
	my $start = $F{'s'} || 0; # s = starting row
	$query .= " LIMIT $start, " . $C->rpp_os();

	$sth = $C->db_query($query,\@dbp);

	my @oss = ();
	while(my $row = $sth->fetchrow_hashref) {
    $row->{os_id} = $row->{id};
    delete($row->{id});    
		push(@oss,$row);
	}
	$sth->finish;

	my $next = $start + $C->rpp_os();
	my $prev = $start - $C->rpp_os();
	# make sure we don't do a previous out of range
	$prev = 0 unless $prev > -1;
	# don't show the previous button unless there are previous items
	my $show_prev = 1 unless $start == 0;
	# don't show next button unless there are more items
	my $show_next = 1 unless $next >= $numrows;
	# page loop
	my @pages = ();
	my $qstring;

	my $pageon = int($start / $C->rpp_os()) + 1;
	if($pageon < 1) {
		$pageon = 1;
	}
	my $startpage = $pageon - 5;
	if($startpage < 1) {
		$startpage = 1;
	}

	my $endpage = $startpage + $C->rpp_os() - 1;
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
		push(@pages,{s=>$C->rpp_os() * $count,page=>$_,tp=>$tp});
		$count ++;
	}
	$sth->finish();
	show_view(\@oss,\$next,\$prev,\$show_next,\$show_prev,\@pages,\$qstring);

}

# ---------------------------------------------------------------------
# Modify an existing OS.
# 02/13/2006 - jarnold
# ---------------------------------------------------------------------
sub do_modify {
	die "No os id passed to modify" unless $F{'os_id'};

	my $query = "select os_name,os_mfr from os where id = ?";
	$sth = $C->db_query($query,[$F{'os_id'}]);
	my $os_info = $sth->fetchrow_hashref;
	$sth->finish;

  # show the update screen if the user clicked modify from the view screen
	if(!defined($F{'update'})) {
		show_modify($os_info);
	}
	else { # updates defined
		die "No os id passed to modify" unless $F{'os_id'};
		my %error = ();

		unless(vrfy_string(\$F{'os_name'})) {
			$error{name_error} = "Either you didn't enter a name for the operating system or it contained invalid characters";
		}
		unless(vrfy_string(\$F{'os_mfr'})) {
			$error{mfr_error} = "Either you didn't enter a manufacturer for the operating system or it contained invalid characters";
		}

		if(%error) {
			$error{'os_name'} = $F{'os_name'};
			$error{'os_mfr'} = $F{'os_mfr'};
			show_modify(\%error);
		}
		else { # execute the update
      my $query = "update os set os_name=?,os_mfr=? where id=?";
			$sth = $C->db_query($query,[$F{'os_name'},$F{'os_mfr'},$F{'os_id'}]);
			$sth->finish();
			show_success("OS '<b>$F{'os_name'}</b>' has been modified.");
	  }
	}
}

sub do_delete {
	die "No os_id passed to do_delete()!" unless $F{'os_id'};

	my $sth = $C->db_query("select os_name from os where id=?",[$F{'os_id'}]);
	my $os_name = $sth->fetchrow();
	$sth->finish;

	if(!$F{'confirm'}) {
    show_delete({os_name=>$os_name});
	}
	else {
		$sth = $C->db_query("delete from os where id = ?",[$F{'os_id'}]);
		$sth->finish();
		show_success("OS '<b>$os_name</b>' has been deleted from SIMS.");
	}
}

sub show_add {
	my $error = shift;

	my $template = $C->tmpl('admin_os_add');
	$template->param(%$error) if $error;
	print $Q->header(-type=>'text/html');
	print $template->output();
}

sub show_modify {
	my $params = shift;
  my $template = $C->tmpl('admin_os_modify');
	$template->param(%$params) if $params;
  $template->param(os_id=>$F{'os_id'});
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
	die "No os_id passed to show_delete()!" unless $F{'os_id'};

	my $template = $C->tmpl('admin_os_delete');
	$template->param(os_id=>$F{'os_id'});
	$template->param(%$params);
	print $Q->header(-type=>'text/html');
	print $template->output();
}

# ---------------------------------------------------------------------
# Display the admin view of all oss
# 02/08/06 - jarnold
# ---------------------------------------------------------------------
sub show_view {
	# all these are refs
	my($list,$next,$prev,$show_next,$show_prev,$pages,$qstring) = @_;

	my $template = $C->tmpl('admin_os_list');
	$template->param(oss=>$list);	#loop
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
