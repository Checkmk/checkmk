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
    plan( tests => 9 );
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

my $author = 'Monitoring::Livestatus test';
for my $key (sort keys %{$objects_to_test}) {
    my $ml = $objects_to_test->{$key};
    isa_ok($ml, 'Monitoring::Livestatus');

    # we dont need warnings for testing
    $ml->warnings(0);

    #########################
    my $downtimes = $ml->selectall_arrayref("GET downtimes\nColumns: id");
    my $num_downtimes = 0;
    $num_downtimes = scalar @{$downtimes} if defined $downtimes;

    #########################
    # get a test host
    my $firsthost = $ml->selectscalar_value("GET hosts\nColumns: name\nLimit: 1");
    isnt($firsthost, undef, 'get test hostname') or BAIL_OUT($key.': got not test hostname');

    my $expect = "aa ²&é\"'''(§è!çà)- %s ''%s'' aa ~ € bb";
    #my $expect = "öäüß";
    my $teststrings = [
        $expect,
        "aa \x{c2}\x{b2}&\x{c3}\x{a9}\"'''(\x{c2}\x{a7}\x{c3}\x{a8}!\x{c3}\x{a7}\x{c3}\x{a0})- %s ''%s'' aa ~ \x{e2}\x{82}\x{ac} bb",
    ];
    for my $string (@{$teststrings}) {
        $ml->do('COMMAND ['.time().'] SCHEDULE_HOST_DOWNTIME;'.$firsthost.';'.time().';'.(time()+300).';1;0;300;'.$author.';'.$string);

        # sometimes it takes while till the downtime is accepted
        my $waited = 0;
        while($downtimes = $ml->selectall_arrayref("GET downtimes\nColumns: id comment", { Slice => 1 }) and scalar @{$downtimes} < $num_downtimes + 1) {
          print "waiting for the downtime...\n";
          sleep(1);
          $waited++;
          BAIL_OUT('waited 30 seconds for the downtime...') if $waited > 30;
        }

        my $last_downtime = pop @{$downtimes};
        #utf8::decode($expect);
        is($last_downtime->{'comment'}, $expect, 'get same utf8 comment: got '.Dumper($last_downtime));
    }
}
