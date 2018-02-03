#! /usr/bin/perl -T
##
# browse_titles.cgi - Provide public-side functionality for browsing/viewing system titles.
#
# $Author: Jarnold $
# $Date: 5/10/06 9:20p $
# $Revision: 1 $
##

use strict;
use lib '.';
use CGI::Carp qw(fatalsToBrowser); #for testing
use CGI;
use DBI;
use Date::Calc qw(Today_and_Now);
use HTML::Template;
use SWINV::Conf;
use SWINV::Verify;
use URI::Escape;

my $C = new SWINV::Conf;
my $Q = new CGI;
my %F = $Q->Vars();

our $DEBUG = 1;
our $DEBUG_INIT = 0;

$C->encode_html(\%F);

# pagination vars
my $sth;
my $next;
my $prev;
my $show_next;
my $show_prev;
my @pages = ();

my %modes = (
	cat     =>\&do_cat,
	os      =>\&do_os,
	vendor  =>\&do_ven,
	alp     =>\&do_alp,
  view    =>\&do_view,
	default =>\&do_default
);

#show_error("Mode = $F{mode}");
if(defined($F{mode}) && exists($modes{$F{mode}})) {
	$modes{$F{mode}}->();
}
else {
	$modes{'default'}->();
}

$SWINV::Conf::DBH->disconnect() if $SWINV::Conf::DBH;
exit;

# Entry Points
###############################################################################
#  Set up the browse by category page
#
# Change History:
# 03.14.2006 - Initial Version - jarnold
###############################################################################
sub do_cat {
  # get the array of categories to use on the page
  my @cats = getCatList($F{'cat'});
  my @titles = ();
  if ($F{'cat'}) {
    @titles = getTitlesByCat($F{'cat'});
    show_cats(\@cats,\@titles,\$next,\$prev,\$show_next,\$show_prev,\@pages);
  } else {
    show_cats(\@cats,\@titles);
  }
}

###############################################################################
#  Set up the browse alphabetica page
#
# Change History:
# 03.15.2006 - Initial Version - jarnold
###############################################################################
sub do_alp {
  # get the array of letters to use on the page
  my @letters = getAlphaList();
  my @titles = ();
  if ($F{'alp'}) {
    @titles = getTitlesAlpha($F{'alp'});
    show_alp(\@letters,\@titles,\$next,\$prev,\$show_next,\$show_prev,\@pages);
  } else {
    show_alp(\@letters,\@titles);
  }
}

###############################################################################
#  Set up the browse by os page
#
# Change History:
# 03.15.2006 - Initial Version - jarnold
###############################################################################
sub do_os {
  # get the array of categories to use on the page
  my @oss = getOSList($F{'os'});
  my @titles = ();
  if ($F{'os'}) {
    @titles = getTitlesByOS($F{'os'});
    show_oss(\@oss,\@titles,\$next,\$prev,\$show_next,\$show_prev,\@pages);
  } else {
    show_oss(\@oss,\@titles);
  }
}

###############################################################################
#  Set up the browse by vendor page
#
# Change History:
# 03.15.2006 - Initial Version - jarnold
###############################################################################
sub do_ven {
  # get the array of categories to use on the page
  my @vendors = getVendorList($F{'vendor'});
  my @titles = ();
  if ($F{'vendor'}) {
    @titles = getTitlesByMfr($F{'vendor'});
    show_vendors(\@vendors,\@titles,\$next,\$prev,\$show_next,\$show_prev,\@pages);
  } else {
    show_vendors(\@vendors,\@titles);
  }
}

