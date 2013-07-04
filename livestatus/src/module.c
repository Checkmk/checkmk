// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include <sys/select.h>
#include <time.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <sys/socket.h>
#include <unistd.h>
#include <sys/select.h>
#include <pthread.h>
#include <stdarg.h>
#include <errno.h>
#include <signal.h>
#include <fcntl.h>

#include "nagios.h"
#include "livestatus.h"
#include "downtime.h"
#include "store.h"
#include "logger.h"
#include "config.h"
#include "global_counters.h"
#include "strutil.h"
#include "auth.h"
#include "data_encoding.h"
#include "waittriggers.h"
#include "livechecking.h"


#ifndef AF_LOCAL
#define   AF_LOCAL AF_UNIX
#endif
#ifndef PF_LOCAL
#define   PF_LOCAL PF_UNIX
#endif

// usually - but not always - in sys/un.h
#ifndef SUN_LEN
# define SUN_LEN(ptr) ((size_t) (((struct sockaddr_un *) 0)->sun_path) + strlen ((ptr)->sun_path))
#endif

void TRIGGER(int what)
{
    pthread_cond_broadcast(&g_wait_cond[WT_ALL]);
    pthread_cond_broadcast(&g_wait_cond[what]);
}


NEB_API_VERSION(CURRENT_NEB_API_VERSION)
extern int event_broker_options;
extern int enable_environment_macros;
extern char *log_file;

int g_idle_timeout_msec = 300 * 1000; /* maximum idle time for connection in keep alive state */
int g_query_timeout_msec = 10 * 1000;      /* maximum time for reading a query */

int g_num_clientthreads = 10;     /* allow 10 concurrent connections per default */
int g_num_queued_connections = 0;     /* current number of queued connections (for statistics) */
int g_num_active_connections = 0;     /* current number of active connections (for statistics) */
size_t g_thread_stack_size = 65536; /* stack size of threads */
extern int g_disable_statehist_filtering;

#define false 0
#define true 1


void *g_nagios_handle;
int g_unix_socket = -1;
int g_max_fd_ever = 0;
char g_socket_path[4096];
char g_pnp_path[4096];
char g_livecheck_path[4096];
char g_logfile_path[4096];
int g_debug_level = 0;
int g_should_terminate = false;
pthread_t g_mainthread_id;
pthread_t *g_clientthread_id;
unsigned long g_max_cached_messages = 500000;
unsigned long g_max_response_size = 100 * 1024 * 1024; // limit answer to 10 MB
int g_thread_running = 0;
int g_thread_pid = 0;
int g_service_authorization = AUTH_LOOSE;
int g_group_authorization = AUTH_STRICT;
int g_data_encoding = ENCODING_UTF8;

/* simple statistics data for TableStatus */
extern struct host *host_list;
extern struct service *service_list;
extern scheduled_downtime *scheduled_downtime_list;
extern int log_initial_states;


int g_num_hosts;
int g_num_services;


void count_hosts()
{
    g_num_hosts = 0;
    host *h = (host *)host_list;
    while (h) {
        g_num_hosts ++;
        h = h->next;
    }
}

void count_services()
{
    g_num_services = 0;
    service *s = (service *)service_list;
    while (s) {
        g_num_services ++;
        s = s->next;
    }
}



void* voidp;

void livestatus_count_fork()
{
    g_counters[COUNTER_FORKS]++;
}


void livestatus_cleanup_after_fork()
{
    // 4.2.2010: Deactivate the cleanup function. It might cause
    // more trouble than it tries to avoid. It might lead to a deadlock
    // with Nagios' fork()-mechanism...
    // store_deinit();
    struct stat st;

    int i;
    // We need to close our server and client sockets. Otherwise
    // our connections are inherited to host and service checks.
    // If we close our client connection in such a situation,
    // the connection will still be open since and the client will
    // hang while trying to read further data. And the CLOEXEC is
    // not atomic :-(

    // Eventuell sollte man hier anstelle von store_deinit() nicht
    // darauf verlassen, dass die ClientQueue alle Verbindungen zumacht.
    // Es sind ja auch Dateideskriptoren offen, die von Threads gehalten
    // werden und nicht mehr in der Queue sind. Und in store_deinit()
    // wird mit mutexes rumgemacht....
    for (i=3; i < g_max_fd_ever; i++) {
        if (0 == fstat(i, &st) && S_ISSOCK(st.st_mode))
        {
            close(i);
        }
    }
}


