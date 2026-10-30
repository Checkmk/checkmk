// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <netdb.h>
#include <sys/socket.h>

#include <cerrno>
#include <chrono>
#include <initializer_list>
#include <stdexcept>
#include <string>
#include <tuple>
#include <variant>
#include <vector>

#include "active_checks/connection_schedule.h"
#include "active_checks/deadline.h"
#include "gtest/gtest.h"

using namespace std::chrono_literals;
using check_mkevents::Action;
using check_mkevents::Clock;
using check_mkevents::ConnectionSchedule;
using check_mkevents::Deadline;
using check_mkevents::GiveUp;
using check_mkevents::numeric_host;
using check_mkevents::StartAttempt;
using check_mkevents::Wait;

namespace {

// An arbitrary start, the times of the tests count from it.
const Clock::time_point t0{std::chrono::hours{1}};

const Deadline deadline{.start = t0, .timeout = std::chrono::seconds{20}};

ConnectionSchedule make_schedule() { return {"ec.example", 6558, deadline}; }

// The numeric addresses as one list, like from getaddrinfo(). freeaddrinfo()
// frees it, as it frees each element on its own.
addrinfo *found(std::initializer_list<const char *> numeric_addresses) {
    addrinfo *head = nullptr;
    addrinfo **tail = &head;
    for (const auto *numeric_address : numeric_addresses) {
        addrinfo hints{};
        hints.ai_flags = AI_NUMERICHOST | AI_NUMERICSERV;
        hints.ai_socktype = SOCK_STREAM;
        if (getaddrinfo(numeric_address, "6558", &hints, tail) != 0) {
            throw std::invalid_argument{numeric_address};
        }
        while (*tail != nullptr) {
            tail = &(*tail)->ai_next;
        }
    }
    return head;
}

// The action as text: "start ADDRESS", "wait until N ms" or "give up: REASON".
std::string describe(const Action &action) {
    if (const auto *start = std::get_if<StartAttempt>(&action)) {
        return "start " + numeric_host(*start->address);
    }
    if (const auto *wait = std::get_if<Wait>(&action)) {
        return "wait until " +
               std::to_string(
                   std::chrono::duration_cast<std::chrono::milliseconds>(
                       wait->until - t0)
                       .count()) +
               " ms";
    }
    return "give up: " + std::get<GiveUp>(action).reason;
}

// The address of the attempt the schedule starts at the time.
const addrinfo &next_address(ConnectionSchedule &schedule,
                             Clock::time_point now) {
    return *std::get<StartAttempt>(schedule.next_action(now)).address;
}

}  // namespace

TEST(ConnectionSchedule, IPv6AnswerStartsAnAttemptAtOnce) {
    auto schedule = make_schedule();
    schedule.lookup_answered(t0, AF_INET6, 0, 0, found({"2001:db8::1"}));

    const auto action = schedule.next_action(t0);

    EXPECT_EQ(describe(action), "start [2001:db8::1]");
}

TEST(ConnectionSchedule, IPv4AnswerWaitsForTheIPv6OneOnlyBriefly) {
    auto schedule = make_schedule();
    schedule.lookup_answered(t0, AF_INET, 0, 0, found({"192.0.2.1"}));

    const auto waiting = describe(schedule.next_action(t0));
    const auto after_waiting = describe(schedule.next_action(t0 + 50ms));

    EXPECT_EQ(waiting, "wait until 50 ms");
    EXPECT_EQ(after_waiting, "start 192.0.2.1");
}

TEST(ConnectionSchedule, IPv6AnswerShortlyAfterTheIPv4OneGetsTheFirstTurn) {
    auto schedule = make_schedule();
    schedule.lookup_answered(t0, AF_INET, 0, 0, found({"192.0.2.1"}));
    schedule.lookup_answered(t0 + 10ms, AF_INET6, 0, 0, found({"2001:db8::1"}));

    const auto action = schedule.next_action(t0 + 10ms);

    EXPECT_EQ(describe(action), "start [2001:db8::1]");
}

TEST(ConnectionSchedule, FailedIPv6LookupEndsTheWaitOfTheIPv4Answer) {
    auto schedule = make_schedule();
    schedule.lookup_answered(t0, AF_INET, 0, 0, found({"192.0.2.1"}));
    schedule.lookup_answered(t0 + 10ms, AF_INET6, EAI_NODATA, 0, nullptr);

    const auto action = schedule.next_action(t0 + 10ms);

    EXPECT_EQ(describe(action), "start 192.0.2.1");
}

