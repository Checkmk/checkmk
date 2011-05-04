#!/usr/bin/env perl

#########################

use strict;
use Test::More;
use Data::Dumper;

if ( ! defined $ENV{TEST_SOCKET} or !defined $ENV{TEST_SERVER} ) {
    my $msg = 'Author test.  Set $ENV{TEST_SOCKET} and $ENV{TEST_SERVER} to run';
    plan( skip_all => $msg );
} else {
    plan( tests => 22 );
}

use_ok('Monitoring::Livestatus::MULTI');

#########################
# create new test object
my $objects_to_test = {
    'multi_one'   => Monitoring::Livestatus::MULTI->new( peer => [ $ENV{TEST_SERVER}                    ], warnings => 0 ),
    'multi_two'   => Monitoring::Livestatus::MULTI->new( peer => [ $ENV{TEST_SERVER}, $ENV{TEST_SOCKET} ], warnings => 0 ),
    'multi_three' => Monitoring::Livestatus::MULTI->new(
          'verbose'  => '0',
          'warnings' => '0',
          'timeout'  => '10',
          'peer' => [
                      { 'name' => 'Mon 1', 'peer' => $ENV{TEST_SERVER} },
                      { 'name' => 'Mon 2', 'peer' => $ENV{TEST_SOCKET} },
                    ],
          'keepalive' => '1'
    ),
};

# dont die on errors
#$ml->errors_are_fatal(0);

for my $key (keys %{$objects_to_test}) {
    my $ml = $objects_to_test->{$key};
    isa_ok($ml, 'Monitoring::Livestatus::MULTI') or BAIL_OUT("no need to continue without a proper Monitoring::Livestatus::MULTI object");

    #########################
    # DATA INTEGRITY
    #########################

    my $statement = "GET hosts\nColumns: state name alias\nLimit: 1";
    my $data1     = $ml->selectall_arrayref($statement, {Slice => 1});
    my $data2     = $ml->selectall_arrayref($statement, {Slice => 1, AddPeer => 1});
    for my $data (@{$data2}) {
        delete $data->{'peer_name'};
        delete $data->{'peer_addr'};
        delete $data->{'peer_key'};
    }
    is_deeply($data1, $data2, "data integrity with peers added and Column");

    $statement = "GET hosts\nLimit: 1";
    $data1     = $ml->selectall_arrayref($statement, {Slice => 1, Deepcopy => 1});
    $data2     = $ml->selectall_arrayref($statement, {Slice => 1, AddPeer => 1, Deepcopy => 1});
    for my $data (@{$data2}) {
        delete $data->{'peer_name'};
        delete $data->{'peer_addr'};
        delete $data->{'peer_key'};
    }
    is_deeply($data1, $data2, "data integrity with peers added without Columns");

    #########################
    # try to change result set to scalar
    for my $data (@{$data1}) { $data->{'peer_name'} = 1; }
    for my $data (@{$data2}) { $data->{'peer_name'} = 1; }
    is_deeply($data1, $data2, "data integrity with changed result set");

    #########################
    # try to change result set to hash
    for my $data (@{$data1}) { $data->{'peer_name'} = {}; }
    for my $data (@{$data2}) { $data->{'peer_name'} = {}; }
    is_deeply($data1, $data2, "data integrity with changed result set");

    #########################
    # BACKENDS
    #########################
    my @backends = $ml->peer_key();
    $data1 = $ml->selectall_arrayref($statement, {Slice => 1});
    $data2 = $ml->selectall_arrayref($statement, {Slice => 1, Backend => \@backends });
    is_deeply($data1, $data2, "data integrity with backends");

    #########################
    # BUGS
    #########################

    #########################
    # Bug: Can't use string ("flap") as an ARRAY ref while "strict refs" in use at Monitoring/Livestatus/MULTI.pm line 206.
    $statement = "GET servicegroups\nColumns: name alias\nFilter: name = flap\nLimit: 1";
    $data1 = $ml->selectrow_array($statement);
    isnt($data1, undef, "bug check: Can't use string (\"group\")...");
}