# ---------------------------------------------------------------------
# View the details for a title.
# ---------------------------------------------------------------------
sub do_view {
	die "No title id passed to modify" unless $F{'title_id'};
	
	my %params = ();
	my $query = 'select subcategory_id,category_id,title,mfr,version,os1,os2,os3,os4,os5,os6,os7,os8 from software where id = ?';
	$sth = $C->db_query($query,[$F{'title_id'}]);
	my ($subcat,$cat,$title,$mfr,$version,$os1,$os2,$os3,$os4,$os5,$os6,$os7,$os8) = $sth->fetchrow();
	$sth->finish;
	
	$params{'title'} = $title;
  $params{'mfr'} = $mfr;
	$params{'version'} = $version;
	my @os_ids = ($os1,$os2,$os3,$os4,$os5,$os6,$os7,$os8);
	my %os_hash = ();
	my $count = 1;
	foreach my $id (@os_ids) {
		if ($id) {%os_hash->{$count} = $id; $count++ }
	}

	$query = 'select username,base_license_key,base_access_key,ext_license_key,ext_access_key,udef_field_val,udef_field_name from license where software_id = ?';
	$sth = $C->db_query($query,[$F{'title_id'}]);
	my ($uname,$blicense,$baccess,$elicense,$eaccess,$udef1,$udef2) = $sth->fetchrow();
	$sth->finish();
	$params{'uname'} = $uname;
	$params{'blicense'} = $blicense;
	$params{'baccess'} = $baccess;
	$params{'elicense'} = $elicense;
	$params{'eaccess'} = $eaccess;
	$params{'udef1'} = $udef1;
	$params{'udef2'} = $udef2;
	
	$query = 'select volume_id,sheet,slot,pouch from location where software_id = ?';
	$sth = $C->db_query($query,[$F{'title_id'}]);
	my ($vol_id,$sheet,$slot,$pouch) = $sth->fetchrow();
	my $vol_desc;
	$sth->finish();
	if ($sheet) {
		$params{'cur_sheet'} = $sheet;
	} else {
		$params{'cur_sheet'} = '-';
	}
	if ($slot) {
		$params{'cur_slot'} = $slot;
	} else {
		$params{'cur_slot'} = '-';
	}
	if ($pouch) {
		$params{'cur_pouch'} = $pouch;
	} else {
		$params{'cur_pouch'} = '-';
	}
	if ($vol_id) {
		$query = 'select vol_desc from volumes where id = ?';
		$sth = $C->db_query($query,[$vol_id]);
		$params{'cur_vol'} = $sth->fetchrow();
		$params{'vol_id'} = $vol_id;
	} else {
		$params{'cur_vol'} = '-';
	}
  if ($F{'print'}) {
    show_print(\%params,\$subcat,\$cat,\%os_hash);
  } else {
    show_view(\%params,\$subcat,\$cat,\%os_hash);
  }
}

# Subroutines
#------------------------------------------------------------------------------
# Show the detail view of the title
#
# Change History:
# 03.14.2006 - Initial Version - jarnold
#------------------------------------------------------------------------------
sub show_view {
  my ($params,$subcat,$cat,$os_hash) = @_;
	#&debug("Cat = " . $$cat . "  Subcat = " . $$subcat);

  my $template = $C->tmpl('titles_view');
	$template->param(%$params) if $params;
	my @oss = build_os_list(\%$os_hash);
	$template->param(oss=>\@oss);
	$template->param(cat=>getCatName($$cat));
	$template->param(subcat=>getSubcatName($$subcat));
  $template->param(ret_id=>$F{'ret_id'});
  $template->param(title_id=>$F{'title_id'});
  $template->param(mode=>$F{'lastmode'});
	print $Q->header(-type=>'text/html');
	print $template->output();
}

###############################################################################
# Show the print detail view of the title
#
# Change History:
# 03.14.2006 - Initial Version - jarnold
###############################################################################
sub show_print {
  my ($params,$subcat,$cat,$os_hash) = @_;
	#&debug("Cat = " . $$cat . "  Subcat = " . $$subcat);
  my ($year,$month,$day,$hours,$mins,$secs) = Today_and_Now();
  
  my $template = $C->tmpl('titles_view_print');
	$template->param(%$params) if $params;
	my @oss = build_os_list(\%$os_hash);
	$template->param(oss=>\@oss);
	$template->param(cat=>getCatName($$cat));
	$template->param(subcat=>getSubcatName($$subcat));
  $template->param(ret_id=>$F{'ret_id'});
  $template->param(mode=>$F{'lastmode'});
	$template->param(datetime=>($month . '-' . $day . '-' . $year . ' ' . $hours . ':' . $mins . ':' . $secs));
  print $Q->header(-type=>'text/html');
	print $template->output();
}

