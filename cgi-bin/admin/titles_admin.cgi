#!/usr/bin/perl -T
# $Id: titles_admin.cgi,v 1.19 2006/02/02 12:13:46 jarnold Exp $
##
## Copyright (C) 2k3 Technologies, 2006
##
## $Id: Conf.pm,v 1.25 2004/03/22 05:04:44 jarnold Exp $

use strict;
use lib '..';
use CGI::Carp qw(fatalsToBrowser); # for testing
use CGI;
use DBI;
use HTML::Template;
use SWINV::Conf;
use SWINV::Verify;
use URI::Escape;

my $C = new SWINV::Conf;
my $Q = new CGI;
my %F = $Q->Vars();

our $DEBUG = 0;
our $DEBUG_INIT = 0;

$C->encode_html(\%F);

my $sth;
my $size_x;
my $size_y;

my %modes = (
	add=>\&do_add,
	view=>\&do_view,
	modify=>\&do_modify,
	delete=>\&do_delete,
	deleteFromLoc=>\&deleteLocation,
	cancelmod=>\&do_cancelmod,
	updateAddPage=>\&getAllInfo,
	updateModifyPage=>\&updateAllInfo,
	default=>\&do_default
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

#############################################################
# Subroutines
#############################################################

sub do_default {
	show_default();
}

sub show_default {
	my $template = $C->tmpl('admin_titles');
	print $Q->header(-type=>'text/html');
	print $template->output();
}

#------------------------------------------------------------------------------
# Return an array of os id,name pairs
#
# Change History:
#------------------------------------------------------------------------------
sub get_os_list {

	my @dbp = ();
	my @oss = ();
	my @osids = $Q->param('os_list');
	&debug("OS Ids Size = " . @osids . "<br>");
	my $query_os = 'select id,os_name from os order by os_name';
	$sth = $C->db_query($query_os,\@dbp);
	while (my $row = $sth->fetchrow_hashref()) {
		$row->{os_id} = $row->{id};
		delete($row->{id});
		foreach my $osid (@osids) {
			if ($row->{os_id} eq $osid) {
			  $row->{'on'} = '1';
			}
		}
		push(@oss,$row);
	}
	return @oss;	
}

sub build_os_list {
	my $osids = shift;
  my $asscount = 0;
  foreach my $key (keys %$osids) {
    $asscount++;
  }
	my @oss = ();
  &debug("Size of oss array argument is " . $asscount . "<br>");
	my $query_os = 'select id,os_name from os order by os_name';
	$sth = $C->db_query($query_os,[]);
	while (my $row = $sth->fetchrow_hashref()) {
		$row->{os_id} = $row->{id};
		delete($row->{id});
		while ((my $k, my $v) = each(%$osids)) {
		&debug("Os Index = " . $k . "  My Os Id = " . $v . "<br>");
			if ($row->{os_id} eq $v) {
			&debug("We Have a match.<br>");
			  $row->{'on'} = '1';
			}
		}
		push(@oss,$row);
	}
	return @oss;	
}

# Build the cat list and mark the appropriate one as 'on'
sub build_cat_list {
	my $cat = shift;
	#&debug("Cat id in build_cat_list = " . $cat);
  # get the category headings for the filter.
  my $query = "select heading,id from category order by heading";
  my @categories = ();
  $sth = $C->db_query($query,[]);
  while (my $row = $sth->fetchrow_hashref) {
    $row->{cat_id} = $row->{id};
    delete($row->{id});
		#&debug("Row->cat_id = " . $row->{cat_id} . "<br>");
    if ($cat eq $row->{cat_id}) {
		#&debug("We have a match");
      $row->{'on'} = "1";
    }
    push(@categories,$row);
  }
  $sth->finish();
	return @categories;
}

# build the subcat list and mark the appropriate one as 'on'
sub build_subcat_list {
	my ($cat,$subcat) = @_;
 	my @subcategories = ();

  # get the subcategories headings for the filter.
  if ($cat) {
	#&debug("Category ID = " . $cat);
		my $query = "select name,id from subcategory where category_id = ? order by name";
  	$sth = $C->db_query($query,[$cat]);
  	while (my $row = $sth->fetchrow_hashref) {
  		$row->{subcat_id} = $row->{id};
			$row->{subcat_heading} = $row->{name};
  		delete($row->{id});
			delete($row->{name});
			if ($subcat && ($subcat eq $row->{subcat_id})) {
				$row->{on} = 1;
			}
			push(@subcategories,$row);
  		}
		$sth->finish();
  }
	return @subcategories;
}

#-------------------------------------------------------------------------------
# Build the list of binders to show in the modify screen
#-------------------------------------------------------------------------------
sub build_binder_list {
	# Get available binder info
	my $query = 'select id,vol_desc,sheets,slots,pouches from volumes order by id';
	my @binders = ();
	my $count = 0;
	$sth = $C->db_query($query,[]);
	while (my $row = $sth->fetchrow_hashref()) {
	$count++;
	#show_error($row->{vol_desc});
		#$pouchstrings .= " " . $row->{pouches};
		$row->{vol_id} = $row->{id};
		delete($row->{id});
		
		# do the easy case first
		if ($row->{pouches}) {
		  delete($row->{sheets});
			delete($row->{slots});
			delete($row->{pouches});
		  push(@binders,$row);
		} else {
			my $capacity = $row->{sheets} * $row->{slots};
			my $query2 = 'select count(*) from location where volume_id = ?';
			my $sth2 = $C->db_query($query2,[$row->{vol_id}]);
			my $filled = $sth2->fetchrow();
			if ($capacity > $filled) {
			  delete($row->{sheets});
				delete($row->{slots});
				delete($row->{pouches});
				push(@binders,$row);
			}
			$sth2->finish();
		}
	}
	$sth->finish();
	return @binders
}

#-----------------------------------------------------------------------------------
# Add a new title to the system
#-----------------------------------------------------------------------------------
sub do_add {
	unless($ENV{'REQUEST_METHOD'} eq 'POST') {
		show_add();
	}
	else {
		my %error = ();
		unless(vrfy_string(\$F{'title'})) {
			$error{title_error} = "Either you didn't enter a title for the software or it contained invalid characters.";
		}
		unless(vrfy_string(\$F{'mfr'})) {
			$error{mfr_error} = "Either you didn't enter a vendor name for the software or it contained invalid characters.";
		}
		unless(vrfy_string(\$F{'version'})) {
			$error{version_error} = "Either you didn't enter the version number for the software or it contained invalid characters.  If a version number is not available, enter '-'.";
		}
		unless(vrfy_string(\$F{'blicense'})) {
			$error{blicense_error} = "Either you didn't enter the base license key for the software or it contained invalid characters.  If the software does not require a license, enter 'None Required'.  If the license key is not known, enter 'Unknown.'";
		}

		if(%error) {
			$error{'title'} = $F{'title'};
			$error{'mfr'} = $F{'mfr'};
			$error{'version'} = $F{'version'};
			$error{'blicense'} = $F{'blicense'};
			show_add(\%error);
		}
		else {
		# Get the selected os ids;
		my ($os1,$os2,$os3,$os4,$os5,$os6,$os7,$os8);
		my @osids = $Q->param('os_list');
		my %os_hash = ();
		my $count = 1;
		foreach  my $osid (@osids) {
			%os_hash->{$count} = $osid;
			$count++;
		}
		$os1 = (defined %os_hash->{1} ? %os_hash->{1} : undef);
		$os2 = (defined %os_hash->{2} ? %os_hash->{2} : undef);
		$os3 = (defined %os_hash->{3} ? %os_hash->{3} : undef);
		$os4 = (defined %os_hash->{4} ? %os_hash->{4} : undef);
		$os5 = (defined %os_hash->{5} ? %os_hash->{5} : undef);
		$os6 = (defined %os_hash->{6} ? %os_hash->{6} : undef);
		$os7 = (defined %os_hash->{7} ? %os_hash->{7} : undef);
		$os8 = (defined %os_hash->{8} ? %os_hash->{8} : undef);
		&debug("os1 = " . $os1 . "; os2 = " . $os2 . "; os3 = " . $os3 . "; os4 = " . $os4 . "; os5 = ". $os5 . "; os6 = " . $os6 . "; os7 = " . $os7 . "; os8 = " . $os8 . "<br>");
		my @dbp = ();
		my $query = 'insert into software (title,mfr,version,category_id,subcategory_id,os1,os2,os3,os4,os5,os6,os7,os8) values (?,?,?,?,?,?,?,?,?,?,?,?,?)';
		$sth = $C->db_query($query,[$F{'title'},$F{'mfr'},$F{'version'},$F{'cat_list'},$F{'subcat_list'},$os1,$os2,$os3,$os4,$os5,$os6,$os7,$os8]);
		$sth->finish();
		my $query = 'select last_insert_id()';
		$sth = $C->db_query($query,\@dbp);
		my $swid = $sth->fetchrow();
		$sth->finish();
		#&debug("Last Insert ID = $swid.");
		
		# insert License Info
		my ($uname,$baccess,$elicense,$eaccess,$udef1,$udef2);
		if ($F{'uname'}) { $uname = $F{'uname'}; }
		if ($F{'baccess'}) { $baccess = $F{'baccess'}; }
		if ($F{'elicense'}) { $elicense = $F{'elicense'}; }
		if ($F{'eaccess'}) { $eaccess = $F{'eaccess'}; }
		if ($F{'udef1'}) { $udef1 = $F{'udef1'}; }
		if ($F{'udef2'}) { $udef2 = $F{'udef2'}; }
		
		$query = 'insert into license  (software_id,username,base_license_key,base_access_key,ext_license_key,ext_access_key,udef_field_val,udef_field_name) values(?,?,?,?,?,?,?,?)';
		$sth = $C->db_query($query,[$swid,$uname,$F{'blicense'},$baccess,$elicense,$eaccess,$udef1,$udef2]);
		$sth->finish();
		# insert Location Info		
		if ($F{'binder_list'}) {
			$query = 'insert into location (software_id,volume_id,sheet,slot,pouch) values(?,?,?,?,?)';
			$sth = $C->db_query($query,[$swid,$F{'binder_list'},$F{'sheet_list'},$F{'slot_list'},$F{'pouch_list'}]);
			$sth->finish();
		}
		show_success("Title '<b>$F{'title'}</b>' has been added successfully.","titles_admin.cgi?mode=view");
		}
	}
}

#---------------------------------------------------------------
# Dynamically display information based on the user selections
#---------------------------------------------------------------
sub getAllInfo {
	my %params = ();
	$params{'title'} = $F{'title'};
	$params{'mfr'} = $F{'mfr'};
	$params{'version'} = $F{'version'};
	$params{'uname'} = $F{'uname'};
	$params{'blicense'} = $F{'blicense'};
	$params{'baccess'} = $F{'baccess'};
	$params{'elicense'} = $F{'elicense'};
	$params{'eaccess'} = $F{'eaccess'};
	$params{'udef1'} = $F{'udef1'};
	$params{'udef2'} = $F{'udef2'};

 	my @sheets = ();
	my @slots = ();

	if ($F{'binder_list'}) {
	  # get the sheet numbers for the binder if we don't already have it
		&debug("Volume ID = " . $F{'binder_list'} . "<br>");
		my $query = 'select sheets,slots from volumes where id = ?';
 		$sth = $C->db_query($query,[$F{'binder_list'}]);
		my ($numSheets,$numSlots) = $sth->fetchrow();
		$sth->finish();
		
		my $sheetCount = 1;

		$query = 'select distinct(sheet) from location where volume_id = ? and sheet is not null order by sheet';
		$sth = $C->db_query($query,[$F{'binder_list'}]);
		while (my $row = $sth->fetchrow_hashref()) {
			&debug("Sheet Number from db = " . $row->{sheet} . "<br>");
			&debug("sheetCount:  " . $sheetCount . "  db sheet num: " . $row->{sheet} . "<br>");
			
      # Add empty previous sheets to the list
			if ($sheetCount < $row->{sheet}) {
				&debug("We are inside adding previous empty sheets<br>");
				my $i = 0;
		  	for ($i = $sheetCount; $i < $row->{sheet}; $i++) {
					my %newrow = ();
					%newrow->{sheet_num} = $i;
					if ($F{'sheet_list'} && ($F{'sheet_list'} eq $row->{sheet})) {
						%newrow->{on} = '1';
					}
					push(@sheets,\%newrow);
				} # end for (...)
				$sheetCount = $i;
			} # End if ($sheetCount  < $row{sheet}
			
      # Add the current sheet if slots are available for it
			my $query2 = 'select count(slot) from location where volume_id = ? and sheet = ? order by slot';
			my $sth2 = $C->db_query($query2,[$F{'binder_list'},$row->{sheet}]);
			my $sheet_slots = $sth2->fetchrow();
			&debug("Sheet Slots in DB: " . $sheet_slots . " Max Slots: " . $numSlots . "<br>");
			if ($sheet_slots < $numSlots) {
				my %newrow = ();
				%newrow->{sheet_num} = $row->{sheet};
				if ($F{'sheet_list'} && ($F{'sheet_list'} eq $row->{sheet})) {
					%newrow->{on} = '1';
				}
				push(@sheets,\%newrow);
			} # end if (@slots ...
			$sth2->finish();
			$sheetCount++;
		} # end while
		
		$sth->finish();
		#&debug("SheetCount after while loop: " . $sheetCount);
		# Add the remaining sheet numbers
		for (my $i = $sheetCount; $i <= $numSheets; $i++) {
			my %row = ();
			%row->{sheet_num} = $i;
			if ($F{'sheet_list'} && ($F{'sheet_list'} eq %row->{sheet_num})) {
				%row->{on} = '1';
			}
			push(@sheets,\%row);
		} # end for (...)
	
		# Add the slots
		if ($F{'sheet_list'}) {
			#&debug("Selected Sheet:  " . $F{'sheet_list'});
			my %knownslots = ();
			for (my $i = 1; $i <= $numSlots; $i++) {
				%knownslots->{$i} = $i;
			}
			$query = 'select slot from location where volume_id = ? and sheet = ? order by slot';
			$sth = $C->db_query($query,[$F{'binder_list'},$F{'sheet_list'}]);
			# remove the slots that are taken
			while (my $row = $sth->fetchrow_hashref()) {
				delete(%knownslots->{$row->{slot}});
			}
      # sort the hash so it shows nicely...
      my @sortedslots = sort { $knownslots{$a} cmp $knownslots{$b} } keys %knownslots;
			# Add whatevers left to the slots array
			foreach my $key (@sortedslots) {
				my %newrow = ();
				%newrow->{slot_num} = $key;
				if ($F{'slot_list'} && ($F{'slot_list'} eq %newrow->{slot_num})) {
					%newrow->{on} = '1';
				}
				push(@slots,\%newrow);
			}
		} # end if ($F{'sheet_list'} ...
	} # end if ($F{'binder_list')
					
	# Set up the pouches list
	my @pouches = ();
	my $query = 'select pouches from volumes where id = ?';
	my $sth = $C->db_query($query,[$F{'binder_list'}]);
	my $numPouches = $sth->fetchrow();
	#&debug("Number of Pouches = " . $numPouches);
	for(my $i = 1; $i <= $numPouches; $i++) {
		my %row = ();
		%row->{pouch_num} = $i;
		if ($F{'pouch_list'} && ($F{'pouch_list'} eq %row->{pouch_num})) {
			%row->{'on'} = "1";
		}
		push(@pouches,\%row);
	}

	# set up the categories	
 	my @subcategories = ();
  # get the subcategories headings for the filter.
  if ($F{'cat_list'}) {
	#&debug("Category ID = " . $F{'cat_list'});
		my $query = "select name,id from subcategory where category_id = ? order by name";
  	$sth = $C->db_query($query,[$F{'cat_list'}]);
  	while (my $row = $sth->fetchrow_hashref) {
  		$row->{subcat_id} = $row->{id};
			$row->{subcat_heading} = $row->{name};
  		delete($row->{id});
			delete($row->{name});
			if ($F{'subcat_list'} && ($F{'subcat_list'} eq $row->{subcat_id})) {
				$row->{on} = 1;
			}
			push(@subcategories,$row);
  		}
		$sth->finish();
  }

	showAddExp(\%params,\@subcategories,\@sheets,\@slots,\@pouches);
}

#---------------------------------------------------------------
# Dynamically display information based on the user selections
#---------------------------------------------------------------
sub updateAllInfo {
	
	die "No title_id passed to updateAllInfo()!" unless $F{'title_id'};
	my %params = ();
	$params{'title_id'} = $F{'title_id'};
	$params{'title'} = $F{'title'};
	$params{'mfr'} = $F{'mfr'};
	$params{'version'} = $F{'version'};
	$params{'uname'} = $F{'uname'};
	$params{'blicense'} = $F{'blicense'};
	$params{'baccess'} = $F{'baccess'};
	$params{'elicense'} = $F{'elicense'};
	$params{'eaccess'} = $F{'eaccess'};
	$params{'udef1'} = $F{'udef1'};
	$params{'udef2'} = $F{'udef2'};
	$params{'cur_vol'} = $F{'cur_vol'};
	$params{'cur_sheet'} = $F{'cur_sheet'};
	$params{'cur_slot'} = $F{'cur_slot'};
	$params{'cur_pouch'} = $F{'cur_pouch'};
	$params{'vol_id'} = $F{'vol_id'};

 	my @sheets = ();
	my @slots = ();
	if ($F{'binder_list'}) {
	  # get the sheet numbers for the binder if we don't already have it
		&debug("Volume ID = " . $F{'binder_list'} . "<br>");
		&debug("Sheet Number = " . $F{'sheet_list'} . "<br>");
		my $query = 'select sheets,slots from volumes where id = ?';
 		$sth = $C->db_query($query,[$F{'binder_list'}]);
		my ($numSheets,$numSlots) = $sth->fetchrow();
		$sth->finish();
		
		my $sheetCount = 1;

		$query = 'select distinct(sheet) from location where volume_id = ? and sheet is not null order by sheet';
		$sth = $C->db_query($query,[$F{'binder_list'}]);
		while (my $row = $sth->fetchrow_hashref()) {
			#&debug("sheetCount:  " . $sheetCount . "  db sheet num: " . $row->{sheet} . "<br>");
			# Add empty previous sheets to the list
			if ($sheetCount < $row->{sheet}) {
				#&debug("We are inside<br>");
				my $i = 0;
		  	for ($i = $sheetCount; $i < $row->{sheet}; $i++) {
					my %newrow = ();
					%newrow->{sheet_num} = $i;
					if ($F{'sheet_list'} && ($F{'sheet_list'} eq $row->{sheet})) {
						%newrow->{on} = '1';
					}
					push(@sheets,\%newrow);
				} # end for (...)
				$sheetCount = $i;
			} # End if ($sheetCount ...
			# Add the current sheet if slots are available for it
			my $query2 = 'select count(slot) from location where volume_id = ? and sheet = ? order by slot';
			my $sth2 = $C->db_query($query2,[$F{'binder_list'},$row->{sheet}]);
      my $sheet_slots = $sth2->fetchrow();
			#&debug("Sheet Slots in DB: " . $sheet_slots . " Max Slots: " . $numSlots . "<br>");
			if ($sheet_slots < $numSlots) {
        #&debug("adding available sheet to list...<br>");
				my %newrow = ();
				%newrow->{sheet_num} = $row->{sheet};
				if ($F{'sheet_list'} && ($F{'sheet_list'} eq $row->{sheet})) {
					%newrow->{on} = '1';
				}
				push(@sheets,\%newrow);
			} # end if (@slots ...
			$sth2->finish();
			$sheetCount++;
		} # end while
		
		$sth->finish();
		#&debug("SheetCount after while loop: " . $sheetCount . "<br>");
		# Add the remaining sheet numbers
		for (my $i = $sheetCount; $i <= $numSheets; $i++) {
			my %row = ();
			%row->{sheet_num} = $i;
			if ($F{'sheet_list'} && ($F{'sheet_list'} eq %row->{sheet_num})) {
				%row->{on} = '1';
			}
			push(@sheets,\%row);
		} # end for (...)
	
		# Add the slots
		if ($F{'sheet_list'}) {
      #&debug("Adding slots to sheets...<br>");
			#&debug("Selected Sheet:  " . $F{'sheet_list'} . "<br>");
			my %knownslots = ();
			for (my $i = 1; $i <= $numSlots; $i++) {
				%knownslots->{$i} = $i;
			}
			$query = 'select slot from location where volume_id = ? and sheet = ? order by slot';
			$sth = $C->db_query($query,[$F{'binder_list'},$F{'sheet_list'}]);
			# remove the slots that are taken
			while (my $row = $sth->fetchrow_hashref()) {
				delete(%knownslots->{$row->{slot}});
			}
      # sort the hash so it shows nicely...
      my @sortedslots = sort { $knownslots{$a} cmp $knownslots{$b} } keys %knownslots;
			# Add whatevers left to the slots array
			foreach my $key (@sortedslots) {
				my %newrow = ();
				%newrow->{slot_num} = $key;
				if ($F{'slot_list'} && ($F{'slot_list'} eq %newrow->{slot_num})) {
					%newrow->{on} = '1';
				}
				push(@slots,\%newrow);
			}
		} # end if ($F{'sheet_list'} ...
	} # end if ($F{'binder_list')
					
	# Set up the pouches list
	my @pouches = ();
	my $query = 'select pouches from volumes where id = ?';
	my $sth = $C->db_query($query,[$F{'binder_list'}]);
	my $numPouches = $sth->fetchrow();
	#show_error("Number of Pouches = " . $numPouches);
	for(my $i = 1; $i <= $numPouches; $i++) {
		my %row = ();
		%row->{pouch_num} = $i;
		if ($F{'pouch_list'} && ($F{'pouch_list'} eq %row->{pouch_num})) {
			%row->{'on'} = "1";
		}
		push(@pouches,\%row);
	}

	# set up the categories	
 	my @subcategories = ();
  # get the subcategories headings for the filter.
  if ($F{'cat_list'}) {
	#&debug("Category ID = " . $F{'cat_list'});
		my $query = "select name,id from subcategory where category_id = ? order by name";
  	$sth = $C->db_query($query,[$F{'cat_list'}]);
  	while (my $row = $sth->fetchrow_hashref) {
  		$row->{subcat_id} = $row->{id};
			$row->{subcat_heading} = $row->{name};
  		delete($row->{id});
			delete($row->{name});
			if ($F{'subcat_list'} && ($F{'subcat_list'} eq $row->{subcat_id})) {
				$row->{on} = 1;
			}
			push(@subcategories,$row);
  		}
		$sth->finish();
  }

	showUpdateExp(\%params,\@subcategories,\@sheets,\@slots,\@pouches);
}

#---------------------------------------------------------------------
# Show expanded select lists on update page
#---------------------------------------------------------------------
sub showUpdateExp {
	my ($params,$subcategories,$sheets,$slots,$pouches) = @_;

	my $template = $C->tmpl('admin_titles_modify');
	$template->param(%$params) if $params;

	my $query = '';
	# get the os list
	my @oss = get_os_list();
	$template->param(oss=>\@oss);
	
	# get the categories
	my @cats = ();
	$query = 'select id,heading from category order by heading';
	$sth = $C->db_query($query,[]);
	while (my $row = $sth->fetchrow_hashref()) {
	  $row->{cat_id} = $row->{id};
		delete($row->{id});
		if ($F{'cat_list'} && ($F{'cat_list'} eq $row->{cat_id})) {
			$row->{'on'} = '1';
		}
		push(@cats,$row);
	}
	$sth->finish();
	$template->param(cats=>\@cats);
	$template->param(subcats=>$subcategories);
	$template->param(sheets=>$sheets);
	$template->param(slots=>$slots);
	$template->param(pouches=>$pouches);

	# Get available binder info
	$query = 'select id,vol_desc,sheets,slots,pouches from volumes order by id';
	my @binders = ();
	my $count = 0;
	$sth = $C->db_query($query,[]);
	while (my $row = $sth->fetchrow_hashref()) {
		$count++;
		#show_error($row->{vol_desc});
		#$pouchstrings .= " " . $row->{pouches};
		$row->{vol_id} = $row->{id};
		delete($row->{id});
		
		# do the easy case first
		if ($row->{pouches}) {
		  delete($row->{sheets});
			delete($row->{slots});
			delete($row->{pouches});
			if ($F{'binder_list'} && ($F{'binder_list'} eq $row->{vol_id})) {
			  $row->{on} = '1';
			}
		  push(@binders,$row);
		} else {
			my $capacity = $row->{sheets} * $row->{slots};
			my $query2 = 'select count(*) from location where volume_id = ?';
			my $sth2 = $C->db_query($query2,[$row->{vol_id}]);
			my $filled = $sth2->fetchrow();
			if ($capacity > $filled) {
			  delete($row->{sheets});
				delete($row->{slots});
				delete($row->{pouches});
				if ($F{'binder_list'} && ($F{'binder_list'} eq $row->{vol_id})) {
					$row->{on} = '1';
				}
				push(@binders,$row);
			}
			$sth2->finish();
		}
	}
	$sth->finish();
	$template->param(binders=>\@binders);
	
	print $Q->header(-type=>'text/html');
	print $template->output();
} # End showUpdateExp

#---------------------------------------------------------------------
# Show expanded select lists on add page
#---------------------------------------------------------------------
sub showAddExp {
	my ($params,$subcategories,$sheets,$slots,$pouches) = @_;

	my $template = $C->tmpl('admin_titles_add');
	$template->param(%$params) if $params;

	my @oss = get_os_list();
	$template->param(oss=>\@oss);
	
	# get the categories
	my @cats = ();
	my $query = 'select id,heading from category order by heading';
	$sth = $C->db_query($query,[]);
	while (my $row = $sth->fetchrow_hashref()) {
	  $row->{cat_id} = $row->{id};
		delete($row->{id});
		if ($F{'cat_list'} && ($F{'cat_list'} eq $row->{cat_id})) {
			$row->{'on'} = '1';
		}
		push(@cats,$row);
	}
	$sth->finish();
	$template->param(cats=>\@cats);
	$template->param(subcats=>$subcategories);
	$template->param(sheets=>$sheets);
	$template->param(slots=>$slots);
	$template->param(pouches=>$pouches);

	# Get available binder info
	$query = 'select id,vol_desc,sheets,slots,pouches from volumes order by id';
	my @binders = ();
	my $count = 0;
	$sth = $C->db_query($query,[]);
	while (my $row = $sth->fetchrow_hashref()) {
		$count++;
		#show_error($row->{vol_desc});
		#$pouchstrings .= " " . $row->{pouches};
		$row->{vol_id} = $row->{id};
		delete($row->{id});
		
		# do the easy case first
		if ($row->{pouches}) {
		  delete($row->{sheets});
			delete($row->{slots});
			delete($row->{pouches});
			if ($F{'binder_list'} && ($F{'binder_list'} eq $row->{vol_id})) {
			  $row->{on} = '1';
			}
		  push(@binders,$row);
		} else {
			my $capacity = $row->{sheets} * $row->{slots};
			my $query2 = 'select count(*) from location where volume_id = ?';
			my $sth2 = $C->db_query($query2,[$row->{vol_id}]);
			my $filled = $sth2->fetchrow();
			if ($capacity > $filled) {
			  delete($row->{sheets});
				delete($row->{slots});
				delete($row->{pouches});
				if ($F{'binder_list'} && ($F{'binder_list'} eq $row->{vol_id})) {
					$row->{on} = '1';
				}
				push(@binders,$row);
			}
			$sth2->finish();
		}
	}
	$sth->finish();
	$template->param(binders=>\@binders);
	
	print $Q->header(-type=>'text/html');
	print $template->output();
}

#-----------------------------------------
# Show the Add Page
#-----------------------------------------
sub show_add {
	my $error = shift;
	my $query = '';
	my $template = $C->tmpl('admin_titles_add');
	$template->param(%$error) if $error;
	my @dbp = ();

	# get the os list
	my @oss = get_os_list();
	$template->param(oss=>\@oss);
	
	# get the categories
	my @cats = ();
	$query = 'select id,heading from category order by heading';
	$sth = $C->db_query($query,\@dbp);
	while (my $row = $sth->fetchrow_hashref()) {
	  $row->{cat_id} = $row->{id};
		delete($row->{id});
		push(@cats,$row);
	}
	$sth->finish();
	$template->param(cats=>\@cats);

	# Get available binder info
	$query = 'select id,vol_desc,sheets,slots,pouches from volumes order by id';
	my @binders = ();
	my $count = 0;
	$sth = $C->db_query($query,\@dbp);
	while (my $row = $sth->fetchrow_hashref()) {
	$count++;
	#show_error($row->{vol_desc});
		#$pouchstrings .= " " . $row->{pouches};
		$row->{vol_id} = $row->{id};
		delete($row->{id});
		
		# do the easy case first
		if ($row->{pouches}) {
		  delete($row->{sheets});
			delete($row->{slots});
			delete($row->{pouches});
		  push(@binders,$row);
		} else {
			my $capacity = $row->{sheets} * $row->{slots};
			my $query2 = 'select count(*) from location where volume_id = ?';
			my $sth2 = $C->db_query($query2,[$row->{vol_id}]);
			my $filled = $sth2->fetchrow();
			if ($capacity > $filled) {
			  delete($row->{sheets});
				delete($row->{slots});
				delete($row->{pouches});
				push(@binders,$row);
			}
			$sth2->finish();
		}
	}
	$sth->finish();
	$template->param(binders=>\@binders);
	print $Q->header(-type=>'text/html');
	print $template->output();
}

#-----------------------------------------------
# Display the admin view of all titles
#-----------------------------------------------
sub do_view {
	my $query1 = "select count(*) from software";
  my @dbparms = ();
  my $where = " where ";
  if ($F{'cat'} && ($F{'cat'} ne "*")) {
    $where = " where category_id = ?";
    $query1 .= $where;
    push(@dbparms,$F{'cat'});
  }
  if ($F{'mfr'} && ($F{'mfr'} ne "*")) {
    $where = " where mfr = ?";
    $query1 .= $where;
    push(@dbparms,$F{'mfr'});
  }
  $sth = $C->db_query($query1,\@dbparms);
	my $numrows = $sth->fetchrow;

	my $numpages = int($numrows / $C->rpp_titles());
	if($numrows % $C->rpp_titles()) {
		$numpages ++;
	}
	$sth->finish;

	my $start = $F{'s'} || 0; # s = starting row
  my $order_by = " order by title";
	my $query = "select id,title,mfr,version from software";
  my @dbparms2 = ();
  if ($F{'cat'} && ($F{'cat'} ne "*")) {
    $where = " where category_id = ?";
    $query .= $where;
    push(@dbparms2,$F{'cat'});
  }
  if ($F{'mfr'} && ($F{'mfr'} ne "*")) {
    $where = " where mfr = ?";
    $query .= $where;
    push(@dbparms2,$F{'mfr'});
  }

  $query .= $order_by . " LIMIT $start, " . $C->rpp_titles();
  $sth = $C->db_query($query,\@dbparms2);
  
	my @titles = ();
	while(my $row = $sth->fetchrow_hashref) {
    $row->{title_id} = $row->{id};
    delete($row->{id});    
		push(@titles,$row);
	}
	$sth->finish;

	my $next = $start + $C->rpp_titles();
	my $prev = $start - $C->rpp_titles();
	# make sure we don't do a previous out of range
	$prev = 0 unless $prev > -1;
	# don't show the previous button unless there are previous items
	my $show_prev = 1 unless $start == 0;
	# don't show next button unless there are more items
	my $show_next = 1 unless $next >= $numrows;
	# page loop
	my @pages = ();
	my $qstring;

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
		push(@pages,{s=>$C->rpp_titles() * $count,page=>$_,tp=>$tp,lastcat=>$F{'cat'},lastmfr=>$F{'mfr'}});
		$count ++;
	}
	$sth->finish();
  
  # get the category headings for the filter.
  $query = "select heading,id from category order by heading";
  my @categories = ();
  $sth = $C->db_query($query,[]);
  while (my $row = $sth->fetchrow_hashref()) {
    $row->{cat_id} = $row->{id};
    delete($row->{id});
    if ($F{'cat'} && ($F{'cat'} eq $row->{cat_id})) {
      $row->{on} = "1";
    }
    push(@categories,$row);
  }
  $sth->finish();
  
  # get the mfr names for the filter
  my @mfrs = ();
  $query = "select distinct(mfr) from software order by mfr";
  $sth = $C->db_query($query,[]);
  while (my $row = $sth->fetchrow_hashref()) {
    $row->{mfr_name} = $row->{mfr};
    delete($row->{mfr});
    if ($F{'mfr'} && ($F{'mfr'} eq $row->{mfr_name})) {
      $row->{on} = "1";
    }
    push(@mfrs,$row);
  }
  $sth->finish();
  
  	show_view(\@categories,\@mfrs,\@titles,\$next,\$prev,\$show_next,\$show_prev,\@pages,\$qstring);

}

