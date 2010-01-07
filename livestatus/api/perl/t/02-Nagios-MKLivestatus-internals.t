#!/usr/bin/env perl

#########################

use strict;
use Test::More tests => 14;
use File::Temp;
use Data::Dumper;
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
my $nl = Nagios::MKLivestatus->new( 'localhost:12345' );
isa_ok($nl, 'Nagios::MKLivestatus', 'single args server');
isa_ok($nl->{'CONNECTOR'}, 'Nagios::MKLivestatus::INET', 'single args server peer');
is($nl->{'CONNECTOR'}->peer_name, 'localhost:12345', 'single args server peer name');
is($nl->{'CONNECTOR'}->peer_addr, 'localhost:12345', 'single args server peer addr');

#########################
# create object with single arg
$nl = Nagios::MKLivestatus->new( $socket_path );
isa_ok($nl, 'Nagios::MKLivestatus', 'single args socket');
isa_ok($nl->{'CONNECTOR'}, 'Nagios::MKLivestatus::UNIX', 'single args socket peer');
is($nl->{'CONNECTOR'}->peer_name, $socket_path, 'single args socket peer name');
is($nl->{'CONNECTOR'}->peer_addr, $socket_path, 'single args socket peer addr');

my $header = "404          43\n";
my($error,$error_msg) = $nl->_parse_header($header);
is($error, '404', 'error code 404');
isnt($error_msg, undef, 'error code 404 message');

#########################
my $stats_query1 = "GET services
Stats: state = 0
Stats: state = 1
Stats: state = 2
Stats: state = 3
Stats: state = 4
Stats: host_state != 0
Stats: state = 1
StatsAnd: 2
Stats: host_state != 0
Stats: state = 2
StatsAnd: 2
Stats: host_state != 0
Stats: state = 3
StatsAnd: 2
Stats: host_state != 0
Stats: state = 3
Stats: active_checks = 1
StatsAnd: 3
Stats: state = 3
Stats: active_checks = 1
StatsOr: 2";
my @expected_keys1 = (
            'state = 0',
            'state = 1',
            'state = 2',
            'state = 3',
            'state = 4',
            'host_state != 0 && state = 1',
            'host_state != 0 && state = 2',
            'host_state != 0 && state = 3',
            'host_state != 0 && state = 3 && active_checks = 1',
            'state = 3 || active_checks = 1',
        );
my @got_keys1 = @{$nl->_extract_keys_from_stats_statement($stats_query1)};
is_deeply(\@got_keys1, \@expected_keys1, 'statsAnd, statsOr query keys')
    or ( diag('got keys: '.Dumper(\@got_keys1)) );


#########################
my $stats_query2 = "GET services
Stats: state = 0 as all_ok
Stats: state = 1 as all_warning
Stats: state = 2 as all_critical
Stats: state = 3 as all_unknown
Stats: state = 4 as all_pending
Stats: host_state != 0
Stats: state = 1
StatsAnd: 2 as all_warning_on_down_hosts
Stats: host_state != 0
Stats: state = 2
StatsAnd: 2 as all_critical_on_down_hosts
Stats: host_state != 0
Stats: state = 3
StatsAnd: 2 as all_unknown_on_down_hosts
Stats: host_state != 0
Stats: state = 3
Stats: active_checks_enabled = 1
StatsAnd: 3 as all_unknown_active_on_down_hosts
Stats: state = 3
Stats: active_checks_enabled = 1
StatsOr: 2 as all_active_or_unknown";
my @expected_keys2 = (
            'all_ok',
            'all_warning',
            'all_critical',
            'all_unknown',
            'all_pending',
            'all_warning_on_down_hosts',
            'all_critical_on_down_hosts',
            'all_unknown_on_down_hosts',
            'all_unknown_active_on_down_hosts',
            'all_active_or_unknown',
        );
my @got_keys2 = @{$nl->_extract_keys_from_stats_statement($stats_query2)};
is_deeply(\@got_keys2, \@expected_keys2, 'stats query keys2')
    or ( diag('got keys: '.Dumper(\@got_keys2)) );


#########################
my $normal_query1 = "GET services
Columns: host_name as host is_flapping description as name state
";
my @expected_keys3 = (
            'host',
            'is_flapping',
            'name',
            'state',
        );
my @got_keys3 = @{$nl->_extract_keys_from_columns_header($normal_query1)};
is_deeply(\@got_keys3, \@expected_keys3, 'normal query keys')
    or ( diag('got keys: '.Dumper(\@got_keys3)) );

#########################
unlink($socket_path);
