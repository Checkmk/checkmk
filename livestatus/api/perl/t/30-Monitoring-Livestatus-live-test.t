#!/usr/bin/env perl

#########################

use strict;
use Test::More;
use Data::Dumper;

if ( ! defined $ENV{TEST_SOCKET} or !defined $ENV{TEST_SERVER} ) {
    my $msg = 'Author test.  Set $ENV{TEST_SOCKET} and $ENV{TEST_SERVER} to run';
    plan( skip_all => $msg );
} else {
    plan( tests => 727 );
}

# set an alarm
my $lastquery;
$SIG{ALRM} = sub {
    my @caller = caller;
    print STDERR 'last query: '.$lastquery if defined $lastquery;
    die "timeout reached:".Dumper(\@caller)."\n" 
};
alarm(120);

use_ok('Monitoring::Livestatus');

#########################
my $line_seperator      = 10;
my $column_seperator    = 0;
my $objects_to_test = {
  # UNIX
  # create unix object with a single arg
#  '01 unix_single_arg' => Monitoring::Livestatus::UNIX->new( $ENV{TEST_SOCKET} ),

  # create unix object with hash args
  '02 unix_few_args' => Monitoring::Livestatus->new(
                                      #verbose             => 1,
                                      socket              => $ENV{TEST_SOCKET},
                                      line_seperator      => $line_seperator,
                                      column_seperator    => $column_seperator,
                                    ),

  # create unix object with hash args
  '03 unix_keepalive' => Monitoring::Livestatus->new(
                                      verbose             => 0,
                                      socket              => $ENV{TEST_SOCKET},
                                      keepalive           => 1,
                                    ),

  # TCP
  # create inet object with a single arg
  '04 inet_single_arg' => Monitoring::Livestatus::INET->new( $ENV{TEST_SERVER} ),

  # create inet object with hash args
  '05 inet_few_args' => Monitoring::Livestatus->new(
                                      verbose             => 0,
                                      server              => $ENV{TEST_SERVER},
                                      line_seperator      => $line_seperator,
                                      column_seperator    => $column_seperator,
                                    ),


  # create inet object with keepalive
  '06 inet_keepalive' => Monitoring::Livestatus->new(
                                      verbose             => 0,
                                      server              => $ENV{TEST_SERVER},
                                      keepalive           => 1,
                                    ),

  # create multi single args
  '07 multi_keepalive' => Monitoring::Livestatus->new( [ $ENV{TEST_SERVER}, $ENV{TEST_SOCKET} ] ),

  # create multi object with keepalive
  '08 multi_keepalive_hash_args' => Monitoring::Livestatus->new(
                                      verbose             => 0,
                                      peer                => [ $ENV{TEST_SERVER}, $ENV{TEST_SOCKET} ],
                                      keepalive           => 1,
                                    ),

  # create multi object without keepalive
  '09 multi_no_keepalive' => Monitoring::Livestatus->new(
                                      peer                => [ $ENV{TEST_SERVER}, $ENV{TEST_SOCKET} ],
                                      keepalive           => 0,
                                    ),

  # create multi object without threads
  '10 multi_no_threads' => Monitoring::Livestatus->new(
                                      peer                => [ $ENV{TEST_SERVER}, $ENV{TEST_SOCKET} ],
                                      use_threads         => 0,
                                    ),

  # create multi object with only one peer
  '11 multi_one_peer' => Monitoring::Livestatus::MULTI->new(
                                      peer                => $ENV{TEST_SERVER},
                                    ),

  # create multi object without threads
  '12 multi_two_peers' => Monitoring::Livestatus::MULTI->new(
                                      peer                => [ $ENV{TEST_SERVER}, $ENV{TEST_SOCKET} ],
                                    ),
};

