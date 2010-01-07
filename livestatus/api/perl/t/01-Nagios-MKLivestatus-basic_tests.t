#!/usr/bin/env perl

#########################

use strict;
use Test::More tests => 24;
use File::Temp;
use Data::Dumper;
use IO::Socket::UNIX qw( SOCK_STREAM SOMAXCONN );
BEGIN { use_ok('Nagios::MKLivestatus') };

#########################
# get a temp file from File::Temp and replace it with our socket
my $fh = File::Temp->new(UNLINK => 0);
my $socket_path = $fh->filename;
unlink($socket_path);
my $listener = IO::Socket::UNIX->new(
                                    Type    => SOCK_STREAM,
                                    Listen  => SOMAXCONN,
                                    Local   => $socket_path,
                                  ) or die("failed to open $socket_path as test socket: $!");
#########################
# create object with single arg
my $nl = Nagios::MKLivestatus->new( $socket_path );
isa_ok($nl, 'Nagios::MKLivestatus', 'single args');
is($nl->peer_name(), $socket_path, 'get peer_name()');
is($nl->peer_addr(), $socket_path, 'get peer_addr()');

#########################
# create object with hash args
my $line_seperator        = 10;
my $column_seperator      = 0;
$nl = Nagios::MKLivestatus->new(
                                    verbose             => 0,
                                    socket              => $socket_path,
                                    line_seperator      => $line_seperator,
                                    column_seperator    => $column_seperator,
                                );
isa_ok($nl, 'Nagios::MKLivestatus', 'new hash args');
is($nl->peer_name(), $socket_path, 'get peer_name()');
is($nl->peer_addr(), $socket_path, 'get peer_addr()');

#########################
# create object with peer arg
$nl = Nagios::MKLivestatus->new(
                                    peer              => $socket_path,
                               );
isa_ok($nl, 'Nagios::MKLivestatus', 'peer hash arg socket');
is($nl->peer_name(), $socket_path, 'get peer_name()');
is($nl->peer_addr(), $socket_path, 'get peer_addr()');
isa_ok($nl->{'CONNECTOR'}, 'Nagios::MKLivestatus::UNIX', 'peer backend UNIX');

#########################
# create object with peer arg
my $server = 'localhost:12345';
$nl = Nagios::MKLivestatus->new(
                                    peer              => $server,
                               );
isa_ok($nl, 'Nagios::MKLivestatus', 'peer hash arg server');
is($nl->peer_name(), $server, 'get peer_name()');
is($nl->peer_addr(), $server, 'get peer_addr()');
isa_ok($nl->{'CONNECTOR'}, 'Nagios::MKLivestatus::INET', 'peer backend INET');

#########################
# create multi object with peers
$nl = Nagios::MKLivestatus->new(
                                    peer              => [ $server, $socket_path ],
                               );
isa_ok($nl, 'Nagios::MKLivestatus', 'peer hash arg multi');
my @names  = $nl->peer_name();
my @addrs  = $nl->peer_addr();
my $name   = $nl->peer_name();
my $expect = [ $server, $socket_path ];
is_deeply(\@names, $expect, 'list context get peer_name()') or diag("got peer names: ".Dumper(\@names)."but expected:  ".Dumper($expect));
is($name, 'multiple connector', 'scalar context get peer_name()') or diag("got peer name: ".Dumper($name)."but expected:  ".Dumper('multiple connector'));
is_deeply(\@addrs, $expect, 'list context get peer_addr()') or diag("got peer addrs: ".Dumper(\@addrs)."but expected:  ".Dumper($expect));

#########################
# create multi object with peers and name
$nl = Nagios::MKLivestatus->new(
                                    peer              => [ $server, $socket_path ],
                                    name              => 'test multi',
                               );
isa_ok($nl, 'Nagios::MKLivestatus', 'peer hash arg multi with name');
$name = $nl->peer_name();
is($name, 'test multi', 'peer_name()');

#########################
$nl = Nagios::MKLivestatus->new(
                                     peer        => [ $socket_path ],
                                     verbose     => 0,
                                     keepalive   => 1,
                                     logger      => undef,
                                );
isa_ok($nl, 'Nagios::MKLivestatus', 'peer hash arg multi with keepalive');
is($nl->peer_name(), $socket_path, 'get peer_name()');
is($nl->peer_addr(), $socket_path, 'get peer_addr()');

#########################
# cleanup
unlink($socket_path);
