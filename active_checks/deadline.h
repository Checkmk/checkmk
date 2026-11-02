// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef deadline_h
#define deadline_h

#include <chrono>
#include <string>

namespace check_mkevents {

using Clock = std::chrono::steady_clock;

// One deadline for the whole exchange with the event console, so the timeouts
// of its steps don't add up.
struct Deadline {
    Clock::time_point start;
    std::chrono::seconds timeout;

    [[nodiscard]] Clock::time_point end() const { return start + timeout; }

    [[nodiscard]] bool has_passed() const { return Clock::now() >= end(); }

    // The reason we report when the deadline has passed.
    [[nodiscard]] std::string timeout_message() const {
        return "timeout after " + std::to_string(timeout.count()) +
               (timeout.count() == 1 ? " second" : " seconds");
    }
};

}  // namespace check_mkevents

#endif  // deadline_h