void *main_thread(void *data __attribute__ ((__unused__)))
{
    g_thread_pid = getpid();
    while (!g_should_terminate)
    {
        do_statistics();
        if (g_thread_pid != getpid()) {
            logger(LG_INFO, "I'm not the main process but %d!", getpid());
            // return;
        }
        struct timeval tv;
        tv.tv_sec  = 2;
        tv.tv_usec = 500 * 1000;

        fd_set fds;
        FD_ZERO(&fds);
        FD_SET(g_unix_socket, &fds);
        int retval = select(g_unix_socket + 1, &fds, NULL, NULL, &tv);
        if (retval > 0 && FD_ISSET(g_unix_socket, &fds)) {
            int cc = accept(g_unix_socket, NULL, NULL);
            if (cc > g_max_fd_ever)
                g_max_fd_ever = cc;
            if (0 < fcntl(cc, F_SETFD, FD_CLOEXEC))
                logger(LG_INFO, "Cannot set FD_CLOEXEC on client socket: %s", strerror(errno));
            queue_add_connection(cc); // closes fd
            g_num_queued_connections++;
            g_counters[COUNTER_CONNECTIONS]++;
        }
    }
    logger(LG_INFO, "Socket thread has terminated");
    return voidp;
}

void *client_thread(void *data __attribute__ ((__unused__)))
{
    void *input_buffer = create_inputbuffer(&g_should_terminate);
    void *output_buffer = create_outputbuffer();

    while (!g_should_terminate) {
        int cc = queue_pop_connection();
        g_num_queued_connections--;
        g_num_active_connections++;
        if (cc >= 0) {
            if (g_debug_level >= 2)
                logger(LG_INFO, "Accepted client connection on fd %d", cc);
            set_inputbuffer_fd(input_buffer, cc);
            int keepalive = 1;
            unsigned requestnr = 1;
            while (keepalive) {
                if (g_debug_level >= 2 && requestnr > 1)
                    logger(LG_INFO, "Handling request %d on same connection", requestnr);
                keepalive = store_answer_request(input_buffer, output_buffer);
                flush_output_buffer(output_buffer, cc, &g_should_terminate);
                g_counters[COUNTER_REQUESTS]++;
                requestnr ++;
            }
            close(cc);
        }
        g_num_active_connections--;
    }
    delete_outputbuffer(output_buffer);
    delete_inputbuffer(input_buffer);
    return voidp;
}

void start_threads()
{
    count_hosts();
    count_services();

    if (!g_thread_running) {
        /* start thread that listens on socket */
        pthread_atfork(livestatus_count_fork, NULL, livestatus_cleanup_after_fork);
        pthread_create(&g_mainthread_id, 0, main_thread, (void *)0);
        if (g_debug_level > 0)
            logger(LG_INFO, "Starting %d client threads", g_num_clientthreads);

        unsigned t;
        g_clientthread_id = (pthread_t *)malloc(sizeof(pthread_t) * g_num_clientthreads);
        pthread_attr_t attr;
        pthread_attr_init(&attr);
        size_t defsize;
        if (g_debug_level >= 2 && 0 == pthread_attr_getstacksize(&attr, &defsize))
            logger(LG_INFO, "Default stack size is %lu", defsize);
        if (0 != pthread_attr_setstacksize(&attr, g_thread_stack_size))
            logger(LG_INFO, "Error: Cannot set thread stack size to %lu", g_thread_stack_size);
        else {
            if (g_debug_level >= 2)
                logger(LG_INFO, "Setting thread stack size to %lu", g_thread_stack_size);
        }
        for (t=0; t < g_num_clientthreads; t++)
            pthread_create(&g_clientthread_id[t], &attr, client_thread, (void *)0);

        g_thread_running = 1;
        pthread_attr_destroy(&attr);
    }
}

