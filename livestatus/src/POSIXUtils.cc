// Copyright (C) 2019 tribe29 GmbH - License: Check_MK Enterprise License
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// According to POSIX, SEEK_SET & Co. are both in <stdio.h> *and* <unistd.h>.
// IWYU pragma: no_include <stdio.h>
#include "POSIXUtils.h"

#include <unistd.h>

#include <thread>

#include "Logger.h"

using namespace std::chrono_literals;

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
