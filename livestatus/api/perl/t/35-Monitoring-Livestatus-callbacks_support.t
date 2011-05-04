#!/usr/bin/env perl

#########################

use strict;
use Encode;
use Test::More;
use Data::Dumper;

if ( !defined $ENV{TEST_SERVER} ) {
    my $msg = 'Author test.  Set $ENV{TEST_SOCKET} and $ENV{TEST_SERVER} to run';
    plan( skip_all => $msg );
} else {
    plan( tests => 15 );
}

use_ok('Monitoring::Livestatus');

#use Log::Log4perl qw(:easy);
#Log::Log4perl->easy_init($DEBUG);

#########################
my $objects_to_test = {
  # create inet object with hash args
  '01 inet_hash_args' => Monitoring::Livestatus->new(
                                      verbose                     => 0,
                                      server                      => $ENV{TEST_SERVER},
                                      keepalive                   => 1,
                                      timeout                     => 3,
                                      retries_on_connection_error => 0,
#                                      logger                     => get_logger(),
                                    ),

  # create inet object with a single arg
  '02 inet_single_arg' => Monitoring::Livestatus::INET->new( $ENV{TEST_SERVER} ),
};

for my $key (sort keys %{$objects_to_test}) {
    my $ml = $objects_to_test->{$key};
    isa_ok($ml, 'Monitoring::Livestatus');

    my $got = $ml->selectall_arrayref("GET hosts\nColumns: name alias state\nLimit: 1", { Slice => 1, callbacks => { 'c1' => sub { return $_[0]->{'alias'}; } } });
    isnt($got->[0]->{'alias'}, undef, 'got a test host');
    is($got->[0]->{'alias'}, $got->[0]->{'c1'}, 'callback for sliced results');

    $got = $ml->selectall_arrayref("GET hosts\nColumns: name alias state\nLimit: 1", { Slice => 1, callbacks => { 'name' => sub { return $_[0]->{'alias'}; } } });
    isnt($got->[0]->{'alias'}, undef, 'got a test host');
    is($got->[0]->{'alias'}, $got->[0]->{'name'}, 'callback for sliced results which overwrites key');

    $got = $ml->selectall_arrayref("GET hosts\nColumns: name alias state\nLimit: 1", { callbacks => { 'c1' => sub { return $_[0]->[1]; } } });
    isnt($got->[0]->[1], undef, 'got a test host');
    is($got->[0]->[1], $got->[0]->[3], 'callback for non sliced results');
}
