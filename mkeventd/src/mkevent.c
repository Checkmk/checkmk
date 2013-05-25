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

#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <sys/socket.h>
#include <netinet/in.h>

/* Methods for specified the path to the pipe of
   mkeventd:

   1. Run mkevent within the environment of a
      OMD site -> will find pipe itself

   2. Specify pipe with -P PATH before message

   3. Run mkeventd with absolute path in a site,
      e.g. /omd/sites/mysite/bin/mkevent -> will
      find pipe itself

   4. Uses hardcoded path /var/run/mkeventd.pipe.

*/

int file_exists(char *path)
{
    struct stat st;
    return (0 == stat(path, &st));
}


char *append_str(char *str, char *dest)
{
    int len = strlen(str);
    memcpy(dest, str, len);
    return dest + len;
}

char *append_int(long n, char *dest)
{
    static char digits[] = "0123456789";
    char buf[32];
    buf[31] = 0;
    char *b = buf + 31;
    do {
        *(--b) = digits[n % 10];
    } while ((n /= 10) > 0);
    return append_str(b, dest);
}

int main(int argc, char **argv)
{
    if (argc < 2) {
        write(2, "Usage: mkevent [-P PIPE] 'Text of the messsage'\n", 48);
        exit(1);
    }


    char path_to_pipe[256];
    path_to_pipe[0] = 0;

    /* Path to pipe can be specified with -P */
    if (argc > 2 && !strcmp(argv[1], "-P")) {
        strncpy(path_to_pipe, argv[2], sizeof(path_to_pipe));
        argc -= 2;
        argv += 2;
    }

    if (!path_to_pipe[0]) {
        const char *omd_root = getenv("OMD_ROOT");
        if (omd_root) {
            strncpy(path_to_pipe, omd_root, 128);
            strcat(path_to_pipe, "/tmp/run/mkeventd/events");
        }
        else if (!strncmp(argv[0], "/omd/sites/", 11)) {
            bzero(path_to_pipe, sizeof(path_to_pipe));
            strncpy(path_to_pipe, argv[0], strlen(argv[0]) - 11); /* cut off bin/mkevent */
            strcat(path_to_pipe, "tmp/run/mkeventd/events");
        }
    }

    /* Nagios notification mode is triggered with option -n */
    char message[8192];
    char *remote = "";

    if (argc > 9 && !strcmp(argv[1], "-n")) {
        /* Arguments: -n FACILITY REMOTE STATE HOST SERVICE MESSAGE */
        /* SERVICE is empty for host notification */
        int facility   = atoi(argv[2]);
        remote   = argv[3];
        int state      = atoi(argv[4]);
        char *hostname = argv[5];
        char *service  = argv[6];
        char *text     = argv[7];
        char *sl_text  = argv[8];
        char *contact  = argv[9];

        /* If this is a service and sl/contact is unset then we use
           the values of the host that are coming as arg 10 and 11 */
        if (sl_text[0] == '$' && argc > 11)
            sl_text = argv[10];
        if (contact[0] == '$' && argc > 11)
            contact = argv[11];

        int sl = atoi(sl_text);
        if (contact[0] == '$')
            contact = "";

        int priority;
        if (state == 0)
            priority = 5;
        else {
            if (!service[0])
                state += 1; // shift host states in order to map service states
            if (state == 1)
                priority = 4; // warn
            else if (state == 3)
                priority = 3; // map UNKNOWN/UNREAD to err
            else
                priority = 2; // CRIT/DOWN goes to crit
        }

        char *w = message;
        *w++ = '<';
        w = append_int((facility << 3) + priority, w);
        *w++ = '>';
        *w++ = '@';
        w = append_int(time(0), w);
        *w++ = ';';
        w = append_int(sl, w);
        *w++ = ';';
        w = append_str(contact, w);
        *w++ = ';';
        *w++ = ' ';
        w = append_str(hostname, w);
        *w++ = ' ';
        w = append_str(service[0] ? service : "HOST", w);
        *w ++ = ':';
        *w ++ = ' ';
        w = append_str(text, w);
        *w = 0;
    }
    else {
        strncpy(message, argv[1], sizeof(message));
    }

    /* If we have a remote host and there is no local event Console running,
       then we will send the message via syslog to the remote host. */
    int fd;
    if (!file_exists(path_to_pipe) && remote[0]) {
        if (!isdigit(remote[0])) {
            write(1, "ERROR: Please specify the remote host as IPv4 address, not '", 60);
            write(1, remote, strlen(remote));
            write(1, "'\n", 2);
            exit(1);
        }
        fd = socket(AF_INET, SOCK_DGRAM, 0);
        struct sockaddr_in servaddr;
        bzero(&servaddr,sizeof(servaddr));
        servaddr.sin_family = AF_INET;
        servaddr.sin_addr.s_addr = inet_addr(remote);
        servaddr.sin_port = htons(514);
        sendto(fd, message, strlen(message), 0, (struct sockaddr *)&servaddr,sizeof(servaddr));
    }
    else {
        fd = open(path_to_pipe, O_WRONLY);
        if (fd < 0) {
            strcpy(message, "Cannot open event pipe ");
            strcat(message, path_to_pipe);
            perror(message);
            exit(1);
        }
        write(fd, message, strlen(message));
        write(fd, "\n", 1);
    }
    close(fd);
    return 0;
}