###############################################################################
# Show the browse alphabetically page
#
# Change History:
# 03.15.2006 - Initial Version - jarnold
###############################################################################
sub show_alp {
  my ($lets,$titles,$next,$prev,$show_next,$show_prev,$pages) = @_;
  my $template = $C->tmpl('titles_alp');
  if ($F{'alp'}) {
    $template->param(lastalp=>$F{'alp'});
  }
  $template->param(lets=>$lets);
  $template->param(titles=>$titles);	# titles loop
	$template->param(next=>$$next) unless !$next;
	$template->param(prev=>$$prev) unless !$prev;
	$template->param(show_next=>$$show_next) unless !$show_next;
	$template->param(show_prev=>$$show_prev) unless !$show_prev;
	$template->param(pages=>$pages) unless !$pages; # page anchors loop
  
	print $Q->header(-type=>'text/html');
	print $template->output();

}

###############################################################################
# Show the browse by os page
#
# Change History:
# 03.15.2006 - Initial Version - jarnold
###############################################################################
sub show_oss {
  my ($oss,$titles,$next,$prev,$show_next,$show_prev,$pages) = @_;
  my $template = $C->tmpl('titles_os');
  if ($F{'os'}) {
    $template->param(lastos=>$F{'os'});
  }
  $template->param(oss=>$oss);
  $template->param(titles=>$titles);	# titles loop
	$template->param(next=>$$next) unless !$next;
	$template->param(prev=>$$prev) unless !$prev;
	$template->param(show_next=>$$show_next) unless !$show_next;
	$template->param(show_prev=>$$show_prev) unless !$show_prev;
	$template->param(pages=>$pages) unless !$pages; # page anchors loop
  
	print $Q->header(-type=>'text/html');
	print $template->output();

}

###############################################################################
# Show the browse by category page
#
# Change History:
# 03.14.2006 - Initial Version - jarnold
###############################################################################
sub show_cats {
  my ($cats,$titles,$next,$prev,$show_next,$show_prev,$pages) = @_;
  my $template = $C->tmpl('titles_cat');
  if ($F{'cat'}) {
    $template->param(lastcat=>$F{'cat'});
  }
  $template->param(categories=>$cats);
  $template->param(titles=>$titles);	# titles loop
	$template->param(next=>$$next) unless !$next;
	$template->param(prev=>$$prev) unless !$prev;
	$template->param(show_next=>$$show_next) unless !$show_next;
	$template->param(show_prev=>$$show_prev) unless !$show_prev;
	$template->param(pages=>$pages) unless !$pages; # page anchors loop
	print $Q->header(-type=>'text/html');
	print $template->output();

}
###############################################################################
# Show the browse by vendor  page
#
# Change History:
# 03.15.2006 - Initial Version - jarnold
###############################################################################
sub show_vendors {
  my ($vendors,$titles,$next,$prev,$show_next,$show_prev,$pages) = @_;
  my $template = $C->tmpl('titles_vendor');
  if ($F{'vendor'}) {
    $template->param(lastmfr=>$F{'vendor'});
  }
  $template->param(vendors=>$vendors);
  $template->param(titles=>$titles);	# titles loop
	$template->param(next=>$$next) unless !$next;
	$template->param(prev=>$$prev) unless !$prev;
	$template->param(show_next=>$$show_next) unless !$show_next;
	$template->param(show_prev=>$$show_prev) unless !$show_prev;
	$template->param(pages=>$pages) unless !$pages; # page anchors loop
	print $Q->header(-type=>'text/html');
	print $template->output();
}

###############################################################################
# Return an array of os names associated with the title
#
# Change History:
# 03.14.2006 - Initial Version - jarnold
###############################################################################
sub build_os_list {
	my $osids = shift;
	my @oss = ();
	my $query_os = 'select id,os_name from os order by os_name';
	$sth = $C->db_query($query_os,[]);
	while (my $row = $sth->fetchrow_hashref()) {
		while ((my $k, my $v) = each(%$osids)) {
		#&debug("Os Index = " . $k . "  My Os Id = " . $v . "<br>");
			if ($row->{id} eq $v) {
			#&debug("We Have a match.<br>");
        delete($row->{id});
			  push(@oss,$row);
			}
		}
	}
	return @oss;	
}

###############################################################################
# Pull the oss from the database and return them in an array
#
# Change History:
# 03.15.2006 - Initial Version - jarnold
###############################################################################
sub getOSList {
  my $os_id = shift;
  my $query = 'select id,os_name from os order by os_name';
  my @dbps = ();
  my @oss = ();
  
  $sth = $C->db_query($query,\@dbps);
  while (my $row = $sth->fetchrow_hashref()) {
    if ($os_id && ($os_id eq $row->{id})) {
      $row->{on} = 1;
    }
    $row->{os_id} = $row->{id};
    delete($row->{id});
    push(@oss,$row);
  }
  return @oss;
}

