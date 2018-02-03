package SWINV::Verify;
##
## SWINV::Verify - Utilities functions for validating input
##
## Copyright (C) 2006 2k3 Technologies
##
## $Id: Verify.pm,v 2.0 2006/02/12 19:55:34 jarnold Exp $ 

use strict;
use Exporter;

our @ISA = qw(Exporter);
our @EXPORT = qw(&vrfy_int &vrfy_float &vrfy_string &vrfy_word &vrfy_blob);

#sub new { return bless {},__PACKAGE__ }

sub vrfy_int {
	my $ref = shift;
	return 0 unless $$ref =~ /^(\d+)$/;
	$$ref = $1;
	return 1;
}

sub vrfy_float {
	my $ref = shift;
	return 0 unless $$ref =~ /^(\d+(?:\.\d+)?)$/;
	$$ref = $1;
	return 1;
}

sub vrfy_string {
	my $ref = shift;
	return 0 unless $$ref =~ /^([\x20-\x7f]+)$/;
	$$ref = $1;
	return 1;
}

sub vrfy_word {
	my $ref = shift;
	return 0 unless $$ref =~ /^([A-Za-z0-9\._\-]+)$/;
	$$ref = $1;
	return 1;
}

# pretty much the same as string but includes \n && \r
sub vrfy_blob {
	my $ref = shift;
	return 0 unless $$ref =~ /^([\x20-\x7f\n\r]+)$/;
	$$ref = $1;
	return 1;
}
	

1;