# ---------------------------------------------------------------------
# Modify an existing software title.
# ---------------------------------------------------------------------
sub do_modify {
	die "No title id passed to modify" unless $F{'title_id'};
	
  # show the update screen if the user clicked modify from the view screen
	if(!defined($F{'update'})) {
		my %params = ();
		$params{'title_id'} = $F{'title_id'};
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
			$params{'noLocSelect'} = "1";
			$params{'vol_id'} = $vol_id;
		} else {
			$params{'cur_vol'} = '-';
			$params{'noremove'} = "1";
		}
		show_modify(\%params,\$subcat,\$cat,\%os_hash);
	}
	else { # updates defined
		die "No title id passed to modify()!" unless $F{'title_id'};

		my %error = ();
		
		unless(vrfy_string(\$F{'title'})) {
			$error{title_error} = "Either you didn't enter a title for the software or it contained invalid characters";
		}
		unless(vrfy_string(\$F{'mfr'})) {
			$error{mfr_error} = "Either you didn't enter a vendor name for the software or it contained invalid characters";
		}
		unless(vrfy_string(\$F{'version'})) {
			$error{version_error} = "Either you didn't enter the version number for the software or it contained invalid characters.  If a version number is not available, enter '-'";
		}
		unless(vrfy_string(\$F{'blicense'})) {
			$error{blicense_error} = "Either you didn't enter the base license key for the software or it contained invalid characters.  If the software does not require a license, enter 'None Required'.  If the license key is not known, enter 'Unknown'";
		}

		if(%error) {
			$error{title_id} = $F{'title_id'};
			$error{title} = $F{'title'};
			$error{mfr} = $F{'mfr'};
			$error{version} = $F{'version'};
			$error{uname} = $F{'uname'};
			$error{blicense} = $F{'blicense'};
			$error{baccess} = $F{'baccess'};
			$error{elicense} = $F{'elicense'};
			$error{eaccess} = $F{'eaccess'};
			$error{udef1} = $F{'udef1'};
			$error{udef2} = $F{'udef2'};
			$error{vol_id} = $F{'vol_id'};
			$error{cur_vol} = $F{'cur_vol'};
			$error{cur_sheet} = $F{'cur_sheet'};
			$error{cur_slot} = $F{'cur_slot'};
			$error{cur_pouch} = $F{'cur_pouch'};
			$error{noLocSelect} = $F{'noLocSelect'};
			my $subcat = $F{'subcat_list'};
			my $cat = $F{'cat_list'};
			my @os_ids = $Q->param('os_list');
			my %os_hash = ();
			my $count = 1;
			foreach my $os_id (@os_ids) {
				%os_hash->{$count} = $os_id;
				$count++;
			}
			
			show_modify(\%error,\$subcat,\$cat,\%os_hash);
		}
		else { # execute the update
			# update the main table
			my @qargs = $Q->param('os_list');
			for (my $i = (@qargs - 1) + 1; $i < 8; $i++) {
				push(@qargs,undef);
			}
			push(@qargs,$F{'title'});
			push(@qargs,$F{'mfr'});
			push(@qargs,$F{'version'});
			push(@qargs,$F{'subcat_list'});
			push(@qargs,$F{'cat_list'});
			
			push(@qargs,$F{'title_id'});
			my $query = 'update software set os1=?,os2=?,os3=?,os4=?,os5=?,os6=?,os7=?,os8=?,title=?,mfr=?,version=?,subcategory_id=?,category_id=? where id = ?';
			$sth = $C->db_query($query,\@qargs);
			$sth->finish();
			
			# update licensing info
			@qargs = ();
			push(@qargs,(defined ($F{'uname'}) ? $F{'uname'} : undef));
			push(@qargs,$F{'blicense'});
			push(@qargs,(defined ($F{'baccess'}) ? $F{'baccess'} : undef));
			push(@qargs,(defined ($F{'elicense'}) ? $F{'elicense'} : undef));
			push(@qargs,(defined ($F{'eaccess'}) ? $F{'eaccess'} : undef));
			push(@qargs,(defined ($F{'udef1'}) ? $F{'udef1'} : undef));
			push(@qargs,(defined ($F{'udef2'}) ? $F{'udef2'} : undef));
			push(@qargs,$F{'title_id'});
			$query = 'update license set username=?,base_license_key=?,base_access_key=?,ext_license_key=?,ext_access_key=?,udef_field_val=?,udef_field_name=? where software_id = ?';
			$sth = $C->db_query($query,\@qargs);
			$sth->finish();
			
			# update location info
      if ($F{'binder_list'}) {
        @qargs = ();
        push(@qargs,$F{'binder_list'});
        push(@qargs,$F{'sheet_list'});
        push(@qargs,$F{'slot_list'});
        push(@qargs,$F{'pouch_list'});
        push(@qargs,$F{'title_id'});
        $query = 'select id from location where software_id = ?';
        $sth = $C->db_query($query,[$F{'title_id'}]);
        my $loc_id = $sth->fetchrow();
        $sth->finish();
        if ($loc_id) {
          $query = 'update location set volume_id=?,sheet=?,slot=?,pouch=? where software_id = ?';
        } else {
          $query = 'insert into location (volume_id,sheet,slot,pouch,software_id) values(?,?,?,?,?)';
        }
        $sth = $C->db_query($query,\@qargs);
        $sth->finish();
			}			
			show_success("'<b>$F{'title'}</b>' has been modified");
	  }  # end execute the update
	} # end updates defined
}