void terminate_threads()
{
    if (g_thread_running) {
        g_should_terminate = true;
        logger(LG_INFO, "Waiting for main to terminate...");
        pthread_join(g_mainthread_id, NULL);
        logger(LG_INFO, "Waiting for client threads to terminate...");
        queue_wakeup_all();
        unsigned t;
        for (t=0; t < g_num_clientthreads; t++) {
            if (0 != pthread_join(g_clientthread_id[t], NULL))
                logger(LG_INFO, "Warning: could not join thread %p", g_clientthread_id[t]);
        }
        if (g_debug_level > 0)
            logger(LG_INFO, "Main thread + %u client threads have finished", g_num_clientthreads);
        g_thread_running = 0;
        g_should_terminate = false;
    }
    free(g_clientthread_id);
}

int open_unix_socket()
{
    struct stat st;
    if (0 == stat(g_socket_path, &st)) {
        if (0 == unlink(g_socket_path)) {
            logger(LG_DEBUG , "Removed old left over socket file %s", g_socket_path);
        }
        else {
            logger(LG_ALERT, "Cannot remove in the way file %s: %s",
                    g_socket_path, strerror(errno));
            return false;
        }
    }

    g_unix_socket = socket(PF_LOCAL, SOCK_STREAM, 0);
    g_max_fd_ever = g_unix_socket;
    if (g_unix_socket < 0)
    {
        logger(LG_CRIT , "Unable to create UNIX socket: %s", strerror(errno));
        return false;
    }

    // Imortant: close on exec -> check plugins must not inherit it!
    if (0 < fcntl(g_unix_socket, F_SETFD, FD_CLOEXEC))
        logger(LG_INFO, "Cannot set FD_CLOEXEC on socket: %s", strerror(errno));

    // Bind it to its address. This creates the file with the name g_socket_path
    struct sockaddr_un sockaddr;
    sockaddr.sun_family = AF_LOCAL;
    strncpy(sockaddr.sun_path, g_socket_path, sizeof(sockaddr.sun_path));
    if (bind(g_unix_socket, (struct sockaddr *) &sockaddr, SUN_LEN(&sockaddr)) < 0)
    {
        logger(LG_ERR , "Unable to bind adress %s to UNIX socket: %s",
                g_socket_path, strerror(errno));
        close(g_unix_socket);
        return false;
    }

    // Make writable group members (fchmod didn't do nothing for me. Don't know why!)
    if (0 != chmod(g_socket_path, 0660)) {
        logger(LG_ERR , "Cannot chown unix socket at %s to 0660: %s", g_socket_path, strerror(errno));
        close(g_unix_socket);
        return false;
    }

    if (0 != listen(g_unix_socket, 3 /* backlog */)) {
        logger(LG_ERR , "Cannot listen to unix socket at %s: %s", g_socket_path, strerror(errno));
        close(g_unix_socket);
        return false;
    }

    if (g_debug_level > 0)
        logger(LG_INFO, "Opened UNIX socket %s\n", g_socket_path);
    return true;

}

void close_unix_socket()
{
    unlink(g_socket_path);
    if (g_unix_socket >= 0) {
        close(g_unix_socket);
        g_unix_socket = -1;
    }
}

int broker_host(int event_type __attribute__ ((__unused__)), void *data __attribute__ ((__unused__)))
{
    g_counters[COUNTER_NEB_CALLBACKS]++;
    return 0;
}


