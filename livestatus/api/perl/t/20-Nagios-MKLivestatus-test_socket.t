#!/usr/bin/env perl

#########################

use strict;
use Test::More;
use IO::Socket::UNIX qw( SOCK_STREAM SOMAXCONN );
use Data::Dumper;

BEGIN {
  eval {require threads;};
  if ( $@ ) {
    plan skip_all => 'need threads support for testing a real socket'
  }else{
    plan tests => 105
  }
}

use File::Temp;
BEGIN { use_ok('Nagios::MKLivestatus') };

#########################
# Normal Querys
#########################
my $line_seperator      = 10;
my $column_seperator    = 0;
my $test_data           = [ ["alias","name","contacts"],       # table header
                            ["alias1","host1","contact1"],     # row 1
                            ["alias2","host2","contact2"],     # row 2
                            ["alias3","host3","contact3"],     # row 3
                          ];
# expected results
my $selectall_arrayref1 = [ [ 'alias1', 'host1', 'contact1' ],
                            [ 'alias2', 'host2', 'contact2' ],
                            [ 'alias3', 'host3', 'contact3' ]
                          ];
my $selectall_arrayref2 = [
                            { 'contacts' => 'contact1', 'name' => 'host1', 'alias' => 'alias1' },
                            { 'contacts' => 'contact2', 'name' => 'host2', 'alias' => 'alias2' },
                            { 'contacts' => 'contact3', 'name' => 'host3', 'alias' => 'alias3' }
                          ];
my $selectall_hashref   = {
                            'host1' => { 'contacts' => 'contact1', 'name' => 'host1', 'alias' => 'alias1' },
                            'host2' => { 'contacts' => 'contact2', 'name' => 'host2', 'alias' => 'alias2' },
                            'host3' => { 'contacts' => 'contact3', 'name' => 'host3', 'alias' => 'alias3' }
                          };
my $selectcol_arrayref1 = [ 'alias1', 'alias2', 'alias3' ];
my $selectcol_arrayref2 = [ 'alias1', 'host1', 'alias2', 'host2', 'alias3', 'host3' ];
my $selectcol_arrayref3 = [ 'alias1', 'host1', 'contact1', 'alias2', 'host2', 'contact2', 'alias3', 'host3', 'contact3' ];
my @selectrow_array     = ( 'alias1', 'host1', 'contact1' );
my $selectrow_arrayref  = [ 'alias1', 'host1', 'contact1' ];
my $selectrow_hashref   = { 'contacts' => 'contact1', 'name' => 'host1', 'alias' => 'alias1' };

#########################
# Single Querys
#########################
my $single_statement    = "GET hosts\nColumns: alias\nFilter: name = host1";
my $select_scalar_value = 'alias1';

#########################
# Stats Querys
#########################
my $stats_statement = "GET services\nStats: state = 0\nStats: state = 1\nStats: state = 2\nStats: state = 3";
my $stats_data      = [[4297,13,9,0]];

# expected results
my $stats_selectall_arrayref1 = [ [4297,13,9,0] ];
my $stats_selectall_arrayref2 = [ { 'state = 0' => '4297', 'state = 1' => '13', 'state = 2' => '9', 'state = 3' => 0 } ];
my $stats_selectcol_arrayref  = [ '4297' ];
my @stats_selectrow_array     = ( '4297', '13', '9', '0' );
my $stats_selectrow_arrayref  = [ '4297', '13', '9', '0' ];
my $stats_selectrow_hashref   = { 'state = 0' => '4297', 'state = 1' => '13', 'state = 2' => '9', 'state = 3' => 0 };

#########################
# Empty Querys
#########################
my $empty_statement = "GET services\nFilter: description = empty";

# expected results
my $empty_selectall_arrayref = [];
my $empty_selectcol_arrayref = [];
my @empty_selectrow_array;
my $empty_selectrow_arrayref;
my $empty_selectrow_hashref;


#########################
# get a temp file from File::Temp and replace it with our socket
my $fh = File::Temp->new(UNLINK => 0);
my $socket_path = $fh->filename;
unlink($socket_path);
my $thr1 = threads->create('create_socket', 'unix');
#########################
# get a temp file from File::Temp and replace it with our socket
my $server              = 'localhost:32987';
my $thr2 = threads->create('create_socket', 'inet');
sleep(1);

#########################
my $objects_to_test = {
  # create unix object with hash args
  'unix_hash_args' => Nagios::MKLivestatus->new(
                                      verbose             => 0,
                                      socket              => $socket_path,
                                      line_seperator      => $line_seperator,
                                      column_seperator    => $column_seperator,
                                    ),

  # create unix object with a single arg
  'unix_single_arg' => Nagios::MKLivestatus::UNIX->new( $socket_path ),

  # create inet object with hash args
  'inet_hash_args' => Nagios::MKLivestatus->new(
                                      verbose             => 0,
                                      server              => $server,
                                      line_seperator      => $line_seperator,
                                      column_seperator    => $column_seperator,
                                    ),

  # create inet object with a single arg
  'inet_single_arg' => Nagios::MKLivestatus::INET->new( $server ),

};

