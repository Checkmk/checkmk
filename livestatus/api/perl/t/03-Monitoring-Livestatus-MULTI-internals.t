#!/usr/bin/env perl

#########################

use strict;
use Test::More;
use Data::Dumper;
use File::Temp;
use IO::Socket::UNIX qw( SOCK_STREAM SOMAXCONN );
use_ok('Monitoring::Livestatus::MULTI');

BEGIN {
    if( $^O eq 'MSWin32' ) {
        plan skip_all => 'no sockets on windows';
    }
    else {
        plan tests => 57;
    }
}

#########################
# create 2 test sockets
# get a temp file from File::Temp and replace it with our socket
my $fh = File::Temp->new(UNLINK => 0);
my $socket_path1 = $fh->filename;
unlink($socket_path1);
my $listener1 = IO::Socket::UNIX->new(
                                    Type    => SOCK_STREAM,
                                    Listen  => SOMAXCONN,
                                    Local   => $socket_path1,
                                ) or die("failed to open $socket_path1 as test socket: $!");

$fh = File::Temp->new(UNLINK => 0);
my $socket_path2 = $fh->filename;
unlink($socket_path2);
my $listener2 = IO::Socket::UNIX->new(
                                    Type    => SOCK_STREAM,
                                    Listen  => SOMAXCONN,
                                    Local   => $socket_path2,
                                ) or die("failed to open $socket_path2 as test socket: $!");

#########################
# test the _merge_answer
my $mergetests = [
    {   # simple test for sliced selectall_arrayref
        in  => { '820e03551b95b42ec037c87aed9b8f4a' => [ { 'description' => 'test_flap_07',     'host_name' => 'test_host_000', 'state' => '0' }, { 'description' => 'test_flap_11',     'host_name' => 'test_host_000', 'state' => '0' } ],
                 '35bbb11a888f66131d429efd058fb141' => [ { 'description' => 'test_ok_00',       'host_name' => 'test_host_000', 'state' => '0' }, { 'description' => 'test_ok_01',       'host_name' => 'test_host_000', 'state' => '0' } ],
                 '70ea8fa14abb984761bdd45ef27685b0' => [ { 'description' => 'test_critical_00', 'host_name' => 'test_host_000', 'state' => '2' }, { 'description' => 'test_critical_19', 'host_name' => 'test_host_000', 'state' => '2' } ]
        },
        exp => [
                 { 'description' => 'test_flap_07',     'host_name' => 'test_host_000', 'state' => '0' },
                 { 'description' => 'test_flap_11',     'host_name' => 'test_host_000', 'state' => '0' },
                 { 'description' => 'test_ok_00',       'host_name' => 'test_host_000', 'state' => '0' },
                 { 'description' => 'test_ok_01',       'host_name' => 'test_host_000', 'state' => '0' },
                 { 'description' => 'test_critical_00', 'host_name' => 'test_host_000', 'state' => '2' },
                 { 'description' => 'test_critical_19', 'host_name' => 'test_host_000', 'state' => '2' },
               ]
    },
];

#########################
# test object creation
my $ml = Monitoring::Livestatus::MULTI->new( [ $socket_path1, $socket_path2 ] );
isa_ok($ml, 'Monitoring::Livestatus', 'single args sockets');
for my $peer (@{$ml->{'peers'}}) {
    isa_ok($peer, 'Monitoring::Livestatus::UNIX', 'single args sockets peer');
}

$ml = Monitoring::Livestatus::MULTI->new( [$socket_path1] );
isa_ok($ml, 'Monitoring::Livestatus', 'single array args socket');
for my $peer (@{$ml->{'peers'}}) {
    isa_ok($peer, 'Monitoring::Livestatus::UNIX', 'single array args socket peer');
    is($peer->peer_addr, $socket_path1, 'single arrays args socket peer addr');
    is($peer->peer_name, $socket_path1, 'single arrays args socket peer name');
}

$ml = Monitoring::Livestatus::MULTI->new( 'localhost:5001' );
isa_ok($ml, 'Monitoring::Livestatus', 'single args server');
for my $peer (@{$ml->{'peers'}}) {
    isa_ok($peer, 'Monitoring::Livestatus::INET', 'single args server peer');
    like($peer->peer_addr, qr/^localhost/, 'single args servers peer addr');
    like($peer->peer_name, qr/^localhost/, 'single args servers peer name');
}

$ml = Monitoring::Livestatus::MULTI->new( ['localhost:5001'] );
isa_ok($ml, 'Monitoring::Livestatus', 'single array args server');
for my $peer (@{$ml->{'peers'}}) {
    isa_ok($peer, 'Monitoring::Livestatus::INET', 'single arrays args server peer');
    like($peer->peer_addr, qr/^localhost/, 'single arrays args servers peer addr');
    like($peer->peer_name, qr/^localhost/, 'single arrays args servers peer name');
}

$ml = Monitoring::Livestatus::MULTI->new( [ 'localhost:5001', 'localhost:5002' ] );
isa_ok($ml, 'Monitoring::Livestatus', 'single args servers');
for my $peer (@{$ml->{'peers'}}) {
    isa_ok($peer, 'Monitoring::Livestatus::INET', 'single args servers peer');
    like($peer->peer_addr, qr/^localhost/, 'single args servers peer addr');
    like($peer->peer_name, qr/^localhost/, 'single args servers peer name');
}

