#!/usr/bin/env perl

=head1 NAME

dump.pl - print some information from a socket

=head1 SYNOPSIS

./dump.pl [ -h ] [ -v ] <socket|server>

=head1 DESCRIPTION

this script print some information from a given livestatus socket or server

=head1 ARGUMENTS

script has the following arguments

=over 4

=item help

    -h

print help and exit

=item verbose

    -v

verbose output

=item socket/server

    server    local socket file or

    server    remote address of livestatus

=back

=head1 EXAMPLE

./dump.pl /tmp/live.sock

=head1 AUTHOR

2009, Sven Nierlein, <nierlein@cpan.org>

=cut

use warnings;
use strict;
use Data::Dumper;
use Getopt::Long;
use Pod::Usage;
use lib 'lib';
use lib '../lib';
use Nagios::MKLivestatus;

$Data::Dumper::Sortkeys = 1;

#########################################################################
# parse and check cmd line arguments
my ($opt_h, $opt_v, $opt_f);
Getopt::Long::Configure('no_ignore_case');
if(!GetOptions (
   "h"              => \$opt_h,
   "v"              => \$opt_v,
   "<>"             => \&add_file,
)) {
    pod2usage( { -verbose => 1, -message => 'error in options' } );
    exit 3;
}

if(defined $opt_h) {
    pod2usage( { -verbose => 1 } );
    exit 3;
}
my $verbose = 0;
if(defined $opt_v) {
    $verbose = 1;
}

if(!defined $opt_f) {
    pod2usage( { -verbose => 1, -message => 'socket/server is a required option' } );
    exit 3;
}

#########################################################################
my $nl;
if(index($opt_f, ':') > 0) {
    $nl = Nagios::MKLivestatus->new( server => $opt_f, verbose => $opt_v );
} else {
    $nl = Nagios::MKLivestatus->new( socket => $opt_f, verbose => $opt_v );
}

#########################################################################
my $hosts = $nl->selectall_hashref('GET hosts', 'name');
print Dumper($hosts);

#########################################################################
my $services = $nl->selectall_arrayref('GET services', { Slice => {}});
print Dumper($services);

#########################################################################
sub add_file {
    my $file = shift;
    $opt_f   = $file;
}