for my $key (keys %{$objects_to_test}) {
    my $nl = $objects_to_test->{$key};
    isa_ok($nl, 'Nagios::MKLivestatus');

    # we dont need warnings for testing
    $nl->warnings(0);

    ##################################################
    # test settings
    my $rt = $nl->verbose(1);
    is($rt, '0', 'enable verbose');
    $rt = $nl->verbose(0);
    is($rt, '1', 'disable verbose');

    $rt = $nl->errors_are_fatal(0);
    is($rt, '1', 'disable errors_are_fatal');
    $rt = $nl->errors_are_fatal(1);
    is($rt, '0', 'enable errors_are_fatal');

    ##################################################
    # do some sample querys
    my $statement = "GET hosts";

    #########################
    my $ary_ref  = $nl->selectall_arrayref($statement);
    is_deeply($ary_ref, $selectall_arrayref1, 'selectall_arrayref($statement)')
        or diag("got: ".Dumper($ary_ref)."\nbut expected ".Dumper($selectall_arrayref1));

    #########################
    $ary_ref  = $nl->selectall_arrayref($statement, { Slice => {} });
    is_deeply($ary_ref, $selectall_arrayref2, 'selectall_arrayref($statement, { Slice => {} })')
        or diag("got: ".Dumper($ary_ref)."\nbut expected ".Dumper($selectall_arrayref2));

    #########################
    my $hash_ref = $nl->selectall_hashref($statement, 'name');
    is_deeply($hash_ref, $selectall_hashref, 'selectall_hashref($statement, "name")')
        or diag("got: ".Dumper($hash_ref)."\nbut expected ".Dumper($selectall_hashref));

    #########################
    $ary_ref  = $nl->selectcol_arrayref($statement);
    is_deeply($ary_ref, $selectcol_arrayref1, 'selectcol_arrayref($statement)')
        or diag("got: ".Dumper($ary_ref)."\nbut expected ".Dumper($selectcol_arrayref1));

    #########################
    $ary_ref = $nl->selectcol_arrayref($statement, { Columns=>[1,2] });
    is_deeply($ary_ref, $selectcol_arrayref2, 'selectcol_arrayref($statement, { Columns=>[1,2] })')
        or diag("got: ".Dumper($ary_ref)."\nbut expected ".Dumper($selectcol_arrayref2));

    $ary_ref = $nl->selectcol_arrayref($statement, { Columns=>[1,2,3] });
    is_deeply($ary_ref, $selectcol_arrayref3, 'selectcol_arrayref($statement, { Columns=>[1,2,3] })')
        or diag("got: ".Dumper($ary_ref)."\nbut expected ".Dumper($selectcol_arrayref3));

    #########################
    my @row_ary  = $nl->selectrow_array($statement);
    is_deeply(\@row_ary, \@selectrow_array, 'selectrow_array($statement)')
        or diag("got: ".Dumper(\@row_ary)."\nbut expected ".Dumper(\@selectrow_array));

    #########################
    $ary_ref  = $nl->selectrow_arrayref($statement);
    is_deeply($ary_ref, $selectrow_arrayref, 'selectrow_arrayref($statement)')
        or diag("got: ".Dumper($ary_ref)."\nbut expected ".Dumper($selectrow_arrayref));

    #########################
    $hash_ref = $nl->selectrow_hashref($statement);
    is_deeply($hash_ref, $selectrow_hashref, 'selectrow_hashref($statement)')
        or diag("got: ".Dumper($hash_ref)."\nbut expected ".Dumper($selectrow_hashref));

    ##################################################
    # stats querys
    ##################################################
    $ary_ref  = $nl->selectall_arrayref($stats_statement);
    is_deeply($ary_ref, $stats_selectall_arrayref1, 'selectall_arrayref($stats_statement)')
        or diag("got: ".Dumper($ary_ref)."\nbut expected ".Dumper($stats_selectall_arrayref1));

    $ary_ref  = $nl->selectall_arrayref($stats_statement, { Slice => {} });
    is_deeply($ary_ref, $stats_selectall_arrayref2, 'selectall_arrayref($stats_statement, { Slice => {} })')
        or diag("got: ".Dumper($ary_ref)."\nbut expected ".Dumper($stats_selectall_arrayref2));

    $ary_ref  = $nl->selectcol_arrayref($stats_statement);
    is_deeply($ary_ref, $stats_selectcol_arrayref, 'selectcol_arrayref($stats_statement)')
        or diag("got: ".Dumper($ary_ref)."\nbut expected ".Dumper($stats_selectcol_arrayref));

    @row_ary = $nl->selectrow_array($stats_statement);
    is_deeply(\@row_ary, \@stats_selectrow_array, 'selectrow_arrayref($stats_statement)')
        or diag("got: ".Dumper(\@row_ary)."\nbut expected ".Dumper(\@stats_selectrow_array));

    $ary_ref  = $nl->selectrow_arrayref($stats_statement);
    is_deeply($ary_ref, $stats_selectrow_arrayref, 'selectrow_arrayref($stats_statement)')
        or diag("got: ".Dumper($ary_ref)."\nbut expected ".Dumper($stats_selectrow_arrayref));

    $hash_ref = $nl->selectrow_hashref($stats_statement);
    is_deeply($hash_ref, $stats_selectrow_hashref, 'selectrow_hashref($stats_statement)')
        or diag("got: ".Dumper($hash_ref)."\nbut expected ".Dumper($stats_selectrow_hashref));

    my $scal = $nl->select_scalar_value($single_statement);
    is($scal, $select_scalar_value, 'select_scalar_value($single_statement)')
        or diag("got: ".Dumper($scal)."\nbut expected ".Dumper($select_scalar_value));

    ##################################################
    # empty querys
    ##################################################
    $ary_ref  = $nl->selectall_arrayref($empty_statement);
    is_deeply($ary_ref, $empty_selectall_arrayref, 'selectall_arrayref($empty_statement)')
        or diag("got: ".Dumper($ary_ref)."\nbut expected ".Dumper($empty_selectall_arrayref));

    $ary_ref  = $nl->selectcol_arrayref($empty_statement);
    is_deeply($ary_ref, $empty_selectcol_arrayref, 'selectcol_arrayref($empty_statement)')
        or diag("got: ".Dumper($ary_ref)."\nbut expected ".Dumper($empty_selectcol_arrayref));

    @row_ary = $nl->selectrow_array($empty_statement);
    is_deeply(\@row_ary, \@empty_selectrow_array, 'selectrow_arrayref($empty_statement)')
        or diag("got: ".Dumper(\@row_ary)."\nbut expected ".Dumper(\@empty_selectrow_array));

    $ary_ref  = $nl->selectrow_arrayref($empty_statement);
    is_deeply($ary_ref, $empty_selectrow_arrayref, 'selectrow_arrayref($empty_statement)')
        or diag("got: ".Dumper($ary_ref)."\nbut expected ".Dumper($empty_selectrow_arrayref));

    $hash_ref = $nl->selectrow_hashref($empty_statement);
    is_deeply($hash_ref, $empty_selectrow_hashref, 'selectrow_hashref($empty_statement)')
        or diag("got: ".Dumper($hash_ref)."\nbut expected ".Dumper($empty_selectrow_hashref));

}

