#!/usr/bin/env perl

#########################

use strict;
use Test::More tests => 3;
use IO::Socket::INET;
BEGIN { use_ok('Nagios::MKLivestatus::UNIX') };

#########################
# create object with single arg
my $socket = "/tmp/blah.socket";
my $nl = Nagios::MKLivestatus::UNIX->new( $socket );
isa_ok($nl, 'Nagios::MKLivestatus', 'Nagios::MKLivestatus::UNIX->new()');

#########################
# create object with hash args
my $line_seperator        = 10;
my $column_seperator      = 0;
$nl = Nagios::MKLivestatus::UNIX->new(
                                    verbose             => 0,
                                    socket              => $socket,
                                    line_seperator      => $line_seperator,
                                    column_seperator    => $column_seperator,
                                );
isa_ok($nl, 'Nagios::MKLivestatus', 'Nagios::MKLivestatus::UNIX->new(%args)');
