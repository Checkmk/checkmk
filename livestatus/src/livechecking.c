// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2012             mk@mathias-kettner.de |
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


#include <sys/types.h>
#include <errno.h>
#include <sys/resource.h>

#include "nagios.h"
#include "logger.h"
#include "global_counters.h"

extern int g_debug_level;

extern int currently_running_host_checks;
extern int currently_running_service_checks;
extern char *check_result_path;
extern char g_livecheck_path[];
extern int host_check_timeout;
extern int service_check_timeout;

int g_num_livehelpers = 20;
int g_livecheck_enabled = 0;

#define LH_BUSY 0
#define LH_READY   1
#define LH_DEAD    2

struct live_helper {
    int id;
    pid_t pid;
    int sock;
    FILE *fsock;
    int status;
};
struct live_helper *g_live_helpers;

void start_livecheck_helper(struct live_helper *lh)
{
    int fd[2]; // fd[0] used by us, fd[1] by livecheck helper
    socketpair(AF_UNIX, SOCK_STREAM, 0, fd);
    pid_t pid = fork();
    if (pid == 0) {
        dup2(fd[1], 0);
        dup2(fd[1], 1);
        dup2(fd[1], 2);
        close(fd[0]);

        // close all other inherited filedescriptiors
        unsigned i;
        for (i=3; i<1024; i++) {
            close(i);
        }
        
        char ht[32];
        snprintf(ht, sizeof(ht), "%u", host_check_timeout);
        char st[32];
        snprintf(st, sizeof(st), "%u", service_check_timeout);

        // reduce stack size in order to save memory
        struct rlimit rl;
        getrlimit(RLIMIT_STACK, &rl);
        rl.rlim_cur = 65536;
        setrlimit(RLIMIT_STACK, &rl);
        execl(g_livecheck_path, "livecheck", check_result_path, ht, st, (char *)0);
        logger(LG_INFO, "ERROR: Cannot start livecheck helper: %s", strerror(errno));
        exit(1);
    }
    close(fd[1]);
    // Make sure our socket is not forked() by Nagios
    if (0 < fcntl(fd[0], F_SETFD, FD_CLOEXEC)) {
        logger(LG_INFO, "WARNING: Cannot set FD_CLOEXEC on fd %d: %s",
           fd[0], strerror(errno));
    }
    lh->pid = pid;
    lh->sock = fd[0];
    lh->fsock = fdopen(fd[0], "r+");
    lh->status = LH_BUSY; // wait until helper sends "ready" byte.
}

void terminate_livecheck_helper(struct live_helper *lh) {
    fclose(lh->fsock);
    kill(lh->pid, SIGTERM);
    int status;
    if (lh->pid != waitpid(lh->pid, &status, 0))
    {
        // Nagios calls waitpid(-1, ...) from time to time and that
        // wait catches away our exit code. They should better know
        // which PID they are looking for :-(...
        if (g_debug_level > 0)
            logger(LG_INFO, "Could not wait() Livecheck helper [%d:%d], "
                            "Nagios was faster.", lh->pid, lh->sock);
    }
    else if (WIFSIGNALED(status) && WTERMSIG(status) != SIGTERM)
    {
        logger(LG_INFO, "Livecheck helper [%d:%d:%d] exited with signal %d.",
            lh->id, lh->pid, lh->sock, WTERMSIG(status));
    }
    else if (g_debug_level > 0) {
        logger(LG_INFO, "Livecheck helper [%d:%d:%d] exited with status %d.",
            lh->id, lh->pid, lh->sock, status);
    }
}

void restart_livecheck_helper(struct live_helper *lh)
{
    terminate_livecheck_helper(lh);
    start_livecheck_helper(lh);
}

void execute_livecheck(struct live_helper *lh, const char *host_name,
       const char *service_description, double latency, const char *command)
{
    if (g_debug_level > 0)
        logger(LG_INFO, "Executing livecheck for %s %s", host_name, service_description);
    char signalbyte;
    if (1 != read(lh->sock, &signalbyte, 1)) {
        logger(LG_INFO, "ERROR: Livecheck helper [%d:%d:%d] not responding. "
                        "Restarting.", lh->id, lh->pid, lh->sock);
        restart_livecheck_helper(lh);
        /* trying again to read the ready byte. */
        if (1 != read(lh->sock, &signalbyte, 1)) {
            logger(LG_INFO, "FATAL: Restarted helper [%d:%d:%d] doesn't "
                            "seem to live.", lh->id, lh->pid, lh->sock);
            lh->status = LH_DEAD;
            return; // This check will never be executed
        }
    }
    fprintf(lh->fsock, "%s\n%s\n%.3f\n%s\n",
        host_name, service_description, latency, command);
    fflush(lh->fsock);
    g_counters[COUNTER_LIVECHECKS]++;
}

