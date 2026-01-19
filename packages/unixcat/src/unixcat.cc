// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <pthread.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <sys/un.h>
#include <unistd.h>

#include <chrono>
#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

#include "livestatus/Poller.h"

using namespace std::chrono_literals;

namespace {
constexpr size_t buffer_size = 65536;

struct thread_info {
    int from;
    int to;
    bool should_shutdown;
    bool terminate_on_read_eof;
};

void printErrno(const std::string &msg) { ::perror(msg.c_str()); }

ssize_t read_with_timeout(int from, std::vector<char> &buffer,
                          std::chrono::microseconds timeout) {
    Poller poller;
    poller.addFileDescriptor(from, PollEvents::in);
    // Do not handle FD errors.
    return poller.poll(timeout) > 0
               ? ::read(from, buffer.data(), buffer.capacity())
               : -2;
}

void *copy_thread(void *info) {
    (void)signal(SIGWINCH, SIG_IGN);
    const auto *tinfo = static_cast<thread_info *>(info);
    std::vector<char> read_buffer(buffer_size);
    while (true) {
        auto bytes_read = read_with_timeout(tinfo->from, read_buffer, 1s);
        if (bytes_read == -1) {
            printErrno("could not read from " + std::to_string(tinfo->from));
            break;
        }
        if (bytes_read == 0) {
            if (tinfo->should_shutdown) {
                ::shutdown(tinfo->to, SHUT_WR);
            }
            if (tinfo->terminate_on_read_eof) {
                // NOLINTNEXTLINE(concurrency-mt-unsafe)
                ::exit(0);
            }
            break;
        }
        if (bytes_read == -2) {
            bytes_read = 0;
        }

        const char *buffer = read_buffer.data();
        size_t bytes_to_write = bytes_read;
        while (bytes_to_write > 0) {
            const ssize_t bytes_written =
                ::write(tinfo->to, buffer, bytes_to_write);
            if (bytes_written == -1) {
                printErrno("cannot write " + std::to_string(bytes_to_write) +
                           " bytes to " + std::to_string(tinfo->to));
                break;
            }
            // NOLINTNEXTLINE(cppcoreguidelines-pro-bounds-pointer-arithmetic)
            buffer += bytes_written;
            bytes_to_write -= bytes_written;
        }
    }
    return nullptr;
}
}  // namespace

// NOLINTNEXTLINE(bugprone-exception-escape)
int main(int argc, char *argv[]) {
    // NOLINTNEXTLINE(cppcoreguidelines-pro-bounds-pointer-arithmetic)
    std::vector<std::string> arguments{argv, argv + argc};
    if (argc != 2) {
        std::cerr << "Usage: " << arguments[0] << " UNIX-socket\n";
        return 1;
    }

    (void)signal(SIGWINCH, SIG_IGN);
    const int sock = ::socket(PF_UNIX, SOCK_STREAM, 0);
    if (sock < 0) {
        printErrno("cannot create client socket");
        return 1;
    }

    struct sockaddr_un sockaddr{.sun_family = AF_UNIX, .sun_path = ""};
    const auto &unixpath = arguments[1];
    unixpath.copy(&sockaddr.sun_path[0], sizeof(sockaddr.sun_path) - 1);
    sockaddr.sun_path[sizeof(sockaddr.sun_path) - 1] = '\0';
    // NOLINTNEXTLINE(cppcoreguidelines-pro-type-reinterpret-cast)
    if (::connect(sock, reinterpret_cast<struct sockaddr *>(&sockaddr),
                  sizeof(sockaddr)) != 0) {
        printErrno("cannot connect to UNIX-socket at '" + unixpath + "'");
        return 1;
    }

    thread_info toleft_info = {.from = sock,
                               .to = 1,
                               .should_shutdown = false,
                               .terminate_on_read_eof = true};
    thread_info toright_info = {.from = 0,
                                .to = sock,
                                .should_shutdown = true,
                                .terminate_on_read_eof = false};
    ::pthread_t toright_thread{};
    ::pthread_t toleft_thread{};
    if (::pthread_create(&toright_thread, nullptr, copy_thread,
                         &toright_info) != 0 ||
        ::pthread_create(&toleft_thread, nullptr, copy_thread, &toleft_info) !=
            0) {
        printErrno("cannot create threads");
        return 1;
    }
    if (::pthread_join(toleft_thread, nullptr) != 0 ||
        ::pthread_join(toright_thread, nullptr) != 0) {
        printErrno("cannot join threads");
        return 1;
    }

    return 0;
}