$ml = Monitoring::Livestatus::MULTI->new( peer => [ 'localhost:5001', 'localhost:5002' ] );
isa_ok($ml, 'Monitoring::Livestatus', 'hash args servers');
for my $peer (@{$ml->{'peers'}}) {
    isa_ok($peer, 'Monitoring::Livestatus::INET', 'hash args servers peer');
    like($peer->peer_addr, qr/^localhost/, 'hash args servers peer addr');
    like($peer->peer_name, qr/^localhost/, 'hash args servers peer name');
}

$ml = Monitoring::Livestatus::MULTI->new( peer => [ $socket_path1, $socket_path2 ] );
isa_ok($ml, 'Monitoring::Livestatus', 'hash args sockets');
for my $peer (@{$ml->{'peers'}}) {
    isa_ok($peer, 'Monitoring::Livestatus::UNIX', 'hash args sockets peer');
}

$ml = Monitoring::Livestatus::MULTI->new( peer => { $socket_path1 => 'Location 1', $socket_path2 => 'Location2' } );
isa_ok($ml, 'Monitoring::Livestatus', 'hash args hashed sockets');
for my $peer (@{$ml->{'peers'}}) {
    isa_ok($peer, 'Monitoring::Livestatus::UNIX', 'hash args hashed sockets peer');
    like($peer->peer_name, qr/^Location/, 'hash args hashed sockets peer name');
}

$ml = Monitoring::Livestatus::MULTI->new( peer => { 'localhost:5001' => 'Location 1', 'localhost:5002' => 'Location2' } );
isa_ok($ml, 'Monitoring::Livestatus', 'hash args hashed servers');
for my $peer (@{$ml->{'peers'}}) {
    isa_ok($peer, 'Monitoring::Livestatus::INET', 'hash args hashed servers peer');
    like($peer->peer_addr, qr/^localhost/, 'hash args hashed servers peer addr');
    like($peer->peer_name, qr/^Location/, 'hash args hashed servers peer name');
}

$ml = Monitoring::Livestatus::MULTI->new( $socket_path1 );
isa_ok($ml, 'Monitoring::Livestatus', 'single args socket');
for my $peer (@{$ml->{'peers'}}) {
    isa_ok($peer, 'Monitoring::Livestatus::UNIX', 'single args socket peer');
}

#########################
# test internal subs
$ml = Monitoring::Livestatus::MULTI->new('peer' => ['192.168.123.2:9996', '192.168.123.2:9997', '192.168.123.2:9998' ] );

my $x = 0;
for my $test (@{$mergetests}) {
    my $got = $ml->_merge_answer($test->{'in'});
    is_deeply($got, $test->{'exp'}, '_merge_answer test '.$x)
        or diag("got: ".Dumper($got)."\nbut expected ".Dumper($test->{'exp'}));
    $x++;
}

#########################
# test the _sum_answer
my $sumtests = [
    { # hashes
        in  => { '192.168.123.2:9996' => { 'ok' => '12', 'warning' => '8' },
                 '192.168.123.2:9997' => { 'ok' => '17', 'warning' => '7' },
                 '192.168.123.2:9998' => { 'ok' => '13', 'warning' => '2' }
        },
        exp => { 'ok' => '42', 'warning' => '17' }
    },
    { # hashes, undefs
        in  => { '192.168.123.2:9996' => { 'ok' => '12', 'warning' => '8' },
                 '192.168.123.2:9997' => undef,
                 '192.168.123.2:9998' => { 'ok' => '13', 'warning' => '2' }
        },
        exp => { 'ok' => '25', 'warning' => '10' }
    },
    { # hashes, undefs
        in  => { '192.168.123.2:9996' => { 'ok' => '12', 'warning' => '8' },
                 '192.168.123.2:9997' => {},
                 '192.168.123.2:9998' => { 'ok' => '13', 'warning' => '2' }
        },
        exp => { 'ok' => '25', 'warning' => '10' }
    },
    { # arrays
        in  => { '192.168.123.2:9996' => [ '3302', '235' ],
                 '192.168.123.2:9997' => [ '3324', '236' ],
                 '192.168.123.2:9998' => [ '3274', '236' ]
        },
        exp => [ 9900, 707 ]
    },
    { # undefs / scalars
        in  => { 'e69322abf0352888e598da3e2514df4a' => undef,
                 'f42530d7e8c2b52732ba427b1e5e0a8e' => '1'
        },
        exp => 1,
    },
    { # arrays, undefs
        in  => { '192.168.123.2:9996' => [ '2', '5' ],
                 '192.168.123.2:9997' => [ ],
                 '192.168.123.2:9998' => [ '4', '6' ]
        },
        exp => [ 6, 11 ]
    },
    { # arrays, undefs
        in  => { '192.168.123.2:9996' => [ '2', '5' ],
                 '192.168.123.2:9997' => undef,
                 '192.168.123.2:9998' => [ '4', '6' ]
        },
        exp => [ 6, 11 ]
    },
];

$x = 1;
for my $test (@{$sumtests}) {
    my $got = $ml->_sum_answer($test->{'in'});
    is_deeply($got, $test->{'exp'}, '_sum_answer test '.$x)
        or diag("got: ".Dumper($got)."\nbut expected ".Dumper($test->{'exp'}));
    $x++;
}

#########################
# clone test
my $clone = $ml->_clone($mergetests);
is_deeply($clone, $mergetests, 'merge test clone');

$clone = $ml->_clone($sumtests);
is_deeply($clone, $sumtests, 'sum test clone');
