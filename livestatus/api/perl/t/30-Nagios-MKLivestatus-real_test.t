#!/usr/bin/env perl

#########################

use strict;
use Test::More;
use Data::Dumper;

if ( ! defined $ENV{TEST_SOCKET} and !defined $ENV{TEST_SERVER} ) {
    my $msg = 'Author test.  Set $ENV{TEST_SOCKET} and $ENV{TEST_SERVER} to run';
    plan( skip_all => $msg );
} else {
    plan(tests => 223);
}

use_ok('Nagios::MKLivestatus');

#########################
my $line_seperator      = 10;
my $column_seperator    = 0;
my $objects_to_test = {
  # UNIX
  # create unix object with a single arg
  'unix_single_arg' => Nagios::MKLivestatus::UNIX->new( $ENV{TEST_SOCKET} ),

  # create unix object with hash args
  'unix_few_args' => Nagios::MKLivestatus->new(
                                      verbose             => 0,
                                      socket              => $ENV{TEST_SOCKET},
                                      line_seperator      => $line_seperator,
                                      column_seperator    => $column_seperator,
                                    ),

  # create unix object with hash args
  'unix_keepalive' => Nagios::MKLivestatus->new(
                                      verbose             => 0,
                                      socket              => $ENV{TEST_SOCKET},
                                      keepalive           => 1,
                                    ),

  # TCP
  # create inet object with a single arg
  'inet_single_arg' => Nagios::MKLivestatus::INET->new( $ENV{TEST_SERVER} ),

  # create inet object with hash args
  'inet_few_args' => Nagios::MKLivestatus->new(
                                      verbose             => 0,
                                      server              => $ENV{TEST_SERVER},
                                      line_seperator      => $line_seperator,
                                      column_seperator    => $column_seperator,
                                    ),


  # create inet object with keepalive
  'inet_keepalive' => Nagios::MKLivestatus->new(
                                      verbose             => 0,
                                      server              => $ENV{TEST_SERVER},
                                      keepalive           => 1,
                                    ),
};