int broker_check(int event_type, void *data)
{
    int result = NEB_OK;
    if (event_type == NEBCALLBACK_SERVICE_CHECK_DATA) {
        if (g_livecheck_enabled)
            result = broker_service_livecheck(event_type, data);

        nebstruct_service_check_data *c = (nebstruct_service_check_data *)data;
        if (c->type == NEBTYPE_SERVICECHECK_PROCESSED) {
            g_counters[COUNTER_SERVICE_CHECKS]++;
        }
    }
    else if (event_type == NEBCALLBACK_HOST_CHECK_DATA) {
        if (g_livecheck_enabled)
            result = broker_host_livecheck(event_type, data);

        nebstruct_host_check_data *c = (nebstruct_host_check_data *)data;
        if (c->type == NEBTYPE_HOSTCHECK_PROCESSED) {
            g_counters[COUNTER_HOST_CHECKS]++;
        }
    }
    TRIGGER(WT_CHECK);
    return result;
}


int broker_comment(int event_type __attribute__ ((__unused__)), void *data)
{
    nebstruct_comment_data *co = (nebstruct_comment_data *)data;
    store_register_comment(co);
    g_counters[COUNTER_NEB_CALLBACKS]++;
    TRIGGER(WT_COMMENT);
    return 0;
}

int broker_downtime(int event_type __attribute__ ((__unused__)), void *data)
{
    nebstruct_downtime_data *dt = (nebstruct_downtime_data *)data;
    store_register_downtime(dt);
    g_counters[COUNTER_NEB_CALLBACKS]++;
    TRIGGER(WT_DOWNTIME);
    return 0;
}

int broker_log(int event_type __attribute__ ((__unused__)), void *data __attribute__ ((__unused__)))
{

    g_counters[COUNTER_NEB_CALLBACKS]++;
    g_counters[COUNTER_LOG_MESSAGES]++;
    TRIGGER(WT_LOG);
    return 0;
}

int broker_command(int event_type __attribute__ ((__unused__)), void *data)
{
    nebstruct_external_command_data *sc = (nebstruct_external_command_data *)data;
    if (sc->type == NEBTYPE_EXTERNALCOMMAND_START)
        g_counters[COUNTER_COMMANDS]++;
    g_counters[COUNTER_NEB_CALLBACKS]++;
    TRIGGER(WT_COMMAND);
    return 0;
}

int broker_state(int event_type __attribute__ ((__unused__)), void *data __attribute__ ((__unused__)))
{
    g_counters[COUNTER_NEB_CALLBACKS]++;
    TRIGGER(WT_STATE);
    return 0;
}

int broker_program(int event_type __attribute__ ((__unused__)), void *data __attribute__ ((__unused__)))
{
    g_counters[COUNTER_NEB_CALLBACKS]++;
    TRIGGER(WT_PROGRAM);
    return 0;
}

char* get_downtime_comment(char* host_name, char* svc_desc)
{
    char* comment;
    int matches = 0;
    scheduled_downtime* dt_list = scheduled_downtime_list;
    while (dt_list != NULL) {
        if (dt_list->type == HOST_DOWNTIME) {
            if (strcmp(dt_list->host_name, host_name) == 0) {
                matches++;
                comment = dt_list->comment;
            }
        }
        if (svc_desc != NULL && dt_list->type == SERVICE_DOWNTIME) {
            if( strcmp(dt_list->host_name, host_name) == 0
                    && strcmp(dt_list->service_description, svc_desc) == 0) {
                matches++;
                comment = dt_list->comment;
            }
        }
        dt_list = dt_list->next;
    }
    return matches == 0 ? "No comment" : matches > 1 ? "Multiple Downtime Comments" : comment;
}

void livestatus_log_initial_states()
{
    // Log DOWNTIME hosts
    host *h = (host *)host_list;
    char buffer[8192];

    while (h) {
        if (h->scheduled_downtime_depth > 0) {
            snprintf(buffer, sizeof(buffer), "HOST DOWNTIME ALERT: %s;STARTED;%s", h->name, get_downtime_comment(h->name, NULL));
            write_to_all_logs(buffer, LG_INFO);
        }
        h = h->next;
    }
    // Log DOWNTIME services
    service *s = (service *)service_list;
    while (s) {
        if (s->scheduled_downtime_depth > 0) {
            snprintf(buffer, sizeof(buffer), "SERVICE DOWNTIME ALERT: %s;%s;STARTED;%s", s->host_name, s->description,
                    get_downtime_comment(s->host_name, s->description));
            write_to_all_logs(buffer, LG_INFO);
        }
        s = s->next;
    }
    // Log TIMERPERIODS
    log_timeperiods_cache();
}