my $expected_keys = {
    'columns'       => [
                         'description','name','table','type'
                       ],
    'commands'      => [
                         'line','name'
                       ],
    'comments'      => [
                         '__all_from_hosts__', '__all_from_services__',
                         'author','comment','entry_time','entry_type','expire_time','expires', 'id','persistent',
                         'source','type'
                       ],
    'contacts'      => [
                         'address1','address2','address3','address4','address5','address6','alias',
                         'can_submit_commands','custom_variable_names','custom_variable_values','email',
                         'host_notification_period','host_notifications_enabled','in_host_notification_period',
                         'in_service_notification_period','name','modified_attributes','modified_attributes_list',
                         'pager','service_notification_period','service_notifications_enabled'
                       ],
    'contactgroups' => [ 'name', 'alias', 'members' ],
    'downtimes'     => [
                         '__all_from_hosts__', '__all_from_services__',
                         'author','comment','duration','end_time','entry_time','fixed','id','start_time',
                         'triggered_by','type'
                       ],
    'hostgroups'    => [
                         'action_url','alias','members','name','members_with_state','notes','notes_url','num_hosts','num_hosts_down',
                         'num_hosts_pending','num_hosts_unreach','num_hosts_up','num_services','num_services_crit',
                         'num_services_hard_crit','num_services_hard_ok','num_services_hard_unknown',
                         'num_services_hard_warn','num_services_ok','num_services_pending','num_services_unknown',
                         'num_services_warn','worst_host_state','worst_service_hard_state','worst_service_state'
                       ],
    'hosts'         => [
                         'accept_passive_checks','acknowledged','acknowledgement_type','action_url','action_url_expanded',
                         'active_checks_enabled','address','alias','check_command','check_freshness','check_interval',
                         'check_options','check_period','check_type','checks_enabled','childs','comments','comments_with_info',
                         'contacts','current_attempt','current_notification_number','custom_variable_names',
                         'custom_variable_values','display_name','downtimes','downtimes_with_info','event_handler_enabled',
                         'execution_time','first_notification_delay','flap_detection_enabled','groups','hard_state','has_been_checked',
                         'high_flap_threshold','icon_image','icon_image_alt','icon_image_expanded','in_check_period',
                         'in_notification_period','initial_state','is_executing','is_flapping','last_check','last_hard_state',
                         'last_hard_state_change','last_notification','last_state','last_state_change','latency','last_time_down',
                         'last_time_unreachable','last_time_up','long_plugin_output','low_flap_threshold','max_check_attempts','name',
                         'modified_attributes','modified_attributes_list','next_check',
                         'next_notification','notes','notes_expanded','notes_url','notes_url_expanded','notification_interval',
                         'notification_period','notifications_enabled','num_services','num_services_crit','num_services_hard_crit',
                         'num_services_hard_ok','num_services_hard_unknown','num_services_hard_warn','num_services_ok',
                         'num_services_pending','num_services_unknown','num_services_warn','obsess_over_host','parents',
                         'pending_flex_downtime','percent_state_change','perf_data','plugin_output',
                         'process_performance_data','retry_interval','scheduled_downtime_depth','services','services_with_state',
                         'state','state_type','statusmap_image','total_services','worst_service_hard_state','worst_service_state',
                         'x_3d','y_3d','z_3d'
                       ],
    'hostsbygroup'  => [
                         '__all_from_hosts__', '__all_from_hostgroups__'
                       ],
    'log'           => [
                         '__all_from_hosts__','__all_from_services__','__all_from_contacts__','__all_from_commands__',
                         'attempt','class','command_name','comment','contact_name','host_name','lineno','message','options',
                         'plugin_output','service_description','state','state_type','time','type'
                       ],
    'servicegroups' => [
                         'action_url','alias','members','name','members_with_state','notes','notes_url','num_services','num_services_crit',
                         'num_services_hard_crit','num_services_hard_ok','num_services_hard_unknown',
                         'num_services_hard_warn','num_services_ok','num_services_pending','num_services_unknown',
                         'num_services_warn','worst_service_state'
                       ],
    'servicesbygroup' => [
                         '__all_from_services__', '__all_from_hosts__', '__all_from_servicegroups__'
                       ],
    'services'      => [
                         '__all_from_hosts__',
                         'accept_passive_checks','acknowledged','acknowledgement_type','action_url','action_url_expanded',
                         'active_checks_enabled','check_command','check_interval','check_options','check_period',
                         'check_type','checks_enabled','comments','comments_with_info','contacts','current_attempt',
                         'current_notification_number','custom_variable_names','custom_variable_values',
                         'description','display_name','downtimes','downtimes_with_info','event_handler','event_handler_enabled',
                         'execution_time','first_notification_delay','flap_detection_enabled','groups',
                         'has_been_checked','high_flap_threshold','icon_image','icon_image_alt','icon_image_expanded','in_check_period',
                         'in_notification_period','initial_state','is_executing','is_flapping','last_check',
                         'last_hard_state','last_hard_state_change','last_notification','last_state',
                         'last_state_change','latency','last_time_critical','last_time_ok','last_time_unknown','last_time_warning',
                         'long_plugin_output','low_flap_threshold','max_check_attempts','modified_attributes','modified_attributes_list',
                         'next_check','next_notification','notes','notes_expanded','notes_url','notes_url_expanded',
                         'notification_interval','notification_period','notifications_enabled','obsess_over_service',
                         'percent_state_change','perf_data','plugin_output','process_performance_data','retry_interval',
                         'scheduled_downtime_depth','state','state_type'
                       ],
    'servicesbyhostgroup' => [
                         '__all_from_services__', '__all_from_hosts__', '__all_from_hostgroups__'
                       ],
    'status'        => [
                         'accept_passive_host_checks','accept_passive_service_checks','cached_log_messages',
                         'check_external_commands','check_host_freshness','check_service_freshness','connections',
                         'connections_rate','enable_event_handlers','enable_flap_detection','enable_notifications',
                         'execute_host_checks','execute_service_checks','forks','forks_rate','host_checks','host_checks_rate','interval_length',
                         'last_command_check','last_log_rotation','livestatus_version','log_messages','log_messages_rate','nagios_pid','neb_callbacks',
                         'neb_callbacks_rate','obsess_over_hosts','obsess_over_services','process_performance_data',
                         'program_start','program_version','requests','requests_rate','service_checks','service_checks_rate'
                       ],
    'timeperiods'   => [ 'in', 'name', 'alias' ],
};