TEST(ConnectionSchedule, NextAddressGetsItsTurnAfterTheAttemptDelay) {
    auto schedule = make_schedule();
    schedule.lookup_answered(t0, AF_INET6, 0, 0,
                             found({"2001:db8::1", "2001:db8::2"}));
    schedule.attempt_going_on(t0, next_address(schedule, t0));

    const auto waiting = describe(schedule.next_action(t0));
    const auto after_waiting = describe(schedule.next_action(t0 + 250ms));

    EXPECT_EQ(waiting, "wait until 250 ms");
    EXPECT_EQ(after_waiting, "start [2001:db8::2]");
}

TEST(ConnectionSchedule, PendingIPv6LookupDoesntShortenTheAttemptDelay) {
    auto schedule = make_schedule();
    schedule.lookup_answered(t0, AF_INET, 0, 0,
                             found({"192.0.2.1", "192.0.2.2"}));
    schedule.attempt_going_on(t0 + 50ms, next_address(schedule, t0 + 50ms));

    const auto waiting = describe(schedule.next_action(t0 + 50ms));
    const auto after_waiting = describe(schedule.next_action(t0 + 300ms));

    EXPECT_EQ(waiting, "wait until 300 ms");
    EXPECT_EQ(after_waiting, "start 192.0.2.2");
}

TEST(ConnectionSchedule, FailedAttemptGivesTheNextAddressItsTurnAtOnce) {
    auto schedule = make_schedule();
    schedule.lookup_answered(t0, AF_INET6, 0, 0,
                             found({"2001:db8::1", "2001:db8::2"}));
    const auto &first = next_address(schedule, t0);
    schedule.attempt_going_on(t0, first);
    schedule.attempt_failed(t0 + 10ms, first, ECONNREFUSED, true);

    const auto action = schedule.next_action(t0 + 10ms);

    EXPECT_EQ(describe(action), "start [2001:db8::2]");
}

TEST(ConnectionSchedule, FailedOlderAttemptKeepsTheDelayOfAYoungerOne) {
    auto schedule = make_schedule();
    schedule.lookup_answered(
        t0, AF_INET6, 0, 0,
        found({"2001:db8::1", "2001:db8::2", "2001:db8::3"}));
    const auto &older = next_address(schedule, t0);
    schedule.attempt_going_on(t0, older);
    schedule.attempt_going_on(t0 + 250ms, next_address(schedule, t0 + 250ms));
    schedule.attempt_failed(t0 + 260ms, older, EHOSTUNREACH, true);

    const auto action = schedule.next_action(t0 + 260ms);

    EXPECT_EQ(describe(action), "wait until 500 ms");
}

TEST(ConnectionSchedule, FailedYoungestAttemptGivesTheNextOneItsTurnAtOnce) {
    auto schedule = make_schedule();
    schedule.lookup_answered(
        t0, AF_INET6, 0, 0,
        found({"2001:db8::1", "2001:db8::2", "2001:db8::3"}));
    schedule.attempt_going_on(t0, next_address(schedule, t0));
    const auto &youngest = next_address(schedule, t0 + 250ms);
    schedule.attempt_going_on(t0 + 250ms, youngest);
    schedule.attempt_failed(t0 + 260ms, youngest, ECONNREFUSED, true);

    const auto action = schedule.next_action(t0 + 260ms);

    EXPECT_EQ(describe(action), "start [2001:db8::3]");
}

TEST(ConnectionSchedule, AddressWithoutASocketGivesTheNextOneItsTurnAtOnce) {
    auto schedule = make_schedule();
    schedule.lookup_answered(t0, AF_INET6, 0, 0,
                             found({"2001:db8::1", "2001:db8::2"}));
    schedule.attempt_failed(t0, next_address(schedule, t0), EAFNOSUPPORT,
                            false);

    const auto action = schedule.next_action(t0);

    EXPECT_EQ(describe(action), "start [2001:db8::2]");
}

TEST(ConnectionSchedule, AddressFamiliesTakeTurns) {
    auto schedule = make_schedule();
    schedule.lookup_answered(t0, AF_INET6, 0, 0,
                             found({"2001:db8::1", "2001:db8::2"}));
    schedule.lookup_answered(t0, AF_INET, 0, 0, found({"192.0.2.1"}));

    std::vector<std::string> order;
    for (int i = 0; i < 3; i++) {
        const auto &address = next_address(schedule, t0);
        order.push_back(numeric_host(address));
        schedule.attempt_failed(t0, address, ECONNREFUSED, true);
    }

    EXPECT_EQ(order, (std::vector<std::string>{"[2001:db8::1]", "192.0.2.1",
                                               "[2001:db8::2]"}));
}