#--------------------------------------------------------------------
# Delete the location from the title
#--------------------------------------------------------------------
sub deleteLocation {
	die "No title_id passed to deleteLocation()!" unless $F{'title_id'};


	if(!$F{'confirm'}) {
    show_deleteLocation({title=>$F{'title'},vol_desc=>$F{'cur_vol'}});
	}
	else {
		$sth = $C->db_query("delete from location where software_id = ?",[$F{'title_id'}]);
		$sth->finish();
		show_success("Title '<b>$F{'title'}</b>' has been removed from Location: '<b>$F{'vol_desc'}</b>'","titles_admin.cgi?mode=modify&title_id=$F{title_id}");
	}
}

sub do_delete {
	die "No title_id passed to do_delete()!" unless $F{'title_id'};

	if(!$F{'confirm'}) {
    show_delete({title=>$F{'title'}});
	}
	else {
		$sth = $C->db_query("delete from software where id = ?",[$F{'title_id'}]);
		$sth->finish();
		$sth = $C->db_query("delete from license where software_id = ?",[$F{'title_id'}]);
		$sth->finish();
		$sth = $C->db_query("delete from location where software_id = ?",[$F{'title_id'}]);
		$sth->finish();
		
		show_success("Title '<b>$F{'title'}</b>' has been deleted from SIMS.","titles_admin.cgi?mode=view");
	}
}