my $author = 'Monitoring::Livestatus test';
for my $key (sort keys %{$objects_to_test}) {
    my $ml = $objects_to_test->{$key};
    isa_ok($ml, 'Monitoring::Livestatus') or BAIL_OUT("no need to continue without a proper Monitoring::Livestatus object: ".$key);

    # dont die on errors
    $ml->errors_are_fatal(0);
    $ml->warnings(0);

    #########################
    # set downtime for a host and service
    my $downtimes = $ml->selectall_arrayref("GET downtimes\nColumns: id");
    my $num_downtimes = 0;
    $num_downtimes = scalar @{$downtimes} if defined $downtimes;
    my $firsthost = $ml->selectscalar_value("GET hosts\nColumns: name\nLimit: 1");
    isnt($firsthost, undef, 'get test hostname') or BAIL_OUT($key.': got not test hostname');
    $ml->do('COMMAND ['.time().'] SCHEDULE_HOST_DOWNTIME;'.$firsthost.';'.time().';'.(time()+300).';1;0;300;'.$author.';perl test: '.$0);
    my $firstservice = $ml->selectscalar_value("GET services\nColumns: description\nFilter: host_name = $firsthost\nLimit: 1");
    isnt($firstservice, undef, 'get test servicename') or BAIL_OUT('got not test servicename');
    $ml->do('COMMAND ['.time().'] SCHEDULE_SVC_DOWNTIME;'.$firsthost.';'.$firstservice.';'.time().';'.(time()+300).';1;0;300;'.$author.';perl test: '.$0);
    # sometimes it takes while till the downtime is accepted
    my $waited = 0;
    while(scalar @{$ml->selectall_arrayref("GET downtimes\nColumns: id")} < $num_downtimes + 2) {
      print "waiting for the downtime...\n";
      sleep(1);
      $waited++;
      BAIL_OUT('waited 30 seconds for the downtime...') if $waited > 30;
    }
    #########################

    #########################
    # check tables
    my $data            = $ml->selectall_hashref("GET columns\nColumns: table", 'table');
    my @tables          = sort keys %{$data};
    my @expected_tables = sort keys %{$expected_keys};
    is_deeply(\@tables, \@expected_tables, $key.' tables') or BAIL_OUT("got tables:\n".join(', ', @tables)."\nbut expected\n".join(', ', @expected_tables));

    #########################
    # check keys
    for my $type (keys %{$expected_keys}) {
        my $filter = "";
        $filter  = "Filter: time > ".(time() - 86400)."\n" if $type eq 'log';
        $filter .= "Filter: time < ".(time())."\n"         if $type eq 'log';
        my $expected_keys = get_expected_keys($type);
        my $statement = "GET $type\n".$filter."Limit: 1";
        $lastquery = $statement;
        my $hash_ref  = $ml->selectrow_hashref($statement );
        undef $lastquery;
        is(ref $hash_ref, 'HASH', $type.' keys are a hash') or BAIL_OUT($type.'keys are not in hash format, got '.Dumper($hash_ref));
        my @keys      = sort keys %{$hash_ref};
        is_deeply(\@keys, $expected_keys, $key.' '.$type.' table columns') or BAIL_OUT("got $type keys:\n".join(', ', @keys)."\nbut expected\n".join(', ', @{$expected_keys}));
    }

    my $statement = "GET hosts\nColumns: name as hostname state\nLimit: 1";
    $lastquery = $statement;
    my $hash_ref  = $ml->selectrow_hashref($statement);
    undef $lastquery;
    isnt($hash_ref, undef, $key.' test column alias');
    is($Monitoring::Livestatus::ErrorCode, 0, $key.' test column alias') or
        diag('got error: '.$Monitoring::Livestatus::ErrorMessage);

    #########################
    # send a test command
    # commands still dont work and breaks livestatus
    my $rt = $ml->do('COMMAND ['.time().'] SAVE_STATE_INFORMATION');
    is($rt, '1', $key.' test command');

    #########################
    # check for errors
    #$ml->{'verbose'} = 1;
    $statement = "GET hosts\nLimit: 1";
    $lastquery = $statement;
    $hash_ref  = $ml->selectrow_hashref($statement );
    undef $lastquery;
    isnt($hash_ref, undef, $key.' test error 200 body');
    is($Monitoring::Livestatus::ErrorCode, 0, $key.' test error 200 status') or
        diag('got error: '.$Monitoring::Livestatus::ErrorMessage);

    $statement = "BLAH hosts";
    $lastquery = $statement;
    $hash_ref  = $ml->selectrow_hashref($statement );
    undef $lastquery;
    is($hash_ref, undef, $key.' test error 401 body');
    is($Monitoring::Livestatus::ErrorCode, '401', $key.' test error 401 status') or
        diag('got error: '.$Monitoring::Livestatus::ErrorMessage);

    $statement = "GET hosts\nLimit: ";
    $lastquery = $statement;
    $hash_ref  = $ml->selectrow_hashref($statement );
    undef $lastquery;
    is($hash_ref, undef, $key.' test error 403 body');
    is($Monitoring::Livestatus::ErrorCode, '403', $key.' test error 403 status') or
        diag('got error: '.$Monitoring::Livestatus::ErrorMessage);

    $statement = "GET unknowntable\nLimit: 1";
    $lastquery = $statement;
    $hash_ref  = $ml->selectrow_hashref($statement );
    undef $lastquery;
    is($hash_ref, undef, $key.' test error 404 body');
    is($Monitoring::Livestatus::ErrorCode, '404', $key.' test error 404 status') or
        diag('got error: '.$Monitoring::Livestatus::ErrorMessage);

    $statement = "GET hosts\nColumns: unknown";
    $lastquery = $statement;
    $hash_ref  = $ml->selectrow_hashref($statement );
    undef $lastquery;
    is($hash_ref, undef, $key.' test error 405 body');
    TODO: {
        local $TODO = 'livestatus returns wrong status';
        is($Monitoring::Livestatus::ErrorCode, '405', $key.' test error 405 status') or
            diag('got error: '.$Monitoring::Livestatus::ErrorMessage);
    };

    #########################
    # some more broken statements
    $statement = "GET ";
    $lastquery = $statement;
    $hash_ref  = $ml->selectrow_hashref($statement);
    undef $lastquery;
    is($hash_ref, undef, $key.' test error 403 body');
    is($Monitoring::Livestatus::ErrorCode, '403', $key.' test error 403 status: GET ') or
        diag('got error: '.$Monitoring::Livestatus::ErrorMessage);

    $statement = "GET hosts\nColumns: name, name";
    $lastquery = $statement;
    $hash_ref  = $ml->selectrow_hashref($statement );
    undef $lastquery;
    is($hash_ref, undef, $key.' test error 405 body');
    is($Monitoring::Livestatus::ErrorCode, '405', $key.' test error 405 status: GET hosts\nColumns: name, name') or
        diag('got error: '.$Monitoring::Livestatus::ErrorMessage);

    $statement = "GET hosts\nColumns: ";
    $lastquery = $statement;
    $hash_ref  = $ml->selectrow_hashref($statement );
    undef $lastquery;
    is($hash_ref, undef, $key.' test error 405 body');
    is($Monitoring::Livestatus::ErrorCode, '405', $key.' test error 405 status: GET hosts\nColumns: ') or
        diag('got error: '.$Monitoring::Livestatus::ErrorMessage);

    #########################
    # some forbidden headers
    $statement = "GET hosts\nKeepAlive: on";
    $lastquery = $statement;
    $hash_ref  = $ml->selectrow_hashref($statement );
    undef $lastquery;
    is($hash_ref, undef, $key.' test error 496 body');
    is($Monitoring::Livestatus::ErrorCode, '496', $key.' test error 496 status: KeepAlive: on') or
        diag('got error: '.$Monitoring::Livestatus::ErrorMessage);

    $statement = "GET hosts\nResponseHeader: fixed16";
    $lastquery = $statement;
    $hash_ref  = $ml->selectrow_hashref($statement );
    undef $lastquery;
    is($hash_ref, undef, $key.' test error 495 body');
    is($Monitoring::Livestatus::ErrorCode, '495', $key.' test error 495 status: ResponseHeader: fixed16') or
        diag('got error: '.$Monitoring::Livestatus::ErrorMessage);

    $statement = "GET hosts\nColumnHeaders: on";
    $lastquery = $statement;
    $hash_ref  = $ml->selectrow_hashref($statement );
    undef $lastquery;
    is($hash_ref, undef, $key.' test error 494 body');
    is($Monitoring::Livestatus::ErrorCode, '494', $key.' test error 494 status: ColumnHeader: on') or
        diag('got error: '.$Monitoring::Livestatus::ErrorMessage);

    $statement = "GET hosts\nOuputFormat: json";
    $lastquery = $statement;
    $hash_ref  = $ml->selectrow_hashref($statement );
    undef $lastquery;
    is($hash_ref, undef, $key.' test error 493 body');
    is($Monitoring::Livestatus::ErrorCode, '493', $key.' test error 493 status: OutputForma: json') or
        diag('got error: '.$Monitoring::Livestatus::ErrorMessage);

    $statement = "GET hosts\nSeparators: 0 1 2 3";
    $lastquery = $statement;
    $hash_ref  = $ml->selectrow_hashref($statement );
    undef $lastquery;
    is($hash_ref, undef, $key.' test error 492 body');
    is($Monitoring::Livestatus::ErrorCode, '492', $key.' test error 492 status: Seperators: 0 1 2 3') or
        diag('got error: '.$Monitoring::Livestatus::ErrorMessage);


    #########################
    # check some fancy stats queries
    my $stats_query = "GET services
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
    $lastquery = $stats_query;
    $hash_ref  = $ml->selectrow_hashref($stats_query );
    undef $lastquery;
    isnt($hash_ref, undef, $key.' test fancy stats query') or
        diag('got error: '.Dumper($hash_ref));
}