int broker_event(int event_type __attribute__ ((__unused__)), void *data)
{
    g_counters[COUNTER_NEB_CALLBACKS]++;
    struct nebstruct_timed_event_struct *ts = (struct nebstruct_timed_event_struct *)data;
    if (ts->event_type == EVENT_LOG_ROTATION)
    {
        if (g_thread_running == 1 )
            livestatus_log_initial_states();
        else if (log_initial_states == 1) // initi
            write_to_all_logs("logging intitial states", LG_INFO); // initial info during startup
    }
    update_timeperiods_cache(ts->timestamp.tv_sec);
    return 0;
}



int broker_process(int event_type __attribute__ ((__unused__)), void *data)
{
    struct nebstruct_process_struct *ps = (struct nebstruct_process_struct *)data;
    if (ps->type == NEBTYPE_PROCESS_EVENTLOOPSTART) {
        update_timeperiods_cache(time(0));
        init_livecheck();
        start_threads();
    }
    return 0;
}


int verify_event_broker_options()
{
    int errors = 0;
    if (!(event_broker_options & BROKER_PROGRAM_STATE)) {
        logger( LG_CRIT, "need BROKER_PROGRAM_STATE (%i) event_broker_option enabled to work.", BROKER_PROGRAM_STATE );
        errors++;
    }
    if (!(event_broker_options & BROKER_TIMED_EVENTS)) {
        logger( LG_CRIT, "need BROKER_TIMED_EVENTS (%i) event_broker_option enabled to work.", BROKER_TIMED_EVENTS );
        errors++;
    }
    if (!(event_broker_options & BROKER_SERVICE_CHECKS)) {
        logger( LG_CRIT, "need BROKER_SERVICE_CHECKS (%i) event_broker_option enabled to work.", BROKER_SERVICE_CHECKS );
        errors++;
    }
    if (!(event_broker_options & BROKER_HOST_CHECKS)) {
        logger( LG_CRIT, "need BROKER_HOST_CHECKS (%i) event_broker_option enabled to work.", BROKER_HOST_CHECKS );
        errors++;
    }
    if (!(event_broker_options & BROKER_LOGGED_DATA)) {
        logger( LG_CRIT, "need BROKER_LOGGED_DATA (%i) event_broker_option enabled to work.", BROKER_LOGGED_DATA );
        errors++;
    }
    if (!(event_broker_options & BROKER_COMMENT_DATA)) {
        logger( LG_CRIT, "need BROKER_COMMENT_DATA (%i) event_broker_option enabled to work.", BROKER_COMMENT_DATA );
        errors++;
    }
    if (!(event_broker_options & BROKER_DOWNTIME_DATA)) {
        logger( LG_CRIT, "need BROKER_DOWNTIME_DATA (%i) event_broker_option enabled to work.", BROKER_DOWNTIME_DATA );
        errors++;
    }
    if (!(event_broker_options & BROKER_STATUS_DATA)) {
        logger( LG_CRIT, "need BROKER_STATUS_DATA (%i) event_broker_option enabled to work.", BROKER_STATUS_DATA );
        errors++;
    }
    if (!(event_broker_options & BROKER_ADAPTIVE_DATA)) {
        logger( LG_CRIT, "need BROKER_ADAPTIVE_DATA (%i) event_broker_option enabled to work.", BROKER_ADAPTIVE_DATA );
        errors++;
    }
    if (!(event_broker_options & BROKER_EXTERNALCOMMAND_DATA)) {
        logger( LG_CRIT, "need BROKER_EXTERNALCOMMAND_DATA (%i) event_broker_option enabled to work.", BROKER_EXTERNALCOMMAND_DATA );
        errors++;
    }
    if (!(event_broker_options & BROKER_STATECHANGE_DATA)) {
        logger( LG_CRIT, "need BROKER_STATECHANGE_DATA (%i) event_broker_option enabled to work.", BROKER_STATECHANGE_DATA );
        errors++;
    }

    return errors == 0;
}