###############################################################################
# Pull the categories from the database and return them in an array
#
# Change History:
# 03.14.2006 - Initial Version - jarnold
###############################################################################
sub getCatList {
  my $cat_id = shift;
  my $query = 'select id,name from category order by name';
  my @dbps = ();
  my @cats = ();
  
  $sth = $C->db_query($query,\@dbps);
  while (my $row = $sth->fetchrow_hashref()) {
    if ($cat_id && ($cat_id eq $row->{id})) {
      $row->{on} = 1;
    }
    $row->{cat_id} = $row->{id};
    $row->{cat_name} = $row->{name};
    delete($row->{id});
    delete($row->{name});
    push(@cats,$row);
  }
  return @cats;
}

###############################################################################
# Pull the alpha letters that are represented in the db from the database and return them in an array
#
# Change History:
# 03.15.2006 - Initial Version - jarnold
###############################################################################
sub getAlphaList {
  my @ iddlets = ();
  my @letters = ('A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z');
  foreach (@letters) {
    my $query = 'select count(*) from software where upper(title) like ?';
    my $dbarg = $_ . '%';
    $sth = $C->db_query($query,[$dbarg]);
    my $row = $sth->fetchrow_hashref();
    $row ->{let} = $_;
    if ($row->{'count(*)'} > 0) {
      $row->{active} = 1;
    }
    delete($row->{'count(*)'});
    push(@iddlets,$row);
  }
  return @iddlets;
}

###############################################################################
# Reurn the vendors from the database
#
# Change History:
# 03.15.2006 - Initial Version - jarnold
###############################################################################
sub getVendorList {
  my $ven = shift;
  my $query = 'select distinct(mfr) from software order by mfr';
  my @dbps = ();
  my @mfrs = ();
  
  $sth = $C->db_query($query,\@dbps);
  while (my $row = $sth->fetchrow_hashref()) {
    if ($ven && ($ven eq $row->{mfr})) {
      $row->{on} = 1;
    }
    push(@mfrs,$row);
  }
  return @mfrs;
}

###############################################################################
# Pull the category name for the cat_id
#
# Change History:
# 03.14.2006 - Initial Version - jarnold
###############################################################################
sub getCatName {
  my $cat_id = shift;
  my $query = 'select name from category where id = ?';
  $sth = $C->db_query($query,[$cat_id]);
  my $catname = $sth->fetchrow();
  return $catname;
}

###############################################################################
# Pull the subcategory name for the subcat_id
#
# Change History:
# 03.14.2006 - Initial Version - jarnold
###############################################################################
sub getSubcatName {
  my $subcat_id = shift;
  my $query = 'select name from subcategory where id = ?';
  $sth = $C->db_query($query,[$subcat_id]);
  my $subcatname = $sth->fetchrow();
  return $subcatname;
}

###############################################################################
# Pull the titles belonging to the category
#
# Change History:
# 03.14.2006 - Initial Version - jarnold
###############################################################################
sub getTitlesByCat {
  my $cat_id = shift;
  die "No cat_id passed to getTitlesByCat!" unless $cat_id;
  
	my $query = "select count(*) from software where category_id = ?";
  $sth = $C->db_query($query,[$cat_id]);
	my $numrows = $sth->fetchrow;
  #&debug("Num Rows = " . $numrows . "<br />");
  
	my $numpages = int($numrows / $C->rpp_titles());
	if($numrows % $C->rpp_titles()) {
		$numpages ++;
	}
	$sth->finish;

	my $start = $F{'s'} || 0; # s = starting row
	$query = "select id,title,mfr,version from software where category_id = ? order by title";

  $query .= " LIMIT $start, " . $C->rpp_titles();
  $sth = $C->db_query($query,[$cat_id]);
  
	my @titles = ();
	while(my $row = $sth->fetchrow_hashref) {
    $row->{title_id} = $row->{id};
    delete($row->{id});
    $row->{cat_id} = $cat_id;
		push(@titles,$row);
	}
	$sth->finish;

  $next = $start + $C->rpp_titles();
	$prev = $start - $C->rpp_titles();
	# make sure we don't do a previous out of range
	$prev = 0 unless $prev > -1;
	# don't show the previous button unless there are previous items
	$show_prev = 1 unless $start == 0;
	# don't show next button unless there are more items
	$show_next = 1 unless $next >= $numrows;
	# page loop
	@pages = ();

	my $pageon = int($start / $C->rpp_titles()) + 1;
	if($pageon < 1) {
		$pageon = 1;
	}
	my $startpage = $pageon - 5;
	if($startpage < 1) {
		$startpage = 1;
	}

	my $endpage = $startpage + $C->rpp_titles() - 1;
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
		push(@pages,{s=>$C->rpp_titles() * $count,page=>$_,tp=>$tp,lastcat=>$F{'cat'}});
		$count ++;
	}
	$sth->finish();
  #&debug("next = " . $next . "<br />");
  #&debug("prev = " . $prev . "<br />");
  #&debug("show_next = " . $show_next . "<br />");
  #&debug("show_prev = " . $show_prev . "<br />");
  
  return @titles;  
}