# generate expected keys
sub get_expected_keys {
    my $type = shift;
    my $skip = shift;
    my @keys = @{$expected_keys->{$type}};

    my @new_keys;
    for my $key (@keys) {
        my $replaced = 0;
        for my $replace_with (keys %{$expected_keys}) {
            if($key eq '__all_from_'.$replace_with.'__') {
                $replaced = 1;
                next if $skip;
                my $prefix = $replace_with.'_';
                if($replace_with eq "hosts")         { $prefix = 'host_';    }
                if($replace_with eq "services")      { $prefix = 'service_'; }
                if($replace_with eq "commands")      { $prefix = 'command_'; }
                if($replace_with eq "contacts")      { $prefix = 'contact_'; }
                if($replace_with eq "servicegroups") { $prefix = 'servicegroup_'; }
                if($replace_with eq "hostgroups")    { $prefix = 'hostgroup_'; }

                if($type eq "log") { $prefix = 'current_'.$prefix; }

                if($type eq "servicesbygroup"     and $replace_with eq 'services')   { $prefix = ''; }
                if($type eq "servicesbyhostgroup" and $replace_with eq 'services')   { $prefix = ''; }
                if($type eq "hostsbygroup"        and $replace_with eq 'hosts')      { $prefix = ''; }

                my $replace_keys = get_expected_keys($replace_with, 1);
                for my $key2 (@{$replace_keys}) {
                    push @new_keys, $prefix.$key2;
                }
            }
        }
        if($replaced == 0) {
            push @new_keys, $key;
        }
    }

    # has been fixed in 1.1.1rc
    #if($type eq 'log') {
    #  my %keys = map { $_ => 1 } @new_keys;
    #  delete $keys{'current_contact_can_submit_commands'};
    #  delete $keys{'current_contact_host_notifications_enabled'};
    #  delete $keys{'current_contact_in_host_notification_period'};
    #  delete $keys{'current_contact_in_service_notification_period'};
    #  delete $keys{'current_contact_service_notifications_enabled'};
    #  @new_keys = keys %keys;
    #}

    my @return = sort @new_keys;
    return(\@return);
}
