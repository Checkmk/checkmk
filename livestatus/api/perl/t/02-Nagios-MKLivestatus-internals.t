#!/usr/bin/env perl

#########################

use strict;
use Test::More tests => 4;
use File::Temp;
use IO::Socket::UNIX qw( SOCK_STREAM SOMAXCONN );
use_ok('Nagios::MKLivestatus');

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

my $header = "404          43\n";
my($error,$error_msg) = $nl->_parse_header($header);
is($error, '404', 'error code 404');
isnt($error_msg, undef, 'error code 404 message');

#########################
unlink($socket_path);