void register_callbacks()
{
    neb_register_callback(NEBCALLBACK_HOST_STATUS_DATA,      g_nagios_handle, 0, broker_host); // Needed to start threads
    neb_register_callback(NEBCALLBACK_COMMENT_DATA,          g_nagios_handle, 0, broker_comment); // dynamic data
    neb_register_callback(NEBCALLBACK_DOWNTIME_DATA,         g_nagios_handle, 0, broker_downtime); // dynamic data
    neb_register_callback(NEBCALLBACK_SERVICE_CHECK_DATA,    g_nagios_handle, 0, broker_check); // only for statistics
    neb_register_callback(NEBCALLBACK_HOST_CHECK_DATA,       g_nagios_handle, 0, broker_check); // only for statistics
    neb_register_callback(NEBCALLBACK_LOG_DATA,              g_nagios_handle, 0, broker_log); // only for trigger 'log'
    neb_register_callback(NEBCALLBACK_EXTERNAL_COMMAND_DATA, g_nagios_handle, 0, broker_command); // only for trigger 'command'
    neb_register_callback(NEBCALLBACK_STATE_CHANGE_DATA,     g_nagios_handle, 0, broker_state); // only for trigger 'state'
    neb_register_callback(NEBCALLBACK_ADAPTIVE_PROGRAM_DATA, g_nagios_handle, 0, broker_program); // only for trigger 'program'
    neb_register_callback(NEBCALLBACK_PROCESS_DATA,          g_nagios_handle, 0, broker_process); // used for starting threads
    neb_register_callback(NEBCALLBACK_TIMED_EVENT_DATA,      g_nagios_handle, 0, broker_event); // used for timeperiods cache
}

void deregister_callbacks()
{
    neb_deregister_callback(NEBCALLBACK_HOST_STATUS_DATA,      broker_host);
    neb_deregister_callback(NEBCALLBACK_COMMENT_DATA,          broker_comment);
    neb_deregister_callback(NEBCALLBACK_DOWNTIME_DATA,         broker_downtime);
    neb_deregister_callback(NEBCALLBACK_SERVICE_CHECK_DATA,    broker_check);
    neb_deregister_callback(NEBCALLBACK_HOST_CHECK_DATA,       broker_check);
    neb_deregister_callback(NEBCALLBACK_LOG_DATA,              broker_log);
    neb_deregister_callback(NEBCALLBACK_EXTERNAL_COMMAND_DATA, broker_command);
    neb_deregister_callback(NEBCALLBACK_STATE_CHANGE_DATA,     broker_state);
    neb_deregister_callback(NEBCALLBACK_ADAPTIVE_PROGRAM_DATA, broker_program);
    neb_deregister_callback(NEBCALLBACK_PROCESS_DATA,          broker_program);
    neb_deregister_callback(NEBCALLBACK_TIMED_EVENT_DATA,      broker_event);
}


void check_pnp_path()
{
    struct stat st;
    if (0 == stat(g_pnp_path, &st)) {
        if (0 != access(g_pnp_path, R_OK)) {
            logger(LG_ERR, "PNP perfdata directory '%s' not readable. Please fix permissions.", g_pnp_path);
            g_pnp_path[0] = 0; // disable
        }
    }
    else {
        logger(LG_ERR, "PNP perfdata directory '%s' not existing. Please check pnp_path option!", g_pnp_path);
        g_pnp_path[0] = 0; // disable
    }
}


