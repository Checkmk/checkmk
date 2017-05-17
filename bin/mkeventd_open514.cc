// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
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

/* This small helper program is intended to be installed SUID root.
   Otherwise it is pointless. It creates a UDP socket with port 514.
   This is a priviledged operation. Then it drops the priviledges,
   moves that port to file descriptor 3 and executes the mkeventd.

   That can then simply use filedescriptor 3 and receive syslog
   messages */

#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>

#define SYSLOG_PORT 514
#define SNMPTRAP_PORT 162

#define PROGRAM "mkeventd"

// Example command line:
// mkeventd_open514 --syslog --syslog-fd 3 --syslog-tcp --syslog-tcp-fd 4
// --snmptrap --snmptrap-fd 5

int main(int argc, char **argv) {
    int do_syslog = 0;
    int do_syslog_tcp = 0;
    int do_snmptrap = 0;

    int syslog_fd = -1;
    int syslog_tcp_fd = -1;
    int snmptrap_fd = -1;

    int i;

    for (i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--syslog") == 0) {
            do_syslog = 1;
        } else if (strcmp(argv[i], "--syslog-tcp") == 0) {
            do_syslog_tcp = 1;
        } else if (strcmp(argv[i], "--snmptrap") == 0) {
            do_snmptrap = 1;
        } else if (strcmp(argv[i], "--syslog-fd") == 0) {
            syslog_fd = atoi(argv[i + 1]);
        } else if (strcmp(argv[i], "--syslog-tcp-fd") == 0) {
            syslog_tcp_fd = atoi(argv[i + 1]);
        } else if (strcmp(argv[i], "--snmptrap-fd") == 0) {
            snmptrap_fd = atoi(argv[i + 1]);
        }
    }

    // Syslog via UDP
    if (do_syslog != 0 && syslog_fd > 0) {
        // Create socket
        int syslog_sock;
        if (0 > (syslog_sock = socket(PF_INET, SOCK_DGRAM, 0))) {
            perror("Cannot create UDP socket for syslog");
            exit(1);
        }

        // set REUSEADDR
        int optval = 1;
        if (0 != setsockopt(syslog_sock, SOL_SOCKET, SO_REUSEADDR, &optval,
                            sizeof(optval))) {
            perror("Cannot set UDP socket for syslog to SO_REUSEADDR");
            exit(1);
        }

        // Bind it to the port (this requires priviledges)
        struct sockaddr_in addr;
        addr.sin_family = AF_INET;
        addr.sin_port = htons(SYSLOG_PORT);
        addr.sin_addr.s_addr = 0;
        if (0 != bind(syslog_sock, reinterpret_cast<struct sockaddr *>(&addr),
                      sizeof(addr))) {
            perror("Cannot bind UDP socket for syslog to port");
            exit(1);
        }

        // Make sure it is at the correct FD
        if (syslog_sock != 0 && syslog_sock != syslog_fd) {
            dup2(syslog_sock, syslog_fd);
            close(syslog_sock);
        }
    }

    // Syslog via TCP
    if (do_syslog_tcp != 0 && syslog_tcp_fd > 0) {
        // Create socket
        int syslog_tcp_sock;
        if (0 > (syslog_tcp_sock = socket(PF_INET, SOCK_STREAM, 0))) {
            perror("Cannot create TCP socket for syslog-tcp");
            exit(1);
        }

        // set REUSEADDR
        int optval = 1;
        if (0 != setsockopt(syslog_tcp_sock, SOL_SOCKET, SO_REUSEADDR, &optval,
                            sizeof(optval))) {
            perror("Cannot set TCP socket for syslog-tcp to SO_REUSEADDR");
            exit(1);
        }

        // Bind it to the port (this requires priviledges)
        struct sockaddr_in addr;
        addr.sin_family = AF_INET;
        addr.sin_port = htons(SYSLOG_PORT);
        addr.sin_addr.s_addr = 0;
        if (0 != bind(syslog_tcp_sock,
                      reinterpret_cast<struct sockaddr *>(&addr),
                      sizeof(addr))) {
            perror("Cannot bind TCP socket for syslog-tcp to port");
            exit(1);
        }

        // Make sure it is at the correct FD
        if (syslog_tcp_sock != 0 && syslog_tcp_sock != syslog_tcp_fd) {
            dup2(syslog_tcp_sock, syslog_tcp_fd);
            close(syslog_tcp_sock);
        }
    }

    // SNMP traps
    if (do_snmptrap != 0 && snmptrap_fd > 0) {
        // Create socket
        int snmptrap_sock;
        if (0 > (snmptrap_sock = socket(PF_INET, SOCK_DGRAM, 0))) {
            perror("Cannot create UDP socket for snmptrap");
            exit(1);
        }

        // set REUSEADDR
        int optval = 1;
        if (0 != setsockopt(snmptrap_sock, SOL_SOCKET, SO_REUSEADDR, &optval,
                            sizeof(optval))) {
            perror("Cannot set UDP socket for snmptrap to SO_REUSEADDR");
            exit(1);
        }

        // Bind it to the port (this requires priviledges)
        struct sockaddr_in addr;
        addr.sin_family = AF_INET;
        addr.sin_port = htons(SNMPTRAP_PORT);
        addr.sin_addr.s_addr = 0;
        if (0 != bind(snmptrap_sock, reinterpret_cast<struct sockaddr *>(&addr),
                      sizeof(addr))) {
            perror("Cannot bind UDP socket for snmptrap to port");
            exit(1);
        }

        // Make sure it is at the correct FD
        if (snmptrap_sock != 0 && snmptrap_sock != snmptrap_fd) {
            dup2(snmptrap_sock, snmptrap_fd);
            close(snmptrap_sock);
        }
    }

    // Drop priviledges
    if (getuid() != geteuid()) {
        if (0 != seteuid(getuid())) {
            perror("Cannot drop priviledges");
            exit(1);
        }
    }

    // Execute the actual program that needs access to the
    // socket. We take the path from argv[0]
    char *last_slash = argv[0];
    char *scan = argv[0];
    while (*scan != 0) {
        if (*scan == '/') {
            last_slash = scan + 1;
        }
        scan++;
    }
    char newpath[512];
    bzero(&newpath, 512);
    int len_to_copy = last_slash - argv[0];
    if (len_to_copy >= 512) {
        exit(1);
    }

    memcpy(newpath, argv[0], len_to_copy);
    strncpy(newpath + len_to_copy, PROGRAM, 511 - len_to_copy);
    execv(newpath, argv);
    perror("Cannot execute mkeventd");
}
