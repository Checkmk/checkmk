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
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include <pthread.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <unistd.h>
#include <cerrno>
#include <chrono>
#include <csignal>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <ratio>
#include <string>
#include "Poller.h"

int copy_data(int from, int to);
void *voidp;

struct thread_info {
    int from;
    int to;
    int should_shutdown;
    int terminate_on_read_eof;
};

void printErrno(const std::string &msg) {
    std::cerr << msg + ": " + strerror(errno) << std::endl;
}

ssize_t read_with_timeout(int from, char *buffer, int size,
                          std::chrono::microseconds timeout) {
    Poller poller;
    poller.addFileDescriptor(from, PollEvents::in);
    return poller.poll(timeout) > 0 ? read(from, buffer, size) : -2;
}

void *copy_thread(void *info) {
    // https://llvm.org/bugs/show_bug.cgi?id=29089
    signal(SIGWINCH, SIG_IGN);  // NOLINT

    auto *ti = static_cast<thread_info *>(info);
    int from = ti->from;
    int to = ti->to;

    char read_buffer[65536];
    while (true) {
        ssize_t r = read_with_timeout(from, read_buffer, sizeof(read_buffer),
                                      std::chrono::microseconds(1000000));
        if (r == -1) {
            printErrno("Error reading from " + std::to_string(from));
            break;
        }
        if (r == 0) {
            if (ti->should_shutdown != 0) {
                shutdown(to, SHUT_WR);
            }
            if (ti->terminate_on_read_eof != 0) {
                exit(0);
                return voidp;
            }
            break;
        }
        if (r == -2) {
            r = 0;
        }

        const char *buffer = read_buffer;
        size_t bytes_to_write = r;
        while (bytes_to_write > 0) {
            ssize_t bytes_written = write(to, buffer, bytes_to_write);
            if (bytes_written == -1) {
                printErrno("Error: Cannot write " +
                           std::to_string(bytes_to_write) + " bytes to " +
                           std::to_string(to));
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
        std::cerr << "Usage: " << argv[0] << " UNIX-socket" << std::endl;
        exit(1);
    }

    // https://llvm.org/bugs/show_bug.cgi?id=29089
    signal(SIGWINCH, SIG_IGN);  // NOLINT

    std::string unixpath = argv[1];
    struct stat st;

    if (0 != stat(unixpath.c_str(), &st)) {
        std::cerr << "No UNIX socket " << unixpath << " existing" << std::endl;
        exit(2);
    }

    int sock = socket(PF_UNIX, SOCK_STREAM, 0);
    if (sock < 0) {
        printErrno("Cannot create client socket");
        exit(3);
    }

    /* Connect */
    struct sockaddr_un sockaddr;
    sockaddr.sun_family = AF_UNIX;
    strncpy(sockaddr.sun_path, unixpath.c_str(), sizeof(sockaddr.sun_path) - 1);
    sockaddr.sun_path[sizeof(sockaddr.sun_path) - 1] = '\0';
    if (connect(sock, reinterpret_cast<struct sockaddr *>(&sockaddr),
                sizeof(sockaddr)) != 0) {
        printErrno("Couldn't connect to UNIX-socket at " + unixpath);
        close(sock);
        exit(4);
    }

    thread_info toleft_info = {sock, 1, 0, 1};
    thread_info toright_info = {0, sock, 1, 0};
    pthread_t toright_thread;
    pthread_t toleft_thread;
    if (pthread_create(&toright_thread, nullptr, copy_thread, &toright_info) !=
            0 ||
        pthread_create(&toleft_thread, nullptr, copy_thread, &toleft_info) !=
            0) {
        printErrno("Couldn't create threads");
        close(sock);
        exit(5);
    }
    if (pthread_join(toleft_thread, nullptr) != 0 ||
        pthread_join(toright_thread, nullptr) != 0) {
        printErrno("Couldn't join threads");
        close(sock);
        exit(6);
    }

    close(sock);
    return 0;
}