sub show_modify {
  my ($params,$subcat,$cat,$os_hash,$vol_id,$sheet,$slot,$pouch) = @_;
	#&debug("Cat = " . $$cat . "  Subcat = " . $$subcat);

  my $template = $C->tmpl('admin_titles_modify');
	$template->param(%$params) if $params;
	my @oss = build_os_list($os_hash);
	my @cats = &build_cat_list($$cat);
	my @subcats = &build_subcat_list($$cat,$$subcat);
	my @binders = &build_binder_list();
	$template->param(oss=>\@oss);
	$template->param(cats=>\@cats);
	$template->param(subcats=>\@subcats);
	$template->param(binders=>\@binders);
  $template->param(tid=>$F{'title_id'});
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
	die "No title_id passed to show_delete()!" unless $F{'title_id'};

	my $template = $C->tmpl('admin_titles_delete');
	$template->param(title_id=>$F{'title_id'});
	$template->param(%$params);
	print $Q->header(-type=>'text/html');
	print $template->output();
}

sub show_deleteLocation {
	my $params = shift;
	die "No title_id passed to show_deleteLocation()!" unless $F{'title_id'};

	my $template = $C->tmpl('admin_titles_deleteLoc');
	$template->param(title_id=>$F{'title_id'});
	$template->param(%$params);
	print $Q->header(-type=>'text/html');
	print $template->output();
}