void livestatus_parse_arguments(const char *args_orig)
{
    /* set default socket path */
    strncpy(g_socket_path, DEFAULT_SOCKET_PATH, sizeof(g_socket_path));

    /* set default path to our logfile to be in the same path as nagios.log */
    strncpy(g_logfile_path, log_file, sizeof(g_logfile_path) - 16 /* len of "livestatus.log" */);
    char *slash = strrchr(g_logfile_path, '/');
    if (!slash)
        strcpy(g_logfile_path, "/tmp/livestatus.log");
    else
        strcpy(slash + 1, "livestatus.log");

    /* there is no default PNP path */
    g_pnp_path[0] = 0;

    /* also livecheck is disabled per default */
    g_livecheck_path[0] = 0;

    if (!args_orig)
        return; // no arguments, use default options

    char *args = strdup(args_orig);
    char *token;
    while (0 != (token = next_field(&args)))
    {
        /* find = */
        char *part = token;
        char *left = next_token(&part, '=');
        char *right = next_token(&part, 0);
        if (!right) {
            strncpy(g_socket_path, left, sizeof(g_socket_path));
        }
        else {
            if (!strcmp(left, "debug")) {
                g_debug_level = atoi(right);
                logger(LG_INFO, "Setting debug level to %d", g_debug_level);
            }
            else if (!strcmp(left, "log_file")) {
                strncpy(g_logfile_path, right, sizeof(g_logfile_path));
            }
            else if (!strcmp(left, "max_cached_messages")) {
                g_max_cached_messages = strtoul(right, 0, 10);
                logger(LG_INFO, "Setting max number of cached log messages to %lu", g_max_cached_messages);
            }
            else if (!strcmp(left, "thread_stack_size")) {
                g_thread_stack_size = strtoul(right, 0, 10);
                logger(LG_INFO, "Setting size of thread stacks to %lu", g_thread_stack_size);
            }
            else if (!strcmp(left, "max_response_size")) {
                g_max_response_size = strtoul(right, 0, 10);
                logger(LG_INFO, "Setting maximum response size to %lu bytes (%.1f MB)",
                        g_max_response_size, g_max_response_size / (1024.0*1024.0));
            }
            else if (!strcmp(left, "num_client_threads")) {
                int c = atoi(right);
                if (c <= 0 || c > 1000)
                    logger(LG_INFO, "Error: Cannot set num_client_threads to %d. Must be > 0 and <= 1000", c);
                else {
                    logger(LG_INFO, "Setting number of client threads to %d", c);
                    g_num_clientthreads = c;
                }
            }
            else if (!strcmp(left, "query_timeout")) {
                int c = atoi(right);
                if (c < 0)
                    logger(LG_INFO, "Error: query_timeout must be >= 0");
                else {
                    g_query_timeout_msec = c;
                    if (c == 0)
                        logger(LG_INFO, "Disabled query timeout!");
                    else
                        logger(LG_INFO, "Setting timeout for reading a query to %d ms", c);
                }
            }
            else if (!strcmp(left, "idle_timeout")) {
                int c = atoi(right);
                if (c < 0)
                    logger(LG_INFO, "Error: idle_timeout must be >= 0");
                else {
                    g_idle_timeout_msec = c;
                    if (c == 0)
                        logger(LG_INFO, "Disabled idle timeout!");
                    else
                        logger(LG_INFO, "Setting idle timeout to %d ms", c);
                }
            }
            else if (!strcmp(left, "service_authorization")) {
                if (!strcmp(right, "strict"))
                    g_service_authorization = AUTH_STRICT;
                else if (!strcmp(right, "loose"))
                    g_service_authorization = AUTH_LOOSE;
                else {
                    logger(LG_INFO, "Invalid service authorization mode. Allowed are strict and loose.");
                }
            }
            else if (!strcmp(left, "group_authorization")) {
                if (!strcmp(right, "strict"))
                    g_group_authorization = AUTH_STRICT;
                else if (!strcmp(right, "loose"))
                    g_group_authorization = AUTH_LOOSE;
                else {
                    logger(LG_INFO, "Invalid group authorization mode. Allowed are strict and loose.");
                }
            }
            else if (!strcmp(left, "pnp_path")) {
                strncpy(g_pnp_path, right, sizeof(g_pnp_path) - 1);
                if (right[strlen(right) - 1] != '/')
                    strncat(g_pnp_path, "/",  sizeof(g_pnp_path) - strlen(g_pnp_path) - 1 ); // make sure, that trailing slash is always there
                check_pnp_path();
            }
            else if (!strcmp(left, "data_encoding")) {
                if (!strcmp(right, "utf8"))
                    g_data_encoding = ENCODING_UTF8;
                else if (!strcmp(right, "latin1"))
                    g_data_encoding = ENCODING_LATIN1;
                else if (!strcmp(right, "mixed"))
                    g_data_encoding = ENCODING_MIXED;
                else {
                    logger(LG_INFO, "Invalid data_encoding %s. Allowed are utf8, latin1 and mixed.", right);
                }
            }
            else if (!strcmp(left, "livecheck")) {
                strncpy(g_livecheck_path, right, sizeof(g_livecheck_path) - 1);
                if (0 != access(g_livecheck_path, X_OK)) {
                    logger(LG_INFO, "ERROR: %s is not executable. Disabling livecheck.", g_livecheck_path);
                    g_livecheck_path[0] = 0;
                }
                g_livecheck_enabled = true;
            }
            else if (!strcmp(left, "num_livecheck_helpers")) {
                g_num_livehelpers = atoi(right);
            }
            else if (!strcmp(left, "disable_statehist_filtering"))
            {
                g_disable_statehist_filtering = atoi(right);
            }
            else {
                logger(LG_INFO, "Ignoring invalid option %s=%s", left, right);
            }
        }
    }
    // free(args); won't free, since we use pointers?
}

