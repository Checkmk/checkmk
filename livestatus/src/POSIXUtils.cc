// Copyright (C) 2019 tribe29 GmbH - License: Check_MK Enterprise License
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// According to POSIX, SEEK_SET & Co. are both in <stdio.h> *and* <unistd.h>.
// IWYU pragma: no_include <stdio.h>
#include "POSIXUtils.h"

#include <fcntl.h>
#include <sys/socket.h>
#include <unistd.h>

#include <array>
#include <thread>

#include "Logger.h"

using namespace std::chrono_literals;

// static
FileDescriptorPair FileDescriptorPair::createSocketPair(Mode mode,
                                                        Logger *logger) {
    std::array<int, 2> fd{-1, -1};
    int sock_type = SOCK_STREAM | SOCK_CLOEXEC;
    if (::socketpair(AF_UNIX, sock_type, 0, &fd[0]) == -1) {
        // socketpair(2) does not modify fd on failure.
        generic_error ge{"cannot create socket pair"};
        Alert(logger) << ge;
        return {-1, -1};
    }
    // yes, we establish half-blocking channel
    if (mode == Mode::nonblocking) {
        if (fcntl(fd[0], F_SETFL, O_NONBLOCK) == -1) {
            generic_error ge{"cannot make socket non-blocking"};
            Alert(logger) << ge;
            ::close(fd[0]);
            ::close(fd[1]);
            return {-1, -1};
        }
    }
    return {fd[0], fd[1]};
}

// static
FileDescriptorPair FileDescriptorPair::makeSocketPair(
    FileDescriptorPair::Mode mode, Logger *logger) {
    std::array<int, 2> fd{-1, -1};
    // TODO(ml): Set cloexec and nonblock in `type` param.
    if (socketpair(AF_UNIX, SOCK_STREAM, 0, &fd[0]) == -1) {
        // socketpair(2) does not modify fd on failure.
        generic_error ge{"cannot create socket pair"};
        Alert(logger) << ge;
        return {-1, -1};
    }

    // Make sure our socket is not forked.
    if (fcntl(fd[0], F_SETFD, FD_CLOEXEC) == -1) {
        generic_error ge{"cannot close-on-exec bit on socket"};
        Alert(logger) << ge;
        ::close(fd[0]);
        ::close(fd[1]);
        return {-1, -1};
    }

    if (mode == FileDescriptorPair::Mode::nonblocking) {
        if (fcntl(fd[0], F_SETFL, O_NONBLOCK) == -1) {
            generic_error ge{"cannot make socket non-blocking"};
            Alert(logger) << ge;
            ::close(fd[0]);
            ::close(fd[1]);
            return {-1, -1};
        }
    }

    return {fd[0], fd[1]};
}

// static
FileDescriptorPair FileDescriptorPair::createPipePair(Mode mode,
                                                      Logger *logger) {
    std::array<int, 2> fd{-1, -1};
    int pipe_mode = O_CLOEXEC;
    if (mode == Mode::nonblocking) {
        pipe_mode |= O_NONBLOCK;
    }
    if (::pipe2(&fd[0], pipe_mode) == -1) {
        generic_error ge{"cannot create pipe pair"};
        Alert(logger) << ge;
        return {-1, -1};
    }
    return {fd[0], fd[1]};
}

// static
FileDescriptorPair FileDescriptorPair::makePipePair(
    FileDescriptorPair::Mode mode, Logger *logger) {
    std::array<int, 2> fd{-1, -1};
    // TODO(ml): Set cloexec and nonblock in `flag` param to `pipe2`.
    if (pipe(&fd[0]) == -1) {
        // pipe2(2) does not modify fd on failure.
        generic_error ge{"cannot create pipe pair"};
        Alert(logger) << ge;
        return {-1, -1};
    }

    // Make sure our socket is not forked.
    if (fcntl(fd[0], F_SETFD, FD_CLOEXEC) == -1) {
        generic_error ge{"cannot close-on-exec bit on pipe"};
        Alert(logger) << ge;
        ::close(fd[0]);
        ::close(fd[1]);
        return {-1, -1};
    }

    if (mode == FileDescriptorPair::Mode::nonblocking) {
        if (fcntl(fd[0], F_SETFL, O_NONBLOCK) == -1) {
            generic_error ge{"cannot make pipe non-blocking"};
            Alert(logger) << ge;
            ::close(fd[0]);
            ::close(fd[1]);
            return {-1, -1};
        }
    }

    return {fd[0], fd[1]};
}

namespace {
thread_local std::string thread_name;
}  // namespace

void setThreadName(std::string name) { thread_name = move(name); }
std::string getThreadName() { return thread_name; }

file_lock::file_lock(const char *name) : fd_(::open(name, O_RDWR)) {
    if (fd_ == -1) {
        throw generic_error("could not open lock file");
    }
}

file_lock::~file_lock() {
    if (fd_ != -1) {
        ::close(fd_);
        fd_ = -1;
    }
}

bool file_lock::fcntl_impl(short l_type, int cmd, const char *msg,
                           bool accecpt_timeout) const {
    struct ::flock fl {
        .l_type = l_type, .l_whence = SEEK_SET, .l_start = 0, .l_len = 0,
        .l_pid = 0,
    };
    if (::fcntl(fd_, cmd, &fl) != -1) {
        return true;
    }
    if (accecpt_timeout && (errno == EAGAIN || errno == EACCES)) {
        return false;
    }
    throw generic_error(msg);
}

using steady_clock = std::chrono::steady_clock;

bool file_lock::try_lock_until_impl(const steady_clock::time_point &time,
                                    short l_type, const char *msg) {
    if (time == steady_clock::time_point::max()) {
        fcntl_impl(l_type, F_SETLKW, msg);
        return true;
    }
    do {
        if (fcntl_impl(l_type, F_SETLK, msg, true)) {
            return true;
        }
        if (steady_clock::now() >= time) {
            return false;
        }
        std::this_thread::sleep_for(10ms);
    } while (true);
}