my $excpected_keys = {
          'hosts'         => ['accept_passive_checks','acknowledged','acknowledgement_type','action_url','active_checks_enabled','address','alias','check_command','check_freshness','check_interval','check_options','check_period','check_type','checks_enabled','childs','contacts','current_attempt','current_notification_number','custom_variable_names','custom_variable_values','display_name','downtimes','event_handler_enabled','execution_time','first_notification_delay','flap_detection_enabled','groups','hard_state','has_been_checked','high_flap_threshold','icon_image','icon_image_alt','in_check_period','in_notification_period','initial_state','is_executing','is_flapping','last_check','last_hard_state','last_hard_state_change','last_notification','last_state','last_state_change','latency','long_plugin_output','low_flap_threshold','max_check_attempts','name','next_check','next_notification','notes','notes_url','notification_interval','notification_period','notifications_enabled','num_services','num_services_crit','num_services_hard_crit','num_services_hard_ok','num_services_hard_unknown','num_services_hard_warn','num_services_ok','num_services_unknown','num_services_warn','parents','pending_flex_downtime','percent_state_change','perf_data','plugin_output','process_performance_data','retry_interval','scheduled_downtime_depth','state','state_type','statusmap_image','total_services','worst_service_hard_state','worst_service_state','x_3d','y_3d','z_3d'],
          'services'      => ['accept_passive_checks','acknowledged','acknowledgement_type','action_url','active_checks_enabled','check_command','check_interval','check_options','check_period','check_type','checks_enabled','contacts','current_attempt','current_notification_number','custom_variable_names','custom_variable_values','description','display_name','downtimes','event_handler','event_handler_enabled','execution_time','first_notification_delay','groups','has_been_checked','high_flap_threshold','host_accept_passive_checks','host_acknowledged','host_acknowledgement_type','host_action_url','host_active_checks_enabled','host_address','host_alias','host_check_command','host_check_freshness','host_check_interval','host_check_options','host_check_period','host_check_type','host_checks_enabled','host_childs','host_contacts','host_current_attempt','host_current_notification_number','host_custom_variable_names','host_custom_variable_values','host_display_name','host_downtimes','host_event_handler_enabled','host_execution_time','host_first_notification_delay','host_flap_detection_enabled','host_groups','host_hard_state','host_has_been_checked','host_high_flap_threshold','host_icon_image','host_icon_image_alt','host_in_check_period','host_in_notification_period','host_initial_state','host_is_executing','host_is_flapping','host_last_check','host_last_hard_state','host_last_hard_state_change','host_last_notification','host_last_state','host_last_state_change','host_latency','host_long_plugin_output','host_low_flap_threshold','host_max_check_attempts','host_name','host_next_check','host_next_notification','host_notes','host_notes_url','host_notification_interval','host_notification_period','host_notifications_enabled','host_num_services','host_num_services_crit','host_num_services_hard_crit','host_num_services_hard_ok','host_num_services_hard_unknown','host_num_services_hard_warn','host_num_services_ok','host_num_services_unknown','host_num_services_warn','host_parents','host_pending_flex_downtime','host_percent_state_change','host_perf_data','host_plugin_output','host_process_performance_data','host_retry_interval','host_scheduled_downtime_depth','host_state','host_state_type','host_statusmap_image','host_total_services','host_worst_service_hard_state','host_worst_service_state','host_x_3d','host_y_3d','host_z_3d','icon_image','icon_image_alt','in_check_period','in_notification_period','initial_state','is_executing','is_flapping','last_check','last_hard_state','last_hard_state_change','last_notification','last_state','last_state_change','latency','long_plugin_output','low_flap_threshold','max_check_attempts','next_check','next_notification','notes','notes_url','notification_interval','notification_period','notifications_enabled','percent_state_change','perf_data','plugin_output','process_performance_data','retry_interval','scheduled_downtime_depth','state','state_type'],
          'contacts'      => ['address1','address2','address3','address4','address5','address6','alias','can_submit_commands','custom_variable_names','custom_variable_values','email','host_notification_period','host_notifications_enabled','in_host_notification_period','in_service_notification_period','name','pager','service_notification_period','service_notifications_enabled'],
          'status'        => ['connections','connections_rate','host_checks','host_checks_rate','neb_callbacks','neb_callbacks_rate','requests','requests_rate','service_checks','service_checks_rate'],
          'hostgroups'    => ['action_url','alias','members','name','notes','notes_url','num_hosts','num_hosts_down','num_hosts_unreach','num_hosts_up','num_services','num_services_crit','num_services_hard_crit','num_services_hard_ok','num_services_hard_unknown','num_services_hard_warn','num_services_ok','num_services_unknown','num_services_warn','worst_host_state','worst_service_hard_state','worst_service_state'],
          'servicegroups' => ['action_url','alias','members','name','notes','notes_url','num_services','num_services_crit','num_services_hard_crit','num_services_hard_ok','num_services_hard_unknown','num_services_hard_warn','num_services_ok','num_services_unknown','num_services_warn','worst_service_state'],
          'downtimes'     => ['author','comment','duration','end_time','entry_time','fixed','host_accept_passive_checks','host_acknowledged','host_acknowledgement_type','host_action_url','host_active_checks_enabled','host_address','host_alias','host_check_command','host_check_freshness','host_check_interval','host_check_options','host_check_period','host_check_type','host_checks_enabled','host_childs','host_contacts','host_current_attempt','host_current_notification_number','host_custom_variable_names','host_custom_variable_values','host_display_name','host_downtimes','host_event_handler_enabled','host_execution_time','host_first_notification_delay','host_flap_detection_enabled','host_groups','host_hard_state','host_has_been_checked','host_high_flap_threshold','host_icon_image','host_icon_image_alt','host_in_check_period','host_in_notification_period','host_initial_state','host_is_executing','host_is_flapping','host_last_check','host_last_hard_state','host_last_hard_state_change','host_last_notification','host_last_state','host_last_state_change','host_latency','host_long_plugin_output','host_low_flap_threshold','host_max_check_attempts','host_name','host_next_check','host_next_notification','host_notes','host_notes_url','host_notification_interval','host_notification_period','host_notifications_enabled','host_num_services','host_num_services_crit','host_num_services_hard_crit','host_num_services_hard_ok','host_num_services_hard_unknown','host_num_services_hard_warn','host_num_services_ok','host_num_services_unknown','host_num_services_warn','host_parents','host_pending_flex_downtime','host_percent_state_change','host_perf_data','host_plugin_output','host_process_performance_data','host_retry_interval','host_scheduled_downtime_depth','host_state','host_state_type','host_statusmap_image','host_total_services','host_worst_service_hard_state','host_worst_service_state','host_x_3d','host_y_3d','host_z_3d','id','service_accept_passive_checks','service_acknowledged','service_acknowledgement_type','service_action_url','service_active_checks_enabled','service_check_command','service_check_interval','service_check_options','service_check_period','service_check_type','service_checks_enabled','service_contacts','service_current_attempt','service_current_notification_number','service_custom_variable_names','service_custom_variable_values','service_description','service_display_name','service_downtimes','service_event_handler','service_event_handler_enabled','service_execution_time','service_first_notification_delay','service_groups','service_has_been_checked','service_high_flap_threshold','service_icon_image','service_icon_image_alt','service_in_check_period','service_in_notification_period','service_initial_state','service_is_executing','service_is_flapping','service_last_check','service_last_hard_state','service_last_hard_state_change','service_last_notification','service_last_state','service_last_state_change','service_latency','service_long_plugin_output','service_low_flap_threshold','service_max_check_attempts','service_next_check','service_next_notification','service_notes','service_notes_url','service_notification_interval','service_notification_period','service_notifications_enabled','service_percent_state_change','service_perf_data','service_plugin_output','service_process_performance_data','service_retry_interval','service_scheduled_downtime_depth','service_state','service_state_type','start_time','triggered_by','type'],
          'columns'       => ['description','name','table','type'],
};

