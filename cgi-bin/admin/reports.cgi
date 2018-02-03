#!/usr/bin/perl -T
# $Id: reports.cgi,v 1.19 2006/20/02 12:13:46 jarnold Exp $
##
## Copyright (C) 2k3 Technologies, 2006
##

use strict;
use lib '..';
use CGI::Carp 'fatalsToBrowser'; # for testing
use CGI;
use DBI;
use HTML::Template;
use SWINV::Conf;
use SWINV::Verify;
use URI::Escape;
use Date::Calc qw(:all);

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
	summary=>\&do_summary,
	glance=>\&do_glance,
	detail=>\&do_detail,
	exception=>\&do_exception,
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
	my $template = $C->tmpl('admin_reports');
	print $Q->header(-type=>'text/html');
	print $template->output();
}

sub do_summary {
	show_summary();
}

sub show_summary {
	my $template = $C->tmpl('reports_sum');
	print $Q->header(-type=>'text/html');
	print $template->output();
}

sub do_glance {
	my ($year,$month,$day) = Today();
	my ($hour,$min,$sec) = Now();
	my $reportDate = $month . "/" . $day . "/" . $year;
	my $reportTime = $hour . ":" . $min . ":" . $sec;
	&debug("Year = " . $year . " Month = " . $month . " Day = " . $day);
	show_glance(\$reportDate,\$reportTime);

}

sub show_glance {
	my ($reportDate,$reportTime) = @_;
	my $template = $C->tmpl('reports_sum_glance');
	$template->param(reportDate=>$$reportDate);
	$template->param(reportTime=>$$reportTime);
	print $Q->header(-type=>'text/html');
	print $template->output();
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