TEST(ConnectionSchedule, LateAnswerWaitsForTheTurnOfItsAddresses) {
    auto schedule = make_schedule();
    schedule.lookup_answered(t0, AF_INET, 0, 0, found({"192.0.2.1"}));
    schedule.attempt_going_on(t0 + 50ms, next_address(schedule, t0 + 50ms));
    schedule.lookup_answered(t0 + 60ms, AF_INET6, 0, 0, found({"2001:db8::1"}));

    const auto waiting = describe(schedule.next_action(t0 + 60ms));
    const auto after_waiting = describe(schedule.next_action(t0 + 300ms));

    EXPECT_EQ(waiting, "wait until 300 ms");
    EXPECT_EQ(after_waiting, "start [2001:db8::1]");
}

TEST(ConnectionSchedule, LookupsAreAwaitedUntilTheDeadline) {
    auto schedule = make_schedule();

    const auto action = schedule.next_action(t0);

    EXPECT_EQ(describe(action), "wait until 20000 ms");
}

TEST(ConnectionSchedule, TurnOfTheNextAddressIsAwaitedUntilTheDeadlineOnly) {
    auto schedule = make_schedule();
    schedule.lookup_answered(t0, AF_INET6, 0, 0,
                             found({"2001:db8::1", "2001:db8::2"}));
    schedule.attempt_going_on(t0 + 19900ms,
                              next_address(schedule, t0 + 19900ms));

    const auto action = schedule.next_action(t0 + 19900ms);

    EXPECT_EQ(describe(action), "wait until 20000 ms");
}

TEST(ConnectionSchedule, AddressFoundTooLateForATurnIsReportedAsTimedOut) {
    auto schedule = make_schedule();
    schedule.lookup_answered(t0, AF_INET, 0, 0, found({"192.0.2.1"}));
    schedule.lookup_answered(t0 + 20s, AF_INET6, 0, 0, found({"2001:db8::1"}));

    const auto action = schedule.next_action(t0 + 20s);

    EXPECT_EQ(describe(action),
              "give up: Cannot connect to event console at [2001:db8::1]:6558 "
              "(timeout after 20 seconds)");
}

// Like for a firewall dropping both, so it's clear that IPv4 was tried, too
TEST(ConnectionSchedule, TimeoutIsReportedForTheOldestAttemptOfEachFamily) {
    auto schedule = make_schedule();
    schedule.lookup_answered(t0, AF_INET6, 0, 0,
                             found({"2001:db8::1", "2001:db8::2"}));
    schedule.lookup_answered(t0, AF_INET, 0, 0,
                             found({"192.0.2.1", "192.0.2.2"}));
    for (const auto now : {t0, t0 + 250ms, t0 + 500ms, t0 + 750ms}) {
        schedule.attempt_going_on(now, next_address(schedule, now));
    }

    const auto action = schedule.next_action(t0 + 20s);

    EXPECT_EQ(describe(action),
              "give up: Cannot connect to event console at [2001:db8::1]:6558 "
              "(timeout after 20 seconds) or 192.0.2.1:6558 (timeout after 20 "
              "seconds)");
}

TEST(ConnectionSchedule, TimeoutIsReportedNextToARefusedConnection) {
    auto schedule = make_schedule();
    schedule.lookup_answered(t0, AF_INET6, EAI_NODATA, 0, nullptr);
    schedule.lookup_answered(t0, AF_INET, 0, 0,
                             found({"192.0.2.1", "192.0.2.2"}));
    schedule.attempt_failed(t0, next_address(schedule, t0), ECONNREFUSED, true);
    schedule.attempt_going_on(t0, next_address(schedule, t0));

    const auto action = schedule.next_action(t0 + 20s);

    EXPECT_EQ(describe(action),
              "give up: Cannot connect to event console at 192.0.2.1:6558 "
              "(Connection refused) or 192.0.2.2:6558 (timeout after 20 "
              "seconds)");
}

// No IPv6 in the kernel, IPv6 disabled via sysctl, or no route
class IPv6FailureSayingLittle
    : public testing::TestWithParam<std::tuple<int, bool>> {};

