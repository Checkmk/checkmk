// Copyright (C) 2020 Checkmk GmbH - License: Check_MK Enterprise License
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef NagiosGlobals_h
#define NagiosGlobals_h

#include "nagios.h"

// This header is as collection of the "inofficial Nagios 3 API" we are using,
// centralizing this hack a bit and keeping all the suppressions in one place.
// Nagios 4 declares all the stuff we need in its headers.

#ifndef NAGIOS4
extern "C" {
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern int accept_passive_host_checks;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern int accept_passive_service_checks;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern int check_external_commands;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern int check_host_freshness;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern int check_service_freshness;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern command* command_list;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern contactgroup* contactgroup_list;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern contact* contact_list;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern int enable_environment_macros;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern int enable_event_handlers;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern int enable_flap_detection;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern int enable_notifications;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern unsigned long event_broker_options;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern int execute_host_checks;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern int execute_service_checks;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern circular_buffer external_command_buffer;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern int external_command_buffer_slots;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern hostgroup* hostgroup_list;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern host* host_list;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern int interval_length;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern time_t last_command_check;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern time_t last_log_rotation;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern char* log_archive_path;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern char* log_file;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern int log_initial_states;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern char* macro_user[MAX_USER_MACROS];
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern int nagios_pid;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern int obsess_over_hosts;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern int obsess_over_services;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern int process_performance_data;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern time_t program_start;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern scheduled_downtime* scheduled_downtime_list;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern servicegroup* servicegroup_list;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern service* service_list;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern timeperiod* timeperiod_list;
}
#endif  // NAGIOS4

#endif  // NagiosGlobals_h
