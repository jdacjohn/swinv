#!/usr/bin/perl -T
# $Id: cats_admin.cgi,v 1.19 2006/02/02 12:13:46 jarnold Exp $
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
#show_error("Mode = " . $F{mode});
my %modes = (
	add=>\&do_add,
	add_subcat=>\&do_add_subcat,
	view=>\&do_view,
	modify=>\&do_modify,
	modify_subcat=>\&do_modify_subcat,
	delete=>\&do_delete,
	delete_subcat=>\&do_delete_subcat,
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
	my $template = $C->tmpl('admin_categories');
	print $Q->header(-type=>'text/html');
	print $template->output();
}

sub do_add {
	unless($ENV{'REQUEST_METHOD'} eq 'POST') {
		show_add();
	}
	else {
		my %error = ();
		unless(vrfy_string(\$F{'heading'})) {
			$error{heading_error} = "Either you didn't enter a category heading or it contained invalid characters";
		}
		unless(vrfy_string(\$F{'cat_name'})) {
			$error{name_error} = "Either you didn't enter the full category name or it contained invalid characters";
		}

		if(%error) {
			$error{'heading'} = $F{'heading'};
			$error{'cat_name'} = $F{'cat_name'};
			show_add(\%error);
		}
		else {
			my $query = "insert into category (heading,name) values (?,?)";
	    $sth = $C->db_query($query,[$F{'heading'},$F{'cat_name'}]);
			$sth->finish();

			show_success("Category $F{'heading'} has been added successfully.");
		}
	}
}

sub do_add_subcat {
	die "No cat_id passed to do_add_subcat()!" unless $F{'cat_id'};
	
	unless($ENV{'REQUEST_METHOD'} eq 'POST') {
		show_add_subcat();
	}
	else {
		my %error = ();
		unless(vrfy_string(\$F{'heading'})) {
			$error{heading_error} = "Either you didn't enter a subcategory heading or it contained invalid characters";
		}
		unless(vrfy_string(\$F{'subcat_name'})) {
			$error{name_error} = "Either you didn't enter the full subcategory name or it contained invalid characters";
		}

		if(%error) {
			$error{'heading'} = $F{'heading'};
			$error{'subcat_name'} = $F{'subcat_name'};
			show_add_subcat(\%error);
		}
		else {
			my $query = "insert into subcategory (heading,name,category_id) values (?,?,?)";
	    $sth = $C->db_query($query,[$F{'heading'},$F{'subcat_name'},$F{'cat_id'}]);
			$sth->finish();

			show_success("Subcategory <b>$F{'heading'}</b> has been successfully added to SIMS.");
		}
	}
}

sub do_view {
	my $query1 = "SELECT COUNT(*) FROM category";
	my @dbp = ();

	$sth = $C->db_query($query1,\@dbp);
	my $numrows = $sth->fetchrow;

	my $numpages = int($numrows / $C->rpp_categories());
	if($numrows % $C->rpp_categories()) {
		$numpages ++;
	}
	$sth->finish;

	my $query = "select id,heading,name from category order by heading";
	my $start = $F{'s'} || 0; # s = starting row
	$query .= " LIMIT $start, " . $C->rpp_categories();

	$sth = $C->db_query($query,\@dbp);

	my @cats = ();
	while(my $row = $sth->fetchrow_hashref) {
    $row->{cat_id} = $row->{id};
    delete($row->{id});    
		push(@cats,$row);
	}
	$sth->finish;

	my $next = $start + $C->rpp_categories();
	my $prev = $start - $C->rpp_categories();
	# make sure we don't do a previous out of range
	$prev = 0 unless $prev > -1;
	# don't show the previous button unless there are previous items
	my $show_prev = 1 unless $start == 0;
	# don't show next button unless there are more items
	my $show_next = 1 unless $next >= $numrows;
	# page loop
	my @pages = ();
	my $qstring;

	my $pageon = int($start / $C->rpp_categories()) + 1;
	if($pageon < 1) {
		$pageon = 1;
	}
	my $startpage = $pageon - 5;
	if($startpage < 1) {
		$startpage = 1;
	}

	my $endpage = $startpage + $C->rpp_categories() - 1;
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
		push(@pages,{s=>$C->rpp_categories() * $count,page=>$_,tp=>$tp});
		$count ++;
	}
	$sth->finish();
	show_view(\@cats,\$next,\$prev,\$show_next,\$show_prev,\@pages,\$qstring);

}

