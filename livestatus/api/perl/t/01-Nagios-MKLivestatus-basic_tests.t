#!/usr/bin/env perl

#########################

use strict;
use Test::More tests => 3;
use File::Temp;
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
unlink($socket_path);