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

#include <stdio.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <sys/timeb.h>
#include <sys/resource.h>
#include <netinet/ip.h>
#include <stdlib.h>
#include <fcntl.h>
#include <string.h>

#include "strutil.h"

pid_t g_pid;
static void alarm_handler(int);
static void term_handler(int);
static char **parse_into_arguments(char *command);
int check_icmp(int argc, char **argv, char *output, int size);
int icmp_sock = -1;

// This program must be called with two arguments:
// 1. Path to check result directory
// 2. timeout for host checks
// 3. timeout for service checks
int main(int argc, char **argv)
{
    if (argc != 4) {
        fprintf(stderr, "Usage: %s CHECKRESULTPATH HOST_CHECK_TIMEOUT SERVICE_CHECK_TIMEOUT\n", argv[0]);
        exit(1);
    }
    char *check_result_path = argv[1];
    int host_check_timeout = atoi(argv[2]);
    int service_check_timeout = atoi(argv[3]);

    char host[256];
    char service[512];
    char latency[16];
    char command[1024];
    int pid;
    int check_result;
    int real_uid = getuid(); // non-root user id
    int real_gid = getgid(); // non-root group id

    signal(SIGALRM, alarm_handler); // handler for check timeout
    signal(SIGINT,  term_handler);
    signal(SIGQUIT, term_handler);
    signal(SIGTERM, term_handler);

    while (1) {
        write(1, "*", 1); // Signal Nagios that we are finished
        if (NULL == fgets(host, sizeof(host), stdin)
         || NULL == fgets(service, sizeof(service), stdin)
         || NULL == fgets(latency, sizeof(latency), stdin)
         || NULL == fgets(command, sizeof(command), stdin))
        {
            exit(0);
        }

        int is_host_check = service[0] == '\n';
        struct timeb start;
        ftime(&start);
        char output[16384];
        int return_code;
        // Optimization(1):
        // If it's check_icmp, we use our inline version
        // of that. But only if we have (had) root priviledges
        // and had been able to create a raw socket
        if (geteuid() == 0 && strstr(command, "/check_icmp ")) {
            char **arguments = parse_into_arguments(command);
            int arg_c = 0;
            while (arguments[arg_c])
                arg_c++;
            return_code = check_icmp(arg_c, arguments, output, sizeof(output));
        }
        else {
            int fd[2];
            pipe(fd);

            pid = fork();
            if (pid == 0) {
                // Drop root priviledges: only needed for ICMP socket
                if (geteuid() == 0)
                    setuid(getuid());

                // Assign this child its own process group, so
                // we can kill its entire process group when a timeout occurs
                setpgid(getpid(), 0);

                close(fd[0]);   // close read end
                dup2(fd[1], 1); // point stdout into pipe
                dup2(fd[1], 2); // also point stderr into pipe
                close(fd[1]);   // lives forth in 1 and 2
                int f = open("/dev/null", O_RDONLY);
                dup2(f, 0);
                close(f);

                // Allow for larger stack size
                struct rlimit rl;
                getrlimit(RLIMIT_STACK, &rl);
                rl.rlim_cur = 32 * 1024 * 1024;
                rl.rlim_max = 32 * 1024 * 1024;
                setrlimit(RLIMIT_STACK, &rl);

                // Optimization(2):
                // if Command begins / and command line does not
                // contain any ', /, < or >, split by spaces and
                // directly call exec.
                // This save two fork()s and one shell.
                if (command[0] == '/'
                    && NULL == strchr(command, '"')
                    && NULL == strchr(command, '\'')
                    && NULL == strchr(command, '>')
                    && NULL == strchr(command, '<')
                    && NULL == strchr(command, ';')
                    && NULL == strchr(command, '|'))
                {
                    char **arguments = parse_into_arguments(command);
                    execv(arguments[0], arguments);
                }
                else {
                    int ret = system(command);
                    if (WIFEXITED(ret))
                        exit(WEXITSTATUS(ret));
                }
                exit(127);
            }
            else { /* parent process */
                close(fd[1]);
                g_pid = pid;
                unsigned timeout = is_host_check ? host_check_timeout : service_check_timeout;
                if (timeout)
                    alarm(timeout);

                int bytes_read = 0;
                char *ptr_output = output;
                const char *ptr_end = output + sizeof(output) - 1;
                while ((bytes_read = read(fd[0], ptr_output, ptr_end - ptr_output)) != 0) {
                    ptr_output += bytes_read;
                    if (ptr_output == ptr_end)
                        break;
                }
                *ptr_output = 0;

                close(fd[0]);
                int ret;
                waitpid(pid, &ret, 0);
                g_pid = 0;
                alarm(0); // cancel timeout

                if (WIFSIGNALED(ret)) {
                    int signum = WTERMSIG(ret);
                    if (signum == SIGKILL) {
                        snprintf(output, sizeof(output), "(Check Timed Out After %d Seconds)\n", timeout);
                        return_code = 3;
                    }
                    else {
                        snprintf(output, sizeof(output), "(Check Plugin Died With Signal %d)\n", signum);
                        return_code = 3;
                    }
                }
                else {
                    return_code = WEXITSTATUS(ret);
                    if (*output == 0 || *output == '\n')
                        snprintf(output, sizeof(output), "(No output returned from plugin)\n");
                }
            }
        }
        struct timeb end;
        ftime(&end);
        char template[256];
        snprintf(template, sizeof(template), "%s/cXXXXXX", check_result_path);
        int fd = mkstemp(template);
        fchmod(fd, 0600);
        FILE *checkfile = fdopen(fd, "w");
        fprintf(checkfile, "host_name=%s", host);
        if (!is_host_check)
            fprintf(checkfile, "service_description=%s", service);
        fprintf(checkfile,
            "### Check result created by livecheck(%d)\n"
            "check_type=%d\n"
            "check_options=0\n"
            "scheduled_check=1\n"
            "reschedule_check=1\n"
            "latency=%s"
            "start_time=%d.%03u\n"
            "finish_time=%d.%03u\n"
            "return_code=%d\n"
            "output=",
            getpid(),
            0,
            latency,
            (int)start.time,
            start.millitm,
            (int)end.time,
            end.millitm,
            return_code);
        char *ptr_output = output;
        char *ptr_walk   = output;
        while (*ptr_walk != 0) {
            if (*ptr_walk == '\n') {
                *ptr_walk = 0;
                fputs(ptr_output, checkfile);
                fputs("\\n", checkfile);
                ptr_output = ptr_walk + 1;
            } else if (*ptr_walk == '\\') {
                *ptr_walk = 0;
                fputs(ptr_output, checkfile);
                fputs("\\\\", checkfile);
                ptr_output = ptr_walk + 1;
            }
            if (*ptr_output == 0)
            	break;
            ptr_walk++;
        }
        if(*ptr_output) {
            fputs(ptr_output, checkfile);
        }
        fputs("\n", checkfile);

        fchown(fd, real_uid, real_gid);
        fclose(checkfile);
        strcat(template, ".ok");
        fd = creat(template, 0600);
        fchown(fd, real_uid, real_gid);
        close(fd);
    }
}

static char **parse_into_arguments(char *command)
{
    static char *arguments[128];
    char *c = command;
    char *executable = next_field(&c);
    arguments[0] = executable;
    unsigned a = 1;
    while (a < 127) {
        char *arg = next_field(&c);
        arguments[a++] = arg;
        if (!arg) break;
    }
    return arguments;
}

// Propagate signal to child, if we are killed
static void term_handler(int signum)
{
    if (g_pid) {
        kill(g_pid, signum);
    }
    exit(0);
}

// handle check timeout
void alarm_handler(int signum)
{
    if (g_pid) {
        kill(-g_pid, SIGKILL);
    }
}