# ---------------------------------------------------------------------
# Modify an existing subcategory.
# 02/13/2006 - initial version.
# ---------------------------------------------------------------------
sub do_modify_subcat {
	die "No subcat id passed to modify" unless $F{'subcat_id'};

	my $query = "select heading,name from subcategory where id = ?";
	$sth = $C->db_query($query,[$F{'subcat_id'}]);
	my $heading;
	my $subcat_name;
	while(my $row = $sth->fetchrow_hashref) {
	  $heading = $row->{heading};
		$subcat_name = $row->{name};
	}
	$sth->finish;
	
  # show the update screen if the user clicked modify from the view screen
	if(!defined($F{'update'})) {
		show_modify_subcat(\$heading,\$subcat_name);
	}
	else { # updates defined
		die "No subcat id passed to modify" unless $F{'subcat_id'};
		my %error = ();

		unless(vrfy_string(\$F{'heading'})) {
			$error{heading_error} = "Either you didn't enter a category heading or it contained invalid characters";
		}
		unless(vrfy_string(\$F{'subcat_name'})) {
			$error{subcat_name_error} = "Either you didn't enter a subcategory name or it contained invalid characters";
		}

		if(%error) {
			$error{'heading'} = $F{'heading'};
			$error{'subcat_name'} = $F{'subcat_name'};
			show_modify(\%error);
		}
		else { # execute the update

      my $query = "update subcategory set heading=?,name=? where id=?";
			$sth = $C->db_query($query,[$F{'heading'},$F{'subcat_name'},$F{'subcat_id'}]);
			$sth->finish();
			show_success("Subcategory '<b>$F{'heading'}</b>' has been modified");
	  } 
	}
}

# ---------------------------------------------------------------------
# Modify an existing category.
# Pulls information for the category plus all subcategories belonging to the category
# and displays it for modification.
# 02/13/2006 - initial versino
# ---------------------------------------------------------------------
sub do_modify {
	die "No cat id passed to modify" unless $F{'cat_id'};

	my $query = "select heading,name from category where id = ?";
	$sth = $C->db_query($query,[$F{'cat_id'}]);
	my $heading;
	my $cat_name;
	while(my $row = $sth->fetchrow_hashref) {
	  $heading = $row->{heading};
		$cat_name = $row->{name};
	}
	$sth->finish;
	
	$query = "select id,heading,name from subcategory where category_id = ?";
	$sth = $C->db_query($query,[$F{'cat_id'}]);
	my @subcats = ();
	while(my $row = $sth->fetchrow_hashref) {
    $row->{subcat_id} = $row->{id};
		$row->{subcat_heading} = $row->{heading};
		$row->{subcat_name} = $row->{name};
    delete($row->{id});    
		delete($row->{heading});
		delete($row->{name});
		push(@subcats,$row);
	}
	$sth->finish;
	
  # show the update screen if the user clicked modify from the view screen
	if(!defined($F{'update'})) {
		show_modify(\$heading,\$cat_name,\@subcats);
	}
	else { # updates defined
		die "No cat id passed to modify" unless $F{'cat_id'};
		my %error = ();

		unless(vrfy_string(\$F{'heading'})) {
			$error{heading_error} = "Either you didn't enter a category heading or it contained invalid characters";
		}
		unless(vrfy_string(\$F{'cat_name'})) {
			$error{cat_name_error} = "Either you didn't enter a category name or it contained invalid characters";
		}

		if(%error) {
			$error{'heading'} = $F{'heading'};
			$error{'cat_name'} = $F{'cat_name'};
			show_modify(\%error);
		}
		else { # execute the update

      my $query = "update category set heading=?,name=? where id=?";
			$sth = $C->db_query($query,[$F{'heading'},$F{'cat_name'},$F{'cat_id'}]);
			$sth->finish();
			show_success("Category '<b>$F{'heading'}</b>' has been modified");
	  } 
	}
}

