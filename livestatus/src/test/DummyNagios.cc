// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <ctime>

#include "nagios.h"

extern "C" {
// official exports ------------------------------------------------------------
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
int accept_passive_host_checks;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
int accept_passive_service_checks;
int check_time_against_period(time_t /*unused*/, timeperiod * /*unused*/) {
    return 0;
}
command *find_command(nagios_compat_const_char_ptr /*unused*/) {
    return nullptr;
}
contact *find_contact(nagios_compat_const_char_ptr /*unused*/) {
    return nullptr;
}
contactgroup *find_contactgroup(nagios_compat_const_char_ptr /*unused*/) {
    return nullptr;
}
host *find_host(nagios_compat_const_char_ptr /*unused*/) { return nullptr; }
hostgroup *find_hostgroup(nagios_compat_const_char_ptr /*unused*/) {
    return nullptr;
}
service *find_service(nagios_compat_const_char_ptr /*unused*/,
                      nagios_compat_const_char_ptr /*unused*/) {
    return nullptr;
}
servicegroup *find_servicegroup(nagios_compat_const_char_ptr /*unused*/) {
    return nullptr;
}
time_t get_next_log_rotation_time(void) { return 0; }
char *get_program_version(void) { return nullptr; }
int is_contact_for_host(host * /*unused*/, contact * /*unused*/) { return 0; }
int is_contact_for_service(service * /*unused*/, contact * /*unused*/) {
    return 0;
}
int is_contact_member_of_contactgroup(contactgroup * /*unused*/,
                                      contact * /*unused*/) {
    return 0;
}
int is_escalated_contact_for_host(host * /*unused*/, contact * /*unused*/) {
    return 0;
}
int is_escalated_contact_for_service(service * /*unused*/,
                                     contact * /*unused*/) {
    return 0;
}
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
time_t last_command_check;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
time_t last_log_rotation;
int neb_deregister_callback(int /*unused*/, int (*/*unused*/)(int, void *)) {
    return 0;
}
int neb_register_callback(int /*unused*/, void * /*unused*/, int /*unused*/,
                          int (*/*unused*/)(int, void *)) {
    return 0;
}
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
int obsess_over_hosts;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
int obsess_over_services;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
int process_performance_data;
int process_external_command1(char * /*unused*/) { return 0; }
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
time_t program_start;
int rotate_log_file(time_t /*unused*/) { return 0; }
nagios_compat_schedule_new_event_t schedule_new_event(
    int /*unused*/, int /*unused*/, time_t /*unused*/, int /*unused*/,
    unsigned long /*unused*/, void * /*unused*/, int /*unused*/,
    void * /*unused*/, void * /*unused*/, int /*unused*/) {
    return 0;
}
int submit_external_command(char * /*unused*/, int * /*unused*/) { return 0; }
int write_to_all_logs(char * /*unused*/, unsigned long /*unused*/) { return 0; }
// inofficial exports ----------------------------------------------------------
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
int check_external_commands;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
int check_host_freshness;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
int check_service_freshness;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
command *command_list;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
contactgroup *contactgroup_list;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
contact *contact_list;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
int enable_environment_macros;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
int enable_event_handlers;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
int enable_flap_detection;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
int enable_notifications;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
unsigned long event_broker_options;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
int execute_host_checks;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
int execute_service_checks;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
NAGIOS_COMPAT_DEFINE_EXTERNAL_COMMAND_BUFFER;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
int external_command_buffer_slots;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
hostgroup *hostgroup_list;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
host *host_list;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
int interval_length;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
char *log_archive_path;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
char *log_file;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
int log_initial_states;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
char *macro_user[256];
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
int nagios_pid;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
scheduled_downtime *scheduled_downtime_list;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
servicegroup *servicegroup_list;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
service *service_list;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
timeperiod *timeperiod_list;
}