for my $key (keys %{$objects_to_test}) {
    my $nl = $objects_to_test->{$key};
    isa_ok($nl, 'Nagios::MKLivestatus') or BAIL_OUT("no need to continue without a proper Nagios::MKLivestatus object: ".$key);

    # dont die on errors
    $nl->errors_are_fatal(0);

    #########################
    # set downtime for a host and service
    #$nl->verbose(1);
    my $firsthost = $nl->select_scalar_value("GET hosts\nColumns: name\nLimit: 1");
    isnt($firsthost, undef, 'get test hostname') or BAIL_OUT('got not test hostname');
    #$nl->do('COMMAND ['.time().'] SCHEDULE_HOST_DOWNTIME;'.$firsthost.';'.time().';'.(time()+30).';0;0;30;'.$0.';Some Downtime Comment');
    my $firstservice = $nl->select_scalar_value("GET services\nColumns: description\nFilter: host_name = $firsthost\nLimit: 1");
    isnt($firstservice, undef, 'get test servicename') or BAIL_OUT('got not test servicename');
    #$nl->do('COMMAND ['.time().'] SCHEDULE_SERVICE_DOWNTIME;'.$firsthost.';'.$firstservice.';'.time().';'.(time()+30).';0;0;30;'.$0.';Some Downtime Comment');
    #$nl->verbose(0);

    #########################
    # check keys
    for my $type (keys %{$excpected_keys}) {
        my $expected_keys = $excpected_keys->{$type};
        my $statement = "GET $type\nLimit: 1";
        my $hash_ref  = $nl->selectrow_hashref($statement );
        my @keys      = sort keys %{$hash_ref};
        #$Data::Dumper::Indent = 0;
        is_deeply(\@keys, $expected_keys, $key.' '.$type.'keys');# or ( diag(Dumper(\@keys)) or die("***************\n".$type."\n***************\n") );
    }

    #########################
    # send a test command
    # commands still dont work and breaks livestatus
    #my $rt = $nl->do('COMMAND ['.time().'] SAVE_STATE_INFORMATION');
    #is($rt, '1', $key.' test command');

    #########################
    # check for errors
    #$nl->{'verbose'} = 1;
    my $statement = "GET hosts\nLimit: 1";
    my $hash_ref  = $nl->selectrow_hashref($statement );
    isnt($hash_ref, undef, $key.' test error 200 body');
    is($Nagios::MKLivestatus::ErrorCode, 0, $key.' test error 200 status') or
        diag('got error: '.$Nagios::MKLivestatus::ErrorMessage);

    $statement = "BLAH hosts";
    $hash_ref  = $nl->selectrow_hashref($statement );
    is($hash_ref, undef, $key.' test error 401 body');
    is($Nagios::MKLivestatus::ErrorCode, '401', $key.' test error 401 status') or
        diag('got error: '.$Nagios::MKLivestatus::ErrorMessage);

    $statement = "GET hosts\nLimit: ";
    $hash_ref  = $nl->selectrow_hashref($statement );
    is($hash_ref, undef, $key.' test error 403 body');
    is($Nagios::MKLivestatus::ErrorCode, '403', $key.' test error 403 status') or
        diag('got error: '.$Nagios::MKLivestatus::ErrorMessage);

    $statement = "GET unknowntable\nLimit: 1";
    $hash_ref  = $nl->selectrow_hashref($statement );
    is($hash_ref, undef, $key.' test error 404 body');
    is($Nagios::MKLivestatus::ErrorCode, '404', $key.' test error 404 status') or
        diag('got error: '.$Nagios::MKLivestatus::ErrorMessage);

    $statement = "GET hosts\nColumns: unknown";
    $hash_ref  = $nl->selectrow_hashref($statement );
    TODO: {
        local $TODO = 'livestatus returns wrong status';
        is($hash_ref, undef, $key.' test error 405 body');
        is($Nagios::MKLivestatus::ErrorCode, '405', $key.' test error 405 status') or
            diag('got error: '.$Nagios::MKLivestatus::ErrorMessage);
    };

    #########################
    # some more broken statements
    $statement = "GET ";
    $hash_ref  = $nl->selectrow_hashref($statement);
    is($hash_ref, undef, $key.' test error 403 body');
    is($Nagios::MKLivestatus::ErrorCode, '403', $key.' test error 403 status: GET ') or
        diag('got error: '.$Nagios::MKLivestatus::ErrorMessage);

    $statement = "GET hosts\nColumns: name, name";
    $hash_ref  = $nl->selectrow_hashref($statement );
    is($hash_ref, undef, $key.' test error 405 body');
    is($Nagios::MKLivestatus::ErrorCode, '405', $key.' test error 405 status: GET hosts\nColumns: name, name') or
        diag('got error: '.$Nagios::MKLivestatus::ErrorMessage);

    $statement = "GET hosts\nColumns: ";
    $hash_ref  = $nl->selectrow_hashref($statement );
    is($hash_ref, undef, $key.' test error 405 body');
    is($Nagios::MKLivestatus::ErrorCode, '405', $key.' test error 405 status: GET hosts\nColumns: ') or
        diag('got error: '.$Nagios::MKLivestatus::ErrorMessage);

    #########################
    # some forbidden headers
    $statement = "GET hosts\nKeepAlive: on";
    $hash_ref  = $nl->selectrow_hashref($statement );
    is($hash_ref, undef, $key.' test error 496 body');
    is($Nagios::MKLivestatus::ErrorCode, '496', $key.' test error 496 status: KeepAlive: on') or
        diag('got error: '.$Nagios::MKLivestatus::ErrorMessage);

    $statement = "GET hosts\nResponseHeader: fixed16";
    $hash_ref  = $nl->selectrow_hashref($statement );
    is($hash_ref, undef, $key.' test error 495 body');
    is($Nagios::MKLivestatus::ErrorCode, '495', $key.' test error 495 status: ResponseHeader: fixed16') or
        diag('got error: '.$Nagios::MKLivestatus::ErrorMessage);

    $statement = "GET hosts\nColumnHeaders: on";
    $hash_ref  = $nl->selectrow_hashref($statement );
    is($hash_ref, undef, $key.' test error 494 body');
    is($Nagios::MKLivestatus::ErrorCode, '494', $key.' test error 494 status: ColumnHeader: on') or
        diag('got error: '.$Nagios::MKLivestatus::ErrorMessage);

    $statement = "GET hosts\nOuputFormat: json";
    $hash_ref  = $nl->selectrow_hashref($statement );
    is($hash_ref, undef, $key.' test error 493 body');
    is($Nagios::MKLivestatus::ErrorCode, '493', $key.' test error 493 status: OutputForma: json') or
        diag('got error: '.$Nagios::MKLivestatus::ErrorMessage);

    $statement = "GET hosts\nSeparators: 0 1 2 3";
    $hash_ref  = $nl->selectrow_hashref($statement );
    is($hash_ref, undef, $key.' test error 492 body');
    is($Nagios::MKLivestatus::ErrorCode, '492', $key.' test error 492 status: Seperators: 0 1 2 3') or
        diag('got error: '.$Nagios::MKLivestatus::ErrorMessage);
}