sub do_delete_subcat {
	die "No subcat_id passed to do_delete_subcat()!" unless $F{'subcat_id'};

	my $sth = $C->db_query("SELECT heading,name FROM subcategory WHERE id=?",[$F{'subcat_id'}]);
	my ($heading,$subcat_name) = $sth->fetchrow();

	$sth->finish;

	if(!$F{'confirm'}) {
    show_delete_subcat({heading=>$heading,});
	}
  else {
		$sth = $C->db_query("delete from subcategory where id = ?",[$F{'subcat_id'}]);
		$sth->finish();
		show_success("Subcategory: '<b>$heading</b>' has been deleted from SIMS.");
	}
}

sub do_delete {
	die "No cat_id passed to do_delete()!" unless $F{'cat_id'};

	my $sth = $C->db_query("SELECT heading,name FROM category WHERE id=?",[$F{'cat_id'}]);
	my ($heading,$cat_name) = $sth->fetchrow();

	$sth->finish;

	if(!$F{'confirm'}) {
    show_delete({heading=>$heading,});
	}
	else {
		$sth = $C->db_query("delete from category where id = ?",[$F{'cat_id'}]);
		$sth->finish();
		$sth = $C->db_query("delete from subcategory where category_id = ?",[$F{'cat_id'}]);
		$sth->finish();

		show_success("Category: '<b>$heading</b>' and all $heading subcategories have been deleted from SIMS.");
	}
}

sub show_add {
	my $error = shift;

	my $template = $C->tmpl('admin_cats_add');
	$template->param(%$error) if $error;
	print $Q->header(-type=>'text/html');
	print $template->output();
}

sub show_add_subcat {

	my $error = shift;
	die "No cat_id passed to show_add_subcat()!" unless $F{'cat_id'};

	my $template = $C->tmpl('admin_subcats_add');
	$template->param(%$error) if $error;
	$template->param(cat_id=>$F{'cat_id'});
	print $Q->header(-type=>'text/html');
	print $template->output();
}

sub show_modify {
  my ($heading,$cat_name,$list) = @_;
  my $template = $C->tmpl('admin_cats_modify');
	$template->param(heading=>$$heading);
	$template->param(cat_name=>$$cat_name);
	$template->param(cat_id=>$F{'cat_id'});
	$template->param(subcats=>$list); # loop
	print $Q->header(-type=>'text/html');
	print $template->output();
}

sub show_modify_subcat {
  my ($heading,$subcat_name) = @_;
  my $template = $C->tmpl('admin_subcats_modify');
	$template->param(heading=>$$heading);
	$template->param(subcat_name=>$$subcat_name);
	$template->param(subcat_id=>$F{'subcat_id'});
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
	die "No cat_id passed to show_delete()!" unless $F{'cat_id'};

	my $template = $C->tmpl('admin_cats_delete');
	$template->param(cat_id=>$F{'cat_id'});
	$template->param(%$params);
	print $Q->header(-type=>'text/html');
	print $template->output();
}

sub show_delete_subcat {
	my $params = shift;
	die "No subcat_id passed to show_delete_subcat()!" unless $F{'subcat_id'};

	my $template = $C->tmpl('admin_subcats_delete');
	$template->param(subcat_id=>$F{'subcat_id'});
	$template->param(%$params);
	print $Q->header(-type=>'text/html');
	print $template->output();
}

# ---------------------------------------------------------------------
# Display the admin view of all categories
# 02/08/06 - jarnold
# ---------------------------------------------------------------------
sub show_view {
	# all these are refs
	my($list,$next,$prev,$show_next,$show_prev,$pages,$qstring) = @_;

	my $template = $C->tmpl('admin_categories_list');
	$template->param(cats=>$list);	#loop
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
  my $template = $C->tmpl('error_user');
  $template->param(msg=>$msg);
  print $Q->header();
  print $template->output();
  exit;
}
