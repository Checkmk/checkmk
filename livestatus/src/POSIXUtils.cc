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
std::optional<FileDescriptorPair> FileDescriptorPair::createSocketPair(
    Mode mode, Logger *logger) {
    std::array<int, 2> fd{-1, -1};
    // NOTE: Things are a bit tricky here: The close-on-exec flag is a file
    // descriptor flag, i.e. it is kept in the entries of the per-process table
    // of file descriptors. It is *not* part of the entries in the system-wide
    // table of open file descriptors, so it is *not* shared between different
    // file descriptors.
    //
    // Although it is necessary to avoid race conditions, specifying the
    // SOCK_CLOEXEC flag in the socketpair() call is not part of the POSIX spec,
    // but it is possible in Linux since kernel 2.6.27 and the various BSD
    // flavors. It sets the close-on-exec flag on *both* file descriptors, which
    // is fine: Before doing an execv(), we duplicate the wanted file
    // descriptors via dup2(), which clears the flag in the duplicate, see
    // Process::run().
    int sock_type = SOCK_STREAM | SOCK_CLOEXEC;
    if (::socketpair(AF_UNIX, sock_type, 0, &fd[0]) == -1) {
        generic_error ge{"cannot create socket pair"};
        Alert(logger) << ge;
        return {};
    }
    if (mode == Mode::nonblocking) {
        if (::fcntl(fd[0], F_SETFL, O_NONBLOCK) == -1) {
            generic_error ge{"cannot make socket non-blocking"};
            Alert(logger) << ge;
            ::close(fd[0]);
            ::close(fd[1]);
            return {};
        }
    }
    return FileDescriptorPair{fd[0], fd[1]};
}

// static
std::optional<FileDescriptorPair> FileDescriptorPair::createPipePair(
    FileDescriptorPair::Mode mode, Logger *logger) {
    std::array<int, 2> fd{-1, -1};
    // NOTE: See the comment in createSocketPair().
    int pipe_mode = O_CLOEXEC;
    if (::pipe2(&fd[0], pipe_mode) == -1) {
        generic_error ge{"cannot create pipe pair"};
        Alert(logger) << ge;
        return {};
    }
    if (mode == FileDescriptorPair::Mode::nonblocking) {
        if (::fcntl(fd[0], F_SETFL, O_NONBLOCK) == -1) {
            generic_error ge{"cannot make pipe non-blocking"};
            Alert(logger) << ge;
            ::close(fd[0]);
            ::close(fd[1]);
            return {};
        }
    }
    return FileDescriptorPair{fd[0], fd[1]};
}

namespace {
void closeFD(int &fd) {
    if (fd != -1) {
        ::close(fd);
    }
    fd = -1;
}
}  // namespace

void FileDescriptorPair::close() {
    closeFD(local_);
    closeFD(remote_);
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