# ---------------------------------------------------------------------
# Display the admin view of all titles
# 02/08/06 - jarnold
# ---------------------------------------------------------------------
sub show_view {
	# all these are refs
	my($catlist,$mfrlist,$list,$next,$prev,$show_next,$show_prev,$pages,$qstring) = @_;

	my $template = $C->tmpl('admin_titles_list');
	$template->param(categories=>$catlist); #categories loop
  $template->param(mfrs=>$mfrlist); # vendor list
  $template->param(titles=>$list);	# titles loop
	$template->param('next'=>$$next);
	$template->param(prev=>$$prev);
	$template->param(show_next=>$$show_next);
	$template->param(show_prev=>$$show_prev);
	$template->param(pages=>$pages); # page anchors loop
	$template->param(qstring=>$$qstring);
  if ($F{'cat'}) {
    $template->param(lastcat=>$F{'cat'});
  }
  if ($F{'mfr'}) {
    $template->param(lastmfr=>$F{'mfr'});
  }
	print $Q->header(-type=>'text/html');
	print $template->output();
}

sub show_success {
	my ($msg,$return) = @_;
	my $template = $C->tmpl('admin_success');
	$template->param(msg=>$msg);
	if ($return) {
		$template->param(return=>$return);
	}
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

sub debug {
  return unless ($DEBUG);
	&debug_init() unless ($DEBUG_INIT);
  print shift;
}

sub debug_init {
	$DEBUG_INIT = 1;
	&debug($Q->header());
}

