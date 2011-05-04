#!/usr/bin/env perl

=head1 NAME

test.pl - print some information from a socket

=head1 SYNOPSIS

./test.pl [ -h ] [ -v ] <socket|server>

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

./test.pl /tmp/live.sock

=head1 AUTHOR

2009, Sven Nierlein, <nierlein@cpan.org>

=cut

use warnings;
use strict;
use Data::Dumper;
use Getopt::Long;
use Pod::Usage;
use Time::HiRes qw( gettimeofday tv_interval );
use Log::Log4perl qw(:easy);
use lib 'lib';
use lib '../lib';
use Monitoring::Livestatus;

$Data::Dumper::Sortkeys = 1;

#########################################################################
# parse and check cmd line arguments
my ($opt_h, $opt_v, @opt_f);
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

if(scalar @opt_f == 0) {
    pod2usage( { -verbose => 1, -message => 'socket/server is a required option' } );
    exit 3;
}

#########################################################################
Log::Log4perl->easy_init($DEBUG);
my $nl = Monitoring::Livestatus->new(
                                     peer             => \@opt_f,
                                     verbose          => $opt_v,
                                     timeout          => 5,
                                     keepalive        => 1,
                                     logger           => get_logger(),
                                   );
my $log = get_logger();

#########################################################################
my $querys = [
    { 'query' => "GET hostgroups\nColumns: members\nFilter: name = flap\nFilter: name = down\nOr: 2",
      'sub'   => "selectall_arrayref",
      'opt'   => {Slice => 1 }
    },
#    { 'query' => "GET comments",
#      'sub'   => "selectall_arrayref",
#      'opt'   => {Slice => 1 }
#    },
#    { 'query' => "GET downtimes",
#      'sub'   => "selectall_arrayref",
#      'opt'   => {Slice => 1, Sum => 1}
#    },
#    { 'query' => "GET log\nFilter: time > ".(time() - 600)."\nLimit: 1",
#      'sub'   => "selectall_arrayref",
#      'opt'   => {Slice => 1, AddPeer => 1}
#    },
#    { 'query' => "GET services\nFilter: contacts >= test\nFilter: host_contacts >= test\nOr: 2\nColumns: host_name description contacts host_contacts",
#      'sub'   => "selectall_arrayref",
#      'opt'   => {Slice => 1, AddPeer => 0}
#    },
#    { 'query' => "GET services\nFilter: host_name = test_host_00\nFilter: description = test_flap_02\nOr: 2\nColumns: host_name description contacts host_contacts",
#      'sub'   => "selectall_arrayref",
#      'opt'   => {Slice => 1, AddPeer => 0}
#    },
];
for my $query (@{$querys}) {
    my $sub     = $query->{'sub'};
    my $t0      = [gettimeofday];
    my $stats   = $nl->$sub($query->{'query'}, $query->{'opt'});
    my $elapsed = tv_interval($t0);
    print Dumper($stats);
    print "Query took ".($elapsed)." seconds\n";
}


#########################################################################
sub add_file {
    my $file = shift;
    push @opt_f, $file;
}
