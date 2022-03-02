// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef nagios_h
#define nagios_h

#include "config.h"  // IWYU pragma: keep

// IWYU pragma: begin_exports
#ifdef CMC
#include "cmc.h"
#else
#define NSCORE
#ifdef NAGIOS4

#include "nagios4/broker.h"
#include "nagios4/common.h"
#include "nagios4/downtime.h"
#include "nagios4/logging.h"
#include "nagios4/macros.h"
#include "nagios4/nagios.h"
#include "nagios4/nebcallbacks.h"
#include "nagios4/neberrors.h"
#include "nagios4/nebmodules.h"
#include "nagios4/nebstructs.h"
#include "nagios4/objects.h"

#define NAGIOS_COMPAT_DEFINE_EXTERNAL_COMMAND_BUFFER

using nagios_compat_contact_struct = struct contact;
using nagios_compat_const_char_ptr = const char *;
using nagios_compat_schedule_new_event_t = timed_event *;

inline time_t nagios_compat_last_command_check() {
    // TODO: check if this data is available in nagios_squeue
    return 0;
}

inline int nagios_compat_external_command_buffer_slots() { return 0; }

inline int nagios_compat_external_command_buffer_items() { return 0; }

inline int nagios_compat_external_command_buffer_high() { return 0; }

inline int nagios_compat_accept_passive_host_checks(const host &h) {
    return h.accept_passive_checks;
}

inline int nagios_compat_accept_passive_service_checks(const service &s) {
    return s.accept_passive_checks;
}

inline int nagios_compat_obsess_over_host(const host &h) { return h.obsess; }

inline int nagios_compat_obsess_over_service(const service &s) {
    return s.obsess;
}

inline time_t nagios_compat_last_host_notification(const host &h) {
    return h.last_notification;
}

inline time_t nagios_compat_next_host_notification(const host &h) {
    return h.next_notification;
}

inline char *&nagios_compat_host_check_command(host &h) {
    return h.check_command;
}

inline char *const &nagios_compat_host_check_command(const host &h) {
    return h.check_command;
}

inline char *&nagios_compat_service_check_command(service &s) {
    return s.check_command;
}

inline char *const &nagios_compat_service_check_command(const service &s) {
    return s.check_command;
}

inline int nagios_compat_submit_external_command(const char *cmd) {
    return process_external_command1(const_cast<char *>(cmd));
}

#else

#include "nagios/broker.h"
#include "nagios/common.h"
#include "nagios/downtime.h"
#include "nagios/macros.h"
#include "nagios/nagios.h"
#include "nagios/nebcallbacks.h"
#include "nagios/neberrors.h"
#include "nagios/nebmodules.h"
#include "nagios/nebstructs.h"
#include "nagios/objects.h"

// a collection of the "inofficial Nagios 3 API" we are using
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
extern command *command_list;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern contactgroup *contactgroup_list;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern contact *contact_list;
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
extern hostgroup *hostgroup_list;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern host *host_list;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern int interval_length;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern time_t last_command_check;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern time_t last_log_rotation;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern char *log_archive_path;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern char *log_file;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern int log_initial_states;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern char *macro_user[MAX_USER_MACROS];
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
extern scheduled_downtime *scheduled_downtime_list;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern servicegroup *servicegroup_list;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern service *service_list;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern timeperiod *timeperiod_list;
}

#define NAGIOS_COMPAT_DEFINE_EXTERNAL_COMMAND_BUFFER \
    circular_buffer external_command_buffer

using nagios_compat_contact_struct = struct contact_struct;
using nagios_compat_const_char_ptr = char *;
using nagios_compat_schedule_new_event_t = int;

inline time_t nagios_compat_last_command_check() { return last_command_check; }

inline int nagios_compat_external_command_buffer_slots() {
    return external_command_buffer_slots;
}

inline int nagios_compat_external_command_buffer_items() {
    return external_command_buffer.items;
}

inline int nagios_compat_external_command_buffer_high() {
    return external_command_buffer.high;
}

inline int nagios_compat_accept_passive_host_checks(const host &h) {
    return h.accept_passive_host_checks;
}

inline int nagios_compat_accept_passive_service_checks(const service &s) {
    return s.accept_passive_service_checks;
}

inline int nagios_compat_obsess_over_host(const host &h) {
    return h.obsess_over_host;
}

inline int nagios_compat_obsess_over_service(const service &s) {
    return s.obsess_over_service;
}

inline time_t nagios_compat_last_host_notification(const host &h) {
    return h.last_host_notification;
}

inline time_t nagios_compat_next_host_notification(const host &h) {
    return h.next_host_notification;
}

inline char *&nagios_compat_host_check_command(host &h) {
    return h.host_check_command;
}

inline char *const &nagios_compat_host_check_command(const host &h) {
    return h.host_check_command;
}

inline char *&nagios_compat_service_check_command(service &s) {
    return s.service_check_command;
}

inline char *const &nagios_compat_service_check_command(const service &s) {
    return s.service_check_command;
}

inline int nagios_compat_submit_external_command(const char *cmd) {
    return submit_external_command(const_cast<char *>(cmd), nullptr);
}

#endif  // NAGIOS4
#endif  // CMC
// IWYU pragma: end_exports
#endif  // nagios_h
