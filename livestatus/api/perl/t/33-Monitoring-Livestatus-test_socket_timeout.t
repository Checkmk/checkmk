#!/usr/bin/env perl

#########################

use strict;
use Test::More;
use Data::Dumper;

if ( !defined $ENV{TEST_SERVER} ) {
    my $msg = 'Author test.  Set $ENV{TEST_SOCKET} and $ENV{TEST_SERVER} to run';
    plan( skip_all => $msg );
} else {
    plan( tests => 7 );
}

# set an alarm
my $lastquery;
$SIG{ALRM} = sub {
    my @caller = caller;
    print STDERR 'last query: '.$lastquery if defined $lastquery;
    die "timeout reached:".Dumper(\@caller)."\n"
};
alarm(30);

use_ok('Monitoring::Livestatus');

#use Log::Log4perl qw(:easy);
#Log::Log4perl->easy_init($DEBUG);

#########################
# Test Query
#########################
my $statement    = "GET hosts\nColumns: alias\nFilter: name = host1";

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

    # we dont need warnings for testing
    $ml->warnings(0);

    #########################
    my $ary_ref  = $ml->selectall_arrayref($statement);
    is($Monitoring::Livestatus::ErrorCode, 0, 'Query Status 0');
    #is_deeply($ary_ref, $selectall_arrayref1, 'selectall_arrayref($statement)')
    #    or diag("got: ".Dumper($ary_ref)."\nbut expected ".Dumper($selectall_arrayref1));

    sleep(10);

    $ary_ref  = $ml->selectall_arrayref($statement);
    is($Monitoring::Livestatus::ErrorCode, 0, 'Query Status 0');
    #is_deeply($ary_ref, $selectall_arrayref1, 'selectall_arrayref($statement)')
    #    or diag("got: ".Dumper($ary_ref)."\nbut expected ".Dumper($selectall_arrayref1));

    #print Dumper($Monitoring::Livestatus::ErrorCode);
    #print Dumper($Monitoring::Livestatus::ErrorMessage);
}