TEST_P(IPv6FailureSayingLittle, DoesntHideARefusedConnection) {
    const auto [err, got_socket] = GetParam();
    auto schedule = make_schedule();
    schedule.lookup_answered(t0, AF_INET, 0, 0, found({"192.0.2.1"}));
    schedule.attempt_failed(t0 + 50ms, next_address(schedule, t0 + 50ms),
                            ECONNREFUSED, true);
    schedule.lookup_answered(t0 + 60ms, AF_INET6, 0, 0, found({"2001:db8::1"}));
    schedule.attempt_failed(t0 + 60ms, next_address(schedule, t0 + 60ms), err,
                            got_socket);

    const auto action = schedule.next_action(t0 + 60ms);

    EXPECT_EQ(describe(action),
              "give up: Cannot connect to event console at 192.0.2.1:6558 "
              "(Connection refused)");
}

INSTANTIATE_TEST_SUITE_P(ConnectionSchedule, IPv6FailureSayingLittle,
                         testing::Values(std::tuple{EAFNOSUPPORT, false},
                                         std::tuple{EADDRNOTAVAIL, true},
                                         std::tuple{ENETUNREACH, true}));

TEST(ConnectionSchedule, UnreachableIPv6NetworkIsntReportedNextToATimeout) {
    auto schedule = make_schedule();
    schedule.lookup_answered(t0, AF_INET6, 0, 0, found({"2001:db8::1"}));
    schedule.lookup_answered(t0, AF_INET, 0, 0, found({"192.0.2.1"}));
    schedule.attempt_failed(t0, next_address(schedule, t0), ENETUNREACH, true);
    schedule.attempt_going_on(t0, next_address(schedule, t0));

    const auto action = schedule.next_action(t0 + 20s);

    EXPECT_EQ(describe(action),
              "give up: Cannot connect to event console at 192.0.2.1:6558 "
              "(timeout after 20 seconds)");
}

TEST(ConnectionSchedule, UnreachableIPv4NetworkIsReportedNextToATimeout) {
    auto schedule = make_schedule();
    schedule.lookup_answered(t0, AF_INET6, EAI_NODATA, 0, nullptr);
    schedule.lookup_answered(t0, AF_INET, 0, 0,
                             found({"192.0.2.1", "192.0.2.2"}));
    schedule.attempt_failed(t0, next_address(schedule, t0), ENETUNREACH, true);
    schedule.attempt_going_on(t0, next_address(schedule, t0));

    const auto action = schedule.next_action(t0 + 20s);

    EXPECT_EQ(describe(action),
              "give up: Cannot connect to event console at 192.0.2.1:6558 "
              "(Network is unreachable) or 192.0.2.2:6558 (timeout after 20 "
              "seconds)");
}

TEST(ConnectionSchedule, LastOfSeveralFailuresOfAFamilyIsReported) {
    auto schedule = make_schedule();
    schedule.lookup_answered(t0, AF_INET6, EAI_NODATA, 0, nullptr);
    schedule.lookup_answered(t0, AF_INET, 0, 0,
                             found({"192.0.2.1", "192.0.2.2"}));
    schedule.attempt_failed(t0, next_address(schedule, t0), ECONNREFUSED, true);
    schedule.attempt_failed(t0, next_address(schedule, t0), EHOSTUNREACH, true);

    const auto action = schedule.next_action(t0);

    EXPECT_EQ(describe(action),
              "give up: Cannot connect to event console at 192.0.2.2:6558 "
              "(No route to host)");
}

// Like for an IPv6 neighbor not answering, which fails after IPv4 is refused.
TEST(ConnectionSchedule, LaterFailureOfTheOtherFamilyDoesntHideAFailure) {
    auto schedule = make_schedule();
    schedule.lookup_answered(t0, AF_INET6, 0, 0, found({"2001:db8::1"}));
    schedule.lookup_answered(t0, AF_INET, 0, 0, found({"192.0.2.1"}));
    const auto &ipv6_address = next_address(schedule, t0);
    schedule.attempt_going_on(t0, ipv6_address);
    schedule.attempt_failed(t0 + 250ms, next_address(schedule, t0 + 250ms),
                            ECONNREFUSED, true);
    schedule.attempt_failed(t0 + 3s, ipv6_address, EHOSTUNREACH, true);

    const auto action = schedule.next_action(t0 + 3s);

    EXPECT_EQ(describe(action),
              "give up: Cannot connect to event console at [2001:db8::1]:6558 "
              "(No route to host) or 192.0.2.1:6558 (Connection refused)");
}

TEST(ConnectionSchedule, LastIPv6FailureSayingLittleIsReportedIfNothingElse) {
    auto schedule = make_schedule();
    schedule.lookup_answered(t0, AF_INET6, 0, 0,
                             found({"2001:db8::1", "2001:db8::2"}));
    schedule.lookup_answered(t0, AF_INET, EAI_NODATA, 0, nullptr);
    schedule.attempt_failed(t0, next_address(schedule, t0), EAFNOSUPPORT,
                            false);
    schedule.attempt_failed(t0, next_address(schedule, t0), EAFNOSUPPORT,
                            false);

    const auto action = schedule.next_action(t0);

    EXPECT_EQ(describe(action),
              "give up: Cannot connect to event console at [2001:db8::2]:6558 "
              "(Address family not supported by protocol)");
}