void omd_advertize()
{
    char *omd_site = getenv("OMD_SITE");
    if (omd_site) {
        if (g_debug_level > 0)
            logger(LG_INFO, "Running on OMD site %s. Cool.", omd_site);
    }
    else {
        logger(LG_INFO, "Hint: please try out OMD - the Open Monitoring Distribution");
        logger(LG_INFO, "Please visit OMD at http://omdistro.org");
    }
}


/* this function gets called when the module is loaded by the event broker */
int nebmodule_init(int flags __attribute__ ((__unused__)), char *args, void *handle)
{
    g_nagios_handle = handle;
    livestatus_parse_arguments(args);
    open_logfile();

    logger(LG_INFO, "Livestatus %s by Mathias Kettner. Socket: '%s'", VERSION, g_socket_path);
    logger(LG_INFO, "Please visit us at http://mathias-kettner.de/");

    omd_advertize();

    if (!open_unix_socket())
        return 1;

    if (!verify_event_broker_options()) {
        logger(LG_CRIT, "Fatal: bailing out. Please fix event_broker_options.");
        logger(LG_CRIT, "Hint: your event_broker_options are set to %d. Try setting it to -1.", event_broker_options);
        return 1;
    }
    else if (g_debug_level > 0)
        logger(LG_INFO, "Your event_broker_options are sufficient for livestatus..");

    if (enable_environment_macros == 1)
        logger(LG_INFO, "Warning: environment_macros are enabled. This might decrease the overall nagios performance");

    store_init();
    register_callbacks();

    /* Unfortunately, we cannot start our socket thread right now.
       Nagios demonizes *after* having loaded the NEB modules. When
       demonizing we are losing our thread. Therefore, we create the
       thread the first time one of our callbacks is called. Before
       that happens, we haven't got any data anyway... */

    logger(LG_INFO, "Finished initialization. Further log messages go to %s", g_logfile_path);
    return 0;
}


int nebmodule_deinit(int flags __attribute__ ((__unused__)), int reason __attribute__ ((__unused__)))
{
    logger(LG_INFO, "deinitializing");
    terminate_threads();
    close_unix_socket();
    store_deinit();
    deregister_callbacks();
    deinit_livecheck();
    close_logfile();
    return 0;
}

