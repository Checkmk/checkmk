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

// IWYU pragma: no_include <bits/socket_type.h>
#include <errno.h>
#include <inttypes.h>
#include <pthread.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <sys/types.h>  // IWYU pragma: keep
#include <sys/un.h>
#include <unistd.h>

#ifndef AF_LOCAL
#define AF_LOCAL AF_UNIX
#endif
#ifndef PF_LOCAL
#define PF_LOCAL PF_UNIX
#endif

/* Ist normalerweise in sys/un.h, aber dietc hat dieses Makro nicht */
/* Evaluate to actual length of the `sockaddr_un' structure.  */
#ifndef SUN_LEN
#define SUN_LEN(ptr) \
    ((size_t)(((struct sockaddr_un *)0)->sun_path) + strlen((ptr)->sun_path))
#endif

int copy_data(int from, int to);
void *voidp;

struct thread_info {
    int from;
    int to;
    int should_shutdown;
    int terminate_on_read_eof;
};

ssize_t read_with_timeout(int from, char *buffer, int size, int us) {
    fd_set fds;
    FD_ZERO(&fds);
    FD_SET(from, &fds);
    struct timeval tv;
    tv.tv_sec = us / 1000000;
    tv.tv_usec = us % 1000000;
    int retval = select(from + 1, &fds, 0, 0, &tv);
    if (retval > 0) {
        return read(from, buffer, size);
    }
    return -2;
}

void *copy_thread(void *info) {
    signal(SIGWINCH, SIG_IGN);

    struct thread_info *ti = (struct thread_info *)info;
    int from = ti->from;
    int to = ti->to;

    char read_buffer[65536];
    while (1) {
        ssize_t r =
            read_with_timeout(from, read_buffer, sizeof(read_buffer), 1000000);
        if (r == -1) {
            fprintf(stderr, "Error reading from %d: %s\n", from,
                    strerror(errno));
            break;
        } else if (r == 0) {
            if (ti->should_shutdown) {
                shutdown(to, SHUT_WR);
            }
            if (ti->terminate_on_read_eof) {
                exit(0);
                return voidp;
            }
            break;
        } else if (r == -2) {
            r = 0;
        }

        const char *buffer = read_buffer;
        size_t bytes_to_write = r;
        while (bytes_to_write > 0) {
            ssize_t bytes_written = write(to, buffer, bytes_to_write);
            if (bytes_written == -1) {
                uintmax_t b = bytes_to_write;
                fprintf(stderr,
                        "Error: Cannot write %" PRIuMAX " bytes to %d: %s\n", b,
                        to, strerror(errno));
                break;
            }
            buffer += bytes_written;
            bytes_to_write -= bytes_written;
        }
    }
    return voidp;
}

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "Usage: %s UNIX-socket\n", argv[0]);
        exit(1);
    }

    signal(SIGWINCH, SIG_IGN);

    const char *unixpath = argv[1];
    struct stat st;

    if (0 != stat(unixpath, &st)) {
        fprintf(stderr, "No UNIX socket %s existing\n", unixpath);
        exit(2);
    }

    int sock = socket(PF_LOCAL, SOCK_STREAM, 0);
    if (sock < 0) {
        fprintf(stderr, "Cannot create client socket: %s\n", strerror(errno));
        exit(3);
    }

    /* Connect */
    struct sockaddr_un sockaddr;
    sockaddr.sun_family = AF_LOCAL;
    strncpy(sockaddr.sun_path, unixpath, sizeof(sockaddr.sun_path));
    if (connect(sock, (struct sockaddr *)&sockaddr, SUN_LEN(&sockaddr))) {
        fprintf(stderr, "Couldn't connect to UNIX-socket at %s: %s.\n",
                unixpath, strerror(errno));
        close(sock);
        exit(4);
    }

    struct thread_info toleft_info = {sock, 1, 0, 1};
    struct thread_info toright_info = {0, sock, 1, 0};
    pthread_t toright_thread, toleft_thread;
    if (pthread_create(&toright_thread, 0, copy_thread,
                       (void *)&toright_info) != 0 ||
        pthread_create(&toleft_thread, 0, copy_thread, (void *)&toleft_info) !=
            0) {
        fprintf(stderr, "Couldn't create threads: %s.\n", strerror(errno));
        close(sock);
        exit(5);
    }
    if (pthread_join(toleft_thread, NULL) != 0 ||
        pthread_join(toright_thread, NULL) != 0) {
        fprintf(stderr, "Couldn't join threads: %s.\n", strerror(errno));
        close(sock);
        exit(6);
    }

    close(sock);
    return 0;
}