struct live_helper *get_free_live_helper()
{
    // Check if one of our helpers is free. First look
    // at the flag
    unsigned i;
    for (i=0; i<g_num_livehelpers; i++) {
        if (g_live_helpers[i].status == LH_READY) {
            g_live_helpers[i].status = LH_BUSY;
            return &g_live_helpers[i];
        }
    }

    // None none to be free -> use select to detect livehelpers
    // that have signalled us (by sending a byte) that they are
    // free again.
    fd_set fds;
    FD_ZERO(&fds);
    int max_fd = 0;
    for (i=0; i<g_num_livehelpers; i++) {
        if (g_live_helpers[i].status != LH_BUSY) {
            continue;
        }
        int fd = g_live_helpers[i].sock;
        FD_SET(fd, &fds);
        if (fd >= max_fd)
            max_fd = fd;
    }
    struct timeval tv;
    tv.tv_sec = 0;
    tv.tv_usec = 0;
    int r = select(max_fd + 1, &fds, 0, 0, &tv);

    // No filedescriptor readable -> all livecheck helpers are busy!
    if (r == 0)
        return 0;

    struct live_helper *free_helper = 0;
    for (i=0; i<g_num_livehelpers; i++) {
        if (FD_ISSET(g_live_helpers[i].sock, &fds))
            g_live_helpers[i].status = LH_READY;
            free_helper = &g_live_helpers[i]; // could be a candidate
    }
    
    // use last found free helper. Do not forget to set this to BUSY!
    // (this was a bug in previous versions)
    free_helper->status = LH_BUSY;
    return free_helper;
}


int broker_host_livecheck(int event_type __attribute__ ((__unused__)), void *data)
{
    nebstruct_host_check_data *hstdata = (nebstruct_host_check_data *)data;
    if (event_type != NEBCALLBACK_HOST_CHECK_DATA
        || hstdata->type != NEBTYPE_HOSTCHECK_ASYNC_PRECHECK)
        return NEB_OK; // ignore other events
    host *hst = hstdata->object_ptr;

    struct live_helper *lh = get_free_live_helper();
    if (!lh) {
        if (g_debug_level > 0)
            logger(LG_INFO, "No livecheck helper free.");
        return NEB_OK;
    }

    // Make core statstics work correctly
    hst->check_options=CHECK_OPTION_NONE;
    currently_running_host_checks++;
    hst->is_executing=TRUE;

    // construct command line
    clear_volatile_macros();
    grab_host_macros(hst);

    char *raw_command;
    get_raw_command_line(hst->check_command_ptr, hst->host_check_command, &raw_command,0);
    char *processed_command;
    process_macros(raw_command, &processed_command, 0);

    execute_livecheck(lh, hst->name, "", hstdata->latency, processed_command);

    free(raw_command);
    free(processed_command);
    return NEBERROR_CALLBACKOVERRIDE;
}

int broker_service_livecheck(int event_type __attribute__ ((__unused__)), void *data)
{
    nebstruct_service_check_data *svcdata = (nebstruct_service_check_data *)data;
    if (event_type != NEBCALLBACK_SERVICE_CHECK_DATA
        || svcdata->type != NEBTYPE_SERVICECHECK_ASYNC_PRECHECK)
        return NEB_OK; // ignore other events
    service *svc = svcdata->object_ptr;

    struct live_helper *lh = get_free_live_helper();
    if (!lh) {
        if (g_debug_level > 0)
            logger(LG_INFO, "No livecheck helper free.");
        // Let the core handle this check himself
        g_counters[COUNTER_LIVECHECK_OVERFLOWS]++;
        return NEB_OK;
    }

    // Make core statstics work correctly
    svc->check_options=CHECK_OPTION_NONE;
    currently_running_service_checks++;
    svc->is_executing=TRUE;

    // construct command line
    clear_volatile_macros();
    grab_host_macros(svc->host_ptr);
    grab_service_macros(svc);
    char *raw_command;
    get_raw_command_line(svc->check_command_ptr, svc->service_check_command, &raw_command,0);
    char *processed_command;
    process_macros(raw_command, &processed_command, 0);

    execute_livecheck(lh, svc->host_name, svc->description, svcdata->latency, processed_command);

    free(raw_command);
    free(processed_command);
    return NEBERROR_CALLBACKOVERRIDE;
}


void init_livecheck()
{
    if (!g_livecheck_enabled)
        return;

    logger(LG_INFO, "Starting %d livechecks helpers", g_num_livehelpers);
    g_live_helpers = (struct live_helper *)malloc(sizeof(struct live_helper) * g_num_livehelpers);

    unsigned i;
    for (i=0; i<g_num_livehelpers; i++) {
        g_live_helpers[i].id = i;
        start_livecheck_helper(&g_live_helpers[i]);
    }
}


void deinit_livecheck()
{
    if (!g_livecheck_enabled)
        return;

    unsigned i;
    for (i=0; i<g_num_livehelpers; i++)
        terminate_livecheck_helper(&g_live_helpers[i]);
    free(g_live_helpers);
}
