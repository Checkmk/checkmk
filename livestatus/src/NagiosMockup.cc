#include <ctime>

extern "C" {
// dummy types -----------------------------------------------------------------

struct circular_buffer {
    int dummy;
};
struct command;
struct contactgroup;
struct contact;
struct hostgroup;
struct host;
struct scheduled_downtime;
struct servicegroup;
struct service;
struct timeperiod;

// official exports ------------------------------------------------------------

int accept_passive_host_checks;
int accept_passive_service_checks;
int check_time_against_period(time_t /*unused*/, timeperiod * /*unused*/) {
    return 0;
}
command *find_command(char * /*unused*/) { return nullptr; }
contact *find_contact(char * /*unused*/) { return nullptr; }
contactgroup *find_contactgroup(char * /*unused*/) { return nullptr; }
host *find_host(char * /*unused*/) { return nullptr; }
hostgroup *find_hostgroup(char * /*unused*/) { return nullptr; }
service *find_service(char * /*unused*/, char * /*unused*/) { return nullptr; }
servicegroup *find_servicegroup(char * /*unused*/) { return nullptr; }
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
time_t last_command_check;
time_t last_log_rotation;
int neb_deregister_callback(int /*unused*/, int (*/*unused*/)(int, void *)) {
    return 0;
}
int neb_register_callback(int /*unused*/, void * /*unused*/, int /*unused*/,
                          int (*/*unused*/)(int, void *)) {
    return 0;
}
int obsess_over_hosts;
int obsess_over_services;
int process_performance_data;
int process_external_command1(char * /*unused*/) { return 0; }
time_t program_start;
int rotate_log_file(time_t /*unused*/) { return 0; }
int schedule_new_event(int /*unused*/, int /*unused*/, time_t /*unused*/,
                       int /*unused*/, unsigned long /*unused*/,
                       void * /*unused*/, int /*unused*/, void * /*unused*/,
                       void * /*unused*/, int /*unused*/) {
    return 0;
}
int submit_external_command(char * /*unused*/, int * /*unused*/) { return 0; }
int write_to_all_logs(char * /*unused*/, unsigned long /*unused*/) { return 0; }

// inofficial exports ----------------------------------------------------------

int check_external_commands;
int check_host_freshness;
int check_service_freshness;
command *command_list;
contactgroup *contactgroup_list;
contact *contact_list;
int enable_environment_macros;
int enable_event_handlers;
int enable_flap_detection;
int enable_notifications;
unsigned long event_broker_options;
int execute_host_checks;
int execute_service_checks;
circular_buffer external_command_buffer;
int external_command_buffer_slots;
hostgroup *hostgroup_list;
host *host_list;
int interval_length;
char *log_archive_path;
char log_file[256];
int log_initial_states;
char *macro_user[256];
int nagios_pid;
scheduled_downtime *scheduled_downtime_list;
servicegroup *servicegroup_list;
service *service_list;
timeperiod *timeperiod_list;

// imports ---------------------------------------------------------------------

int nebmodule_init(int flags, char *args, void *handle);
int nebmodule_deinit(int flags, int reason);
}

int main() {
    nebmodule_init(0, nullptr, nullptr);
    nebmodule_deinit(0, 0);
    return 0;
}