###############################################################################
# Pull the titles starting with the given letter
#
# Change History:
# 03.15.2006 - Initial Version - jarnold
###############################################################################
sub getTitlesAlpha {
  my $alpha = shift;
  die "No search criteria passed to getTitlesAlpha!" unless $alpha;
  
	my $query = "select count(*) from software where upper(title) like ?";
  $sth = $C->db_query($query,[$alpha . '%']);
	my $numrows = $sth->fetchrow;
  #&debug("Num Rows = " . $numrows . "<br />");
  
	my $numpages = int($numrows / $C->rpp_titles());
	if($numrows % $C->rpp_titles()) {
		$numpages ++;
	}
	$sth->finish;

	my $start = $F{'s'} || 0; # s = starting row
	$query = "select id,title,mfr,version from software where title like ? order by title";

  $query .= " LIMIT $start, " . $C->rpp_titles();
  $sth = $C->db_query($query,[$alpha . '%']);
  
	my @titles = ();
	while(my $row = $sth->fetchrow_hashref) {
    $row->{title_id} = $row->{id};
    delete($row->{id});
    $row->{alp} = $alpha;
		push(@titles,$row);
	}
	$sth->finish;

  $next = $start + $C->rpp_titles();
	$prev = $start - $C->rpp_titles();
	# make sure we don't do a previous out of range
	$prev = 0 unless $prev > -1;
	# don't show the previous button unless there are previous items
	$show_prev = 1 unless $start == 0;
	# don't show next button unless there are more items
	$show_next = 1 unless $next >= $numrows;
	# page loop
	@pages = ();

	my $pageon = int($start / $C->rpp_titles()) + 1;
	if($pageon < 1) {
		$pageon = 1;
	}
	my $startpage = $pageon - 5;
	if($startpage < 1) {
		$startpage = 1;
	}

	my $endpage = $startpage + $C->rpp_titles() - 1;
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
		push(@pages,{s=>$C->rpp_titles() * $count,page=>$_,tp=>$tp,lastalp=>$alpha});
		$count ++;
	}
	$sth->finish();
  #&debug("next = " . $next . "<br />");
  #&debug("prev = " . $prev . "<br />");
  #&debug("show_next = " . $show_next . "<br />");
  #&debug("show_prev = " . $show_prev . "<br />");
  
  return @titles;  
}

