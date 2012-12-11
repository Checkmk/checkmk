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

/* This small helper program is intended to be installed SUID root.
   Otherwise it is pointless. It creates a UDP socket with port 514.
   This is a priviledged operation. Then it drops the priviledges,
   moves that port to file descriptor 3 and executes the mkeventd.

   That can then simply use filedescriptor 3 and receive syslog 
   messages */

#include <sys/types.h>
#include <sys/socket.h>
#include <strings.h>
#include <string.h>
#include <netinet/in.h>
#include <stdlib.h>
#include <stdio.h>

#define PORT    514
#define FD      3
#define PROGRAM "mkeventd"

int main(int argc, char **argv)
{
    int sock;

    // Create socket
    if (0 > (sock = socket(PF_INET, SOCK_DGRAM, 0))) {
        perror("Cannot create socket");
        exit(1);
    }

    // set REUSEADDR
    int optval = 1;
    if (0 != setsockopt(sock, SOL_SOCKET, SO_REUSEADDR, &optval, sizeof(optval))) {
        perror("Cannot set socket to SO_REUSEADDR");
        exit(1);
    }

    // Bind it to the port (this requires priviledges)
    struct sockaddr_in addr;
    addr.sin_family        = AF_INET;
    addr.sin_port          = htons(PORT);
    addr.sin_addr.s_addr   = 0;
    if (0 != bind(sock, (struct sockaddr *)&addr, sizeof(addr))) {
        perror("Cannot bind socket to port");
        exit(1);
    }

    // Drop priviledges
    if (getuid() != geteuid()) {
        if (0 != seteuid(getuid())) {
            perror("Cannot drop priviledges");
            exit(1);
        }
    }

    // Make sure it is at the correct FD
    if (sock != FD) {
        dup2(sock, FD);
        close(sock);
    }

    // Execute the actual program that needs access to the
    // socket. We take the path from argv[0]
    char *last_slash = argv[0];
    char *scan = argv[0];
    while (*scan) {
        if ((*scan) == '/')
            last_slash = scan + 1;
        scan++;
    }
    char newpath[512];
    bzero(&newpath, 512);
    int len_to_copy = last_slash - argv[0];
    if (len_to_copy >= 512)
        exit(1);

    memcpy(newpath, argv[0], len_to_copy);
    strncpy(newpath + len_to_copy, PROGRAM, 511 - len_to_copy);
    execv(newpath, argv);
    perror("Cannot execute mkeventd");
}
