// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// Livestatus parses every line of the monitoring history into a LogEntry, so
// parsing must not allocate beyond the line it gets. This test binary counts
// allocations by replacing the global operator new, which is why it is a
// binary of its own.

#include <cstddef>
#include <cstdlib>
#include <new>
#include <string>
#include <utility>

#include "gtest/gtest.h"
#include "livestatus/LogEntry.h"

namespace {
// The number of allocations of the calling thread so far.
size_t &allocations() {
    thread_local size_t count{0};
    return count;
}
}  // namespace

void *operator new(std::size_t size) {
    ++allocations();
    // NOLINTNEXTLINE(cppcoreguidelines-no-malloc,cppcoreguidelines-owning-memory)
    if (void *ptr = std::malloc(size)) {
        return ptr;
    }
    throw std::bad_alloc{};
}

void operator delete(void *ptr) noexcept {
    // NOLINTNEXTLINE(cppcoreguidelines-no-malloc,cppcoreguidelines-owning-memory)
    std::free(ptr);
}

void operator delete(void *ptr, std::size_t /*size*/) noexcept {
    // NOLINTNEXTLINE(cppcoreguidelines-no-malloc,cppcoreguidelines-owning-memory)
    std::free(ptr);
}

namespace {
class LogEntryAllocations : public ::testing::TestWithParam<std::string> {};
}  // namespace

TEST_P(LogEntryAllocations, ParsingALineAllocatesNothing) {
    auto line = "[1551424305] " + GetParam();

    allocations() = 0;
    const LogEntry entry{42, std::move(line)};
    const auto count = allocations();

    EXPECT_EQ(size_t{0}, count);
}

INSTANTIATE_TEST_SUITE_P(
    LogEntry, LogEntryAllocations,
    ::testing::Values(
        "SERVICE ALERT: web01;CPU load;CRITICAL;HARD;3;load too high",
        "SERVICE NOTIFICATION: alice;web01;CPU load;CRITICAL;mail;too high",
        "EXTERNAL COMMAND: ADD_SVC_COMMENT;web01;CPU load;0;alice;secret",
        "Warning: Unrecognized external command -> MODIFY_HOST_DOWNTIME;42",
        "LOG VERSION: 2.0", "logging initial states", "logging intitial states",
        "Check_MK Micro Core 2.5.0 starting...",
        "Check_MK Micro Core shutting down...",
        "Auto-save of retention data completed successfully."));
