// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// According to POSIX, SEEK_SET & Co. are both in <stdio.h> *and* <unistd.h>.
// IWYU pragma: no_include <stdio.h>

// We need pthread_setname_np() from <pthread.h>.
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif

#include "livestatus/POSIXUtils.h"

#include <pthread.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <unistd.h>

#include <compare>
#include <thread>

#include "livestatus/Logger.h"
#include "livestatus/Poller.h"

using namespace std::chrono_literals;

namespace {
std::optional<SocketPair> fail(const std::string &message, Logger *logger,
                               SocketPair &sp) {
    const generic_error ge{message};
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

int createUnixDomainSocket(const std::filesystem::path &path, Logger *logger,
                           int socket_backlog) {
    int result = -1;
    struct stat st{};

    if (0 == stat(path.c_str(), &st)) {
        if (0 == ::unlink(path.c_str())) {
            Notice(logger) << "removed stale socket file " << path;
        } else {
            const generic_error ge("cannot remove stale socket file " +
                                   path.string());
            Alert(logger) << ge;
            return -1;
        }
    }

    result = ::socket(PF_UNIX, SOCK_STREAM, 0);
    if (result < 0) {
        const generic_error ge("cannot create UNIX socket");
        Alert(logger) << ge;
        return -1;
    }

    // Imortant: close on exec -> forked processes must not inherit it!
    // NOLINTNEXTLINE(cppcoreguidelines-pro-type-vararg)
    if (::fcntl(result, F_SETFD, FD_CLOEXEC) == -1) {
        const generic_error ge("cannot set close-exec bit on socket");
        Alert(logger) << ge;
        ::close(result);
        return -1;
    }

    // Bind it to its address. This creates the socket file.
    sockaddr_un sockaddr{.sun_family = AF_UNIX, .sun_path = ""};
    std::string_view{path.c_str()}.copy(&sockaddr.sun_path[0],
                                        sizeof(sockaddr.sun_path) - 1);
    sockaddr.sun_path[sizeof(sockaddr.sun_path) - 1] = '\0';
    // NOLINTNEXTLINE(cppcoreguidelines-pro-type-reinterpret-cast)
    if (::bind(result, reinterpret_cast<struct sockaddr *>(&sockaddr),
               sizeof(sockaddr)) < 0) {
        const generic_error ge("cannot bind UNIX socket to address " +
                               path.string());
        Alert(logger) << ge;
        ::close(result);
        return -1;
    }

    if (0 != ::chmod(path.c_str(), S_IRUSR | S_IWUSR | S_IRGRP | S_IWGRP)) {
        const generic_error ge("cannot chown UNIX socket at " + path.string() +
                               " to 0660");
        Error(logger) << ge;
        ::close(result);
        return -1;
    }

    if (0 != ::listen(result, socket_backlog)) {
        const generic_error ge("cannot listen to unix socket at " +
                               path.string());
        Alert(logger) << ge;
        ::close(result);
        return -1;
    }

    Notice(logger) << "listening on " << path.string();
    return result;
}

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
            // NOLINTNEXTLINE(cppcoreguidelines-pro-type-vararg)
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
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
thread_local std::string thread_name;
}  // namespace

void setThreadName(std::string name) {
    // Setting the thread name is a portability nightmare, even among POSIX
    // systems, see e.g. https://stackoverflow.com/a/7989973.
    //
    // #include <pthread.h>  // or maybe <pthread_np.h> for some OSes
    //
    // Linux (remember to set _GNU_SOURCE, restricted to 16 chars)
    // int pthread_setname_np(pthread_t thread, const char *name);
    //
    // NetBSD: name + arg work like printf(name, arg)
    // int pthread_setname_np(pthread_t thread, const char *name, void *arg);
    //
    // FreeBSD & OpenBSD: function name is slightly different, no return value
    // void pthread_set_name_np(pthread_t tid, const char *name);
    //
    // Mac OS X: must be set from within the thread (can't specify thread ID)
    // int pthread_setname_np(const char *);
    //
    // HACK: We have yet another complication on Linux: Both
    // pthread_setname_np(...) and prctl(PR_SET_NAME, ...) seem to reuse the
    // kernel field for the "filename of the executable", i.e. the "Name" field
    // in /proc/<pid>/status resp. the "tcomm" field in /proc/<pid>/stat. This
    // confuses ps and pstree, so we don't set this for the main thread. :-/
    if (name != "main") {
        pthread_setname_np(pthread_self(), name.substr(0, 15).c_str());
    }

    // ... and here invisible to ps/pstree/..., but in its full glory:
    thread_name = std::move(name);
}

std::string getThreadName() { return thread_name; }

file_lock::file_lock(const std::filesystem::path &name)
    // NOLINTNEXTLINE(cppcoreguidelines-pro-type-vararg)
    : fd_{::open(name.c_str(), O_RDWR)} {
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
    struct ::flock fl{
        .l_type = l_type,
        .l_whence = SEEK_SET,
        .l_start = 0,
        .l_len = 0,
        .l_pid = 0,
    };
    // NOLINTNEXTLINE(cppcoreguidelines-pro-type-vararg)
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
    while (true) {
        if (fcntl_impl(l_type, F_SETLK, msg, true)) {
            return true;
        }
        if (steady_clock::now() >= time) {
            return false;
        }
        std::this_thread::sleep_for(10ms);
    }
}

ssize_t writeWithTimeoutWhile(int fd, std::string_view buffer,
                              std::chrono::nanoseconds timeout,
                              const std::function<bool()> &pred) {
    auto size = buffer.size();
    while (!buffer.empty() && pred()) {
        auto ret = ::write(fd, buffer.data(), buffer.size());
        if (ret == -1 && errno == EWOULDBLOCK) {
            ret = Poller{}.wait(timeout, fd, PollEvents::out)
                      ? ::write(fd, buffer.data(), buffer.size())
                      : -1;
        }
        if (ret != -1) {
            // NOLINTNEXTLINE(cppcoreguidelines-pro-bounds-pointer-arithmetic)
            buffer = std::string_view{buffer.data() + ret, buffer.size() - ret};
        } else if (errno != EINTR) {
            return -1;
        }
    }
    // NOLINTNEXTLINE(bugprone-narrowing-conversions,cppcoreguidelines-narrowing-conversions)
    return size;
}

ssize_t writeWithTimeout(int fd, std::string_view buffer,
                         std::chrono::nanoseconds timeout) {
    return writeWithTimeoutWhile(fd, buffer, timeout, []() { return true; });
}
