// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2010             mk@mathias-kettner.de |
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
#include <stdlib.h>
#include <fcntl.h>
#include <string.h>

#include "strutil.h"

int main(int argc, char **argv)
{ 
    char *check_result_path = argv[1];
    char host[256];
    char service[512];
    char latency[16];
    char command[1024]; 
    int pid;
    int check_result;

    while (1) {
        write(1, "*", 1); // Signal Nagios that we are finished
        if (NULL == fgets(host, sizeof(host), stdin)
         || NULL == fgets(service, sizeof(service), stdin)
         || NULL == fgets(latency, sizeof(latency), stdin)
         || NULL == fgets(command, sizeof(command), stdin))
        {
            exit(0);
        }
    
        int fd[2];
        pipe(fd);

        pid = fork();
        struct timeb start;
        ftime(&start);

        if (pid == 0) {
            close(fd[0]);   // close read end
            dup2(fd[1], 1); // point stdout into pipe  
            dup2(fd[1], 2); // also point stderr into pipe
            int f = open("/dev/null", O_RDONLY);
            dup2(f, 0);

            // Optimization:
            // if Command begins / and command line does not
            // contain any ', /, < or >, split by spaces and
            // directly call exec.
            // This save two fork()s and one shell.
            if (command[0] == '/'
                && NULL == strchr(command, '"') 
                && NULL == strchr(command, '\'') 
                && NULL == strchr(command, '>') 
                && NULL == strchr(command, '<') 
                && NULL == strchr(command, '|'))
            {
                char *c = command;
                char *arguments[128];
                char *executable = next_field(&c);
                arguments[0] = executable;
                unsigned a = 1;
                while (a < 127) {
                    char *arg = next_field(&c);
                    arguments[a++] = arg;
                    if (!arg) break;
                }
                execv(executable, arguments);
            }
            else {
                int ret = system(command);
                if (WIFEXITED(ret))
                    exit(WEXITSTATUS(ret));
            }
            exit(127);
        }

        else {
            char output[1024]; 
            int bytes_read = read(fd[0], output, sizeof(output));
            int ret;
            waitpid(pid, &ret, 0);
            int return_code;

            if (WIFEXITED(ret))
                return_code = WEXITSTATUS(ret);
            else {
                if (0 == bytes_read)
                    sprintf(output, "Error executing %s\n", command);
                return_code = 3;
            }
            struct timeb end;
            ftime(&end);
            char template[256];
            snprintf(template, sizeof(template), "%s/cXXXXXX", check_result_path);
            char *foo = mktemp(template);
            FILE *checkfile = fopen(template, "w");
            fprintf(checkfile, "host_name=%s", host);
            if (service[0] != '\n')
                fprintf(checkfile, "service_description=%s", service);
            fprintf(checkfile, 
                "check_type=%d\n"
                "check_options=0\n"
                "scheduled_check=1\n"
                "reschedule_check=1\n"
                "latency=%s"
                "start_time=%d.%03u\n" 
                "finish_time=%d.%03u\n"
                "return_code=%d\n"                                                   
                "output=%s\n", 
                service[0] == '\n' ? 0 : 1,
                latency,
                (int)start.time,
                start.millitm,
                (int)end.time,
                end.millitm,
                return_code,
                output);
            fclose(checkfile);
            strcat(template, ".ok");
            close(creat(template, 0644));
        }
    }
}