##################################################
# exit threads
$thr1->kill('KILL')->detach();
$thr2->kill('KILL')->detach();
exit;


#########################
# SUBS
#########################
# test socket server
sub create_socket {
    my $type = shift;
    my $listener;

    if($type eq 'unix') {
      print "creating unix socket\n";
      $listener = IO::Socket::UNIX->new(
                                        Type    => SOCK_STREAM,
                                        Listen  => SOMAXCONN,
                                        Local   => $socket_path,
                                      ) or die("failed to open $socket_path as test socket: $!");
    }
    elsif($type eq 'inet') {
            print "creating tcp socket\n";
      $listener = IO::Socket::INET->new(
                                        LocalAddr  => $server,
                                        Proto      => 'tcp',
                                        Listen     => 1,
                                        Reuse      => 1,
                                      ) or die("failed to listen on $server: $!");
    } else {
      die("unknown type");
    }
    while( my $socket = $listener->accept() or die('cannot accept: $!') ) {
        my $recv = "";
        while(<$socket>) { $recv .= $_; }
        my $data;
        my $status = 200;
        if($recv =~ m/^GET .*?\s+Filter:.*?empty/m) {
            $data = '';
        }
        elsif($recv =~ m/^GET hosts\s+Columns: alias/m) {
            $data = join( chr($line_seperator), map( join( chr($column_seperator), $_->[0]), @{$test_data}[1..3] ) )."\n";
        }
        elsif($recv =~ m/^GET hosts\s+Columns: name/m) {
            $data = join( chr($line_seperator), map( join( chr($column_seperator), $_->[1]), @{$test_data}[1..3] ) )."\n";
        }
        elsif($recv =~ m/^GET hosts/) {
            $data = join( chr($line_seperator), map( join( chr($column_seperator), @{$_}), @{$test_data} ) )."\n";
        }
        elsif($recv =~ m/^GET services/ and $recv =~ m/Stats:/m) {
            $data = join( chr($line_seperator), map( join( chr($column_seperator), @{$_}), @{$stats_data} ) )."\n";
        }
        my $content_length = sprintf("%11s", length($data));
        print $socket $status." ".$content_length."\n";
        print $socket $data;
        close($socket);
    }
    unlink($socket_path);
}
