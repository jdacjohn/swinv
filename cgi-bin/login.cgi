#! /usr/bin/perl -T
##
# login.cgi - Authenticate the user for protected site access.
#
# $Author: Jarnold $
# $Date: 5/31/06 9:20p $
# $Revision: 1 $
##

use strict;
use lib '.';
use CGI::Carp qw(fatalsToBrowser); #for testing
use CGI;
use CGI::Session;
use DBI;
use Date::Calc qw(Today_and_Now);
use HTML::Template;
use SWINV::Conf;
use SWINV::Verify;
use URI::Escape;

my $Q = new CGI;
my %F = $Q->Vars();
my $C = new SWINV::Conf;
my $session = new CGI::Session(undef, $Q, {Directory=>'/usr/local/Apache2/tmp'});
$Q->param(CGISESSID=>$session->id());

#show_CGI_vars();
init($session,$Q);

exit;

sub show_CGI_vars {
	print $Q->header(-type=>'text/html');
	print "URL = " . $Q->referer() . "<br>";
	while (my ($key,$value) = each(%F)) {
			print $key . '-' . $value . "<br>";
		}
}

sub init {
	my ($session, $cgi) = @_; # receive two args.
	
	if ($session->param('~logged-in')) {
		#print "User is logged in <br>";
		show_page(); # if logged in, go no further
	}
	#print "User is NOT logged in <br>";
	my $lg_name = $cgi->param("lg_name") or die 'No user name passed into login.cgi';
	my $lg_password = $cgi->param("lg_password") or die 'No password passed into login.cgi';
	if (my $login_match = authenticate($lg_name,$lg_password)) {
		#print "User login credentials passed <br>";
		$session->param("~logged_in", 1);
		$session->clear(["~log_attempts"]);
		show_page();
	} else {
		#print "User login credentials failed <br>";
		my $log_attempts = $session->param("~log_attempts") || 0;
		$session->param("~log_attempts",++$log_attempts);
		show_login();
	}
}

sub authenticate {
	my ($lg_name, $lg_password) = @_;
	my $query = 'select count(*) from user where username=? and u_passwd=password(?)';
	my $sth = $C->db_query($query,[$lg_name,$lg_password]);
	return $sth->fetchrow();
}

sub show_login {
	my $template = $C->tmpl('login');
	$template->param(auth_error=>'Your login credentials failed.  Please try again.');
	print $Q->header(-type=>'text/html');
	print $template->output();
}

sub show_page {
	#print $Q->header(-type=>'text/html');
	#print $Q->referer();
	print $Q->redirect(-uri=>$Q->referer(),
										 -status=>302,
										 -nph=>0);

}