###############################################################################
# Pull the titles belonging to the vendor
#
# Change History:
# 03.15.2006 - Initial Version - jarnold
###############################################################################
sub getTitlesByMfr {
  my $mfr = shift;
  die "No vendor passed to getTitlesByMfr!" unless $mfr;
  
	my $query = "select count(*) from software where mfr = ?";
  $sth = $C->db_query($query,[$mfr]);
	my $numrows = $sth->fetchrow;
  #&debug("Num Rows = " . $numrows . "<br />");
  
	my $numpages = int($numrows / $C->rpp_titles());
	if($numrows % $C->rpp_titles()) {
		$numpages ++;
	}
	$sth->finish;

	my $start = $F{'s'} || 0; # s = starting row
	$query = "select id,title,mfr,version from software where mfr = ? order by title";

  $query .= " LIMIT $start, " . $C->rpp_titles();
  $sth = $C->db_query($query,[$mfr]);
  
	my @titles = ();
	while(my $row = $sth->fetchrow_hashref) {
    $row->{title_id} = $row->{id};
    delete($row->{id});
		push(@titles,$row);
	}
	$sth->finish;

  $next = $start + $C->rpp_titles();
	$prev = $start - $C->rpp_titles();
	# make sure we don't do a previous out of range
	$prev = 0 unless $prev > -1;
	# don't show the previous button unless there are previous items
	$show_prev = 1 unless $start == 0;
	# don't show next button unless there are more items
	$show_next = 1 unless $next >= $numrows;
	# page loop
	@pages = ();

	my $pageon = int($start / $C->rpp_titles()) + 1;
	if($pageon < 1) {
		$pageon = 1;
	}
	my $startpage = $pageon - 5;
	if($startpage < 1) {
		$startpage = 1;
	}

	my $endpage = $startpage + $C->rpp_titles() - 1;
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
		push(@pages,{s=>$C->rpp_titles() * $count,page=>$_,tp=>$tp,lastmfr=>$mfr});
		$count ++;
	}
	$sth->finish();
  #&debug("next = " . $next . "<br />");
  #&debug("prev = " . $prev . "<br />");
  #&debug("show_next = " . $show_next . "<br />");
  #&debug("show_prev = " . $show_prev . "<br />");
  
  return @titles;  
}

###############################################################################
# Return the titles belonging to the os
#
# Change History:
# 03.15.2006 - Initial Version - jarnold
###############################################################################
sub getTitlesByOS {
  my $os_id = shift;
  die "No os_id passed to getTitlesByIS!" unless $os_id;
  
	my $query = "select count(*) from software where os1 = ? OR os2 = ? OR os3 = ? OR os4 = ? OR os5 = ? OR os6 = ? OR os7 = ? OR os8 = ?";
  $sth = $C->db_query($query,[$os_id,$os_id,$os_id,$os_id,$os_id,$os_id,$os_id,$os_id]);
	my $numrows = $sth->fetchrow;
  #&debug("Num Rows = " . $numrows . "<br />");
  
	my $numpages = int($numrows / $C->rpp_titles());
	if($numrows % $C->rpp_titles()) {
		$numpages ++;
	}
	$sth->finish;

	my $start = $F{'s'} || 0; # s = starting row
	$query = "select id,title,mfr,version from software where os1 = ? OR os2 = ? OR os3 = ? OR os4 = ? OR os5 = ? OR os6 = ? OR os7 = ? OR os8 = ? order by title";

  $query .= " LIMIT $start, " . $C->rpp_titles();
  $sth = $C->db_query($query,[$os_id,$os_id,$os_id,$os_id,$os_id,$os_id,$os_id,$os_id]);
  
	my @titles = ();
	while(my $row = $sth->fetchrow_hashref) {
    $row->{title_id} = $row->{id};
    delete($row->{id}); 
    $row->{os_id} = $os_id;
		push(@titles,$row);
	}
	$sth->finish;

  $next = $start + $C->rpp_titles();
	$prev = $start - $C->rpp_titles();
	# make sure we don't do a previous out of range
	$prev = 0 unless $prev > -1;
	# don't show the previous button unless there are previous items
	$show_prev = 1 unless $start == 0;
	# don't show next button unless there are more items
	$show_next = 1 unless $next >= $numrows;
	# page loop
	@pages = ();

	my $pageon = int($start / $C->rpp_titles()) + 1;
	if($pageon < 1) {
		$pageon = 1;
	}
	my $startpage = $pageon - 5;
	if($startpage < 1) {
		$startpage = 1;
	}

	my $endpage = $startpage + $C->rpp_titles() - 1;
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
		push(@pages,{s=>$C->rpp_titles() * $count,page=>$_,tp=>$tp,lastos=>$F{'os'}});
		$count ++;
	}
	$sth->finish();
  #&debug("next = " . $next . "<br />");
  #&debug("prev = " . $prev . "<br />");
  #&debug("show_next = " . $show_next . "<br />");
  #&debug("show_prev = " . $show_prev . "<br />");
  
  return @titles;  
}

###############################################################################
## Error & Debugging
sub show_error {
  my $msg = shift;
  my $template = $C->tmpl('admin_error_user');
  $template->param(msg=>$msg);
  print $Q->header();
  print $template->output();
  exit;
}

sub debug {
  return unless ($DEBUG);
	&debug_init() unless ($DEBUG_INIT);
  print shift;
}

sub debug_init {
	$DEBUG_INIT = 1;
	&debug($Q->header());
}