TEST(ConnectionSchedule, LookupTimeoutIsReportedNextToARefusedConnection) {
    auto schedule = make_schedule();
    schedule.lookup_answered(t0, AF_INET, 0, 0, found({"192.0.2.1"}));
    schedule.attempt_failed(t0 + 50ms, next_address(schedule, t0 + 50ms),
                            ECONNREFUSED, true);

    const auto action = schedule.next_action(t0 + 20s);

    EXPECT_EQ(describe(action),
              "give up: Cannot connect to event console at 192.0.2.1:6558 "
              "(Connection refused) or resolve the IPv6 addresses of "
              "ec.example (timeout after 20 seconds)");
}

TEST(ConnectionSchedule, LookupFailureIsReportedNextToARefusedConnection) {
    auto schedule = make_schedule();
    schedule.lookup_answered(t0, AF_INET6, EAI_AGAIN, 0, nullptr);
    schedule.lookup_answered(t0, AF_INET, 0, 0, found({"192.0.2.1"}));
    schedule.attempt_failed(t0, next_address(schedule, t0), ECONNREFUSED, true);

    const auto action = schedule.next_action(t0);

    EXPECT_EQ(describe(action),
              "give up: Cannot connect to event console at 192.0.2.1:6558 "
              "(Connection refused) or resolve the IPv6 addresses of "
              "ec.example (Temporary failure in name resolution)");
}

TEST(ConnectionSchedule, UnreachableIPv6NetworkDoesntHideALookupTimeout) {
    auto schedule = make_schedule();
    schedule.lookup_answered(t0, AF_INET6, 0, 0, found({"2001:db8::1"}));
    schedule.attempt_failed(t0, next_address(schedule, t0), ENETUNREACH, true);

    const auto action = schedule.next_action(t0 + 20s);

    EXPECT_EQ(describe(action),
              "give up: Cannot resolve the IPv4 addresses of ec.example "
              "(timeout after 20 seconds)");
}

TEST(ConnectionSchedule, UnreachableIPv6NetworkDoesntHideALookupFailure) {
    auto schedule = make_schedule();
    schedule.lookup_answered(t0, AF_INET6, 0, 0, found({"2001:db8::1"}));
    schedule.lookup_answered(t0, AF_INET, EAI_AGAIN, 0, nullptr);
    schedule.attempt_failed(t0, next_address(schedule, t0), ENETUNREACH, true);

    const auto action = schedule.next_action(t0);

    EXPECT_EQ(describe(action),
              "give up: Cannot resolve the IPv4 addresses of ec.example "
              "(Temporary failure in name resolution)");
}

TEST(ConnectionSchedule, LookupFailureIsReportedNextToALookupTimeout) {
    auto schedule = make_schedule();
    schedule.lookup_answered(t0, AF_INET6, EAI_AGAIN, 0, nullptr);

    const auto action = schedule.next_action(t0 + 20s);

    EXPECT_EQ(describe(action),
              "give up: Cannot resolve the IPv6 addresses of ec.example "
              "(Temporary failure in name resolution) or resolve the IPv4 "
              "addresses of ec.example (timeout after 20 seconds)");
}

// Like for "fe80::1%nosuch", where IPv6 reports the unknown zone and IPv4 the
// wrong family.
class LookupFailuresInEitherOrder : public testing::TestWithParam<bool> {};

TEST_P(LookupFailuresInEitherOrder, ReportTheMoreTellingOne) {
    const bool ipv6_answers_first = GetParam();
    auto schedule = make_schedule();
    for (const int family : ipv6_answers_first
                                ? std::vector{AF_INET6, AF_INET}
                                : std::vector{AF_INET, AF_INET6}) {
        schedule.lookup_answered(
            t0, family, family == AF_INET6 ? EAI_NONAME : EAI_ADDRFAMILY, 0,
            nullptr);
    }

    const auto action = schedule.next_action(t0);

    EXPECT_EQ(describe(action),
              "give up: Cannot resolve the addresses of ec.example (Name or "
              "service not known)");
}

INSTANTIATE_TEST_SUITE_P(ConnectionSchedule, LookupFailuresInEitherOrder,
                         testing::Bool());
