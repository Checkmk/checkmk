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
#include <ratio>
#include <thread>

#include "Logger.h"
#include "Poller.h"

using namespace std::chrono_literals;

namespace {
std::optional<SocketPair> fail(const std::string &message, Logger *logger,
                               SocketPair &sp) {
    generic_error ge{message};
    Alert(logger) << ge;
    sp.close();
    return {};
}

void closeFD(int &fd) {
    if (fd != -1) {
        ::close(fd);
    }
    fd = -1;
}
}  // namespace

// static
std::optional<SocketPair> SocketPair::make(Mode mode, Direction direction,
                                           Logger *logger) {
    // NOTE: Things are a bit tricky here: The close-on-exec flag is a file
    // descriptor flag, i.e. it is kept in the entries of the per-process table
    // of file descriptors. It is *not* part of the entries in the system-wide
    // table of open files, so it is *not* shared between different file
    // descriptors.
    //
    // Although it is necessary to avoid race conditions, specifying the
    // SOCK_CLOEXEC flag in the socketpair() call is not part of the POSIX spec,
    // but it is possible in Linux since kernel 2.6.27 and the various BSD
    // flavors. It sets the close-on-exec flag on *both* file descriptors, which
    // is fine: Before doing an execv(), we duplicate the wanted file
    // descriptors via dup2(), which clears the flag in the duplicate, see
    // Process::run().
    SocketPair sp{-1, -1};
    if (::socketpair(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC, 0, sp.fd_.data()) ==
        -1) {
        return fail("cannot create socket pair", logger, sp);
    }
    // NOTE: Again, things are a bit tricky: The non-blocking flag is kept in
    // the entries of the system-wide table of open files, so it is *shared*
    // between different file descriptors pointing to the same open file.
    // Nevertheless, socketpair() returns two file descriptors pointing to two
    // *different* open files. Therefore, changing the non-blocking flag via a
    // fcntl() on one of these file descriptors does *not* affect the
    // non-blocking flag of the other one.
    //
    // The subprocesses we create always expect a standard blocking file, so we
    // cannot use SOCK_NONBLOCK in the socketpair() call above: This would make
    // *both* files non-blocking. We only want our own, local file to be
    // non-blocking, so we have to use the separate fcntl() below.
    switch (mode) {
        case Mode::blocking:
            break;
        case Mode::local_non_blocking:
            if (::fcntl(sp.local(), F_SETFL, O_NONBLOCK) == -1) {
                return fail("cannot make socket non-blocking", logger, sp);
            }
            break;
    }
    switch (direction) {
        case Direction::bidirectional:
            break;
        case Direction::remote_to_local:
            if (::shutdown(sp.local(), SHUT_WR) == -1) {
                return fail("cannot make socket one-directional", logger, sp);
            }
            break;
    }
    return sp;
}

void SocketPair::close() {
    closeFD(fd_[0]);
    closeFD(fd_[1]);
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

ssize_t writeWithTimeout(int fd, std::string_view buffer,
                         std::chrono::nanoseconds timeout) {
    auto size = buffer.size();
    while (!buffer.empty()) {
        auto ret = ::write(fd, buffer.data(), buffer.size());
        if (ret == -1 && errno == EWOULDBLOCK) {
            ret = Poller{}.wait(timeout, fd, PollEvents::out)
                      ? ::write(fd, buffer.data(), buffer.size())
                      : -1;
        }
        if (ret != -1) {
            buffer = std::string_view{buffer.data() + ret, buffer.size() - ret};
        } else if (errno != EINTR) {
            return -1;
        }
    }
    return size;
}
