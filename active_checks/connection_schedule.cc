// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "active_checks/connection_schedule.h"

#include <sys/socket.h>

#include <algorithm>
#include <array>
#include <cerrno>
#include <initializer_list>
#include <system_error>
#include <utility>

namespace check_mkevents {

std::string numeric_host(const addrinfo &address) {
    std::array<char, NI_MAXHOST> host{};
    if (getnameinfo(address.ai_addr, address.ai_addrlen, host.data(),
                    host.size(), nullptr, 0, NI_NUMERICHOST) != 0) {
        return "?";
    }
    return address.ai_addr->sa_family == AF_INET6
               ? "[" + std::string{host.data()} + "]"
               : host.data();
}

void Failure::record(const addrinfo &failed, int error, bool got_socket) {
    const bool little =
        failed.ai_family == AF_INET6 &&
        (!got_socket || error == EADDRNOTAVAIL || error == ENETUNREACH);
    if (!little || err == 0 || says_little) {
        address = numeric_host(failed);
        err = error;
        says_little = little;
    }
}

void LookupFailures::record(int family, int rc, int err) {
    (family == AF_INET6 ? ipv6_ : ipv4_) = Lookup{.rc = rc, .err = err};
}

std::string LookupFailures::reason() const {
    return message(weight(ipv4_.rc) > weight(ipv6_.rc) ? ipv4_ : ipv6_);
}

std::optional<std::string> LookupFailures::telling_failure(int family) const {
    const auto &lookup = family == AF_INET6 ? ipv6_ : ipv4_;
    if (weight(lookup.rc) > weight(EAI_NODATA)) {
        return message(lookup);
    }
    return {};
}

std::string LookupFailures::message(const Lookup &failure) {
    return failure.rc == EAI_SYSTEM
               ? std::generic_category().message(failure.err)
               : gai_strerror(failure.rc);
}

// How much a failure says, the more the higher.
int LookupFailures::weight(int rc) {
    switch (rc) {
        case 0:
            return 0;
        case EAI_ADDRFAMILY:
            return 1;
        case EAI_NONAME:
        case EAI_NODATA:
            return 2;
        default:
            return 3;
    }
}

void WaitingAddresses::add(const addrinfo *addresses) {
    for (const auto *address = addresses; address != nullptr;
         address = address->ai_next) {
        (address->ai_family == AF_INET6 ? ipv6_ : ipv4_).push_back(address);
    }
}

const std::deque<const addrinfo *> &WaitingAddresses::queue() const {
    const auto &turn = last_was_ipv6_ ? ipv4_ : ipv6_;
    return turn.empty() ? (last_was_ipv6_ ? ipv6_ : ipv4_) : turn;
}

const addrinfo *WaitingAddresses::peek() const { return queue().front(); }

const addrinfo *WaitingAddresses::next() {
    const auto *address = peek();
    last_was_ipv6_ = address->ai_family == AF_INET6;
    (last_was_ipv6_ ? ipv6_ : ipv4_).pop_front();
    return address;
}

ConnectionSchedule::ConnectionSchedule(std::string name, uint16_t port,
                                       Deadline deadline)
    : name_{std::move(name)}, port_{port}, deadline_{deadline} {}

void ConnectionSchedule::lookup_answered(Clock::time_point now, int family,
                                         int rc, int err, addrinfo *addresses) {
    if (family == AF_INET6) {
        ipv6_lookup_pending_ = false;
        ipv6_awaited_until_.reset();
    } else {
        ipv4_lookup_pending_ = false;
        if (rc == 0 && ipv6_lookup_pending_) {
            ipv6_awaited_until_ = now + resolution_delay;
        }
    }
    if (rc == 0) {
        answers_.emplace_back(addresses, &freeaddrinfo);
        waiting_.add(addresses);
    } else {
        lookup_failures_.record(family, rc, err);
    }
}

void ConnectionSchedule::attempt_going_on(Clock::time_point now,
                                          const addrinfo &address) {
    going_on_.push_back(&address);
    next_turn_ = now + attempt_delay;
}

void ConnectionSchedule::attempt_failed(Clock::time_point now,
                                        const addrinfo &address, int err,
                                        bool got_socket) {
    (address.ai_family == AF_INET6 ? ipv6_failure_ : ipv4_failure_)
        .record(address, err, got_socket);
    // If the youngest attempt fails, the next address gets its turn at once.
    // An older one leaves the Connection Attempt Delay of the younger ones, and
    // an attempt failing at once has got its turn already.
    if (!going_on_.empty() && going_on_.back() == &address) {
        next_turn_ = now;
    }
    std::erase(going_on_, &address);
}

Action ConnectionSchedule::next_action(Clock::time_point now) {
    if (now >= deadline_.end()) {
        return GiveUp{.reason = failure_reasons()};
    }
    if (may_start_attempt(now)) {
        ipv6_awaited_until_.reset();
        return StartAttempt{.address = waiting_.next()};
    }
    if (going_on_.empty() && !lookups_pending()) {
        return GiveUp{.reason = failure_reasons()};
    }
    return Wait{.until =
                    waiting_.empty()
                        ? deadline_.end()
                        : std::min(deadline_.end(),
                                   ipv6_awaited_until_.value_or(next_turn_))};
}

bool ConnectionSchedule::may_start_attempt(Clock::time_point now) const {
    return !waiting_.empty() &&
           !(ipv6_awaited_until_ && now < *ipv6_awaited_until_) &&
           (going_on_.empty() || now >= next_turn_);
}

// The family's lookup problem: a timeout if pending, else a telling failure.
std::optional<std::string> ConnectionSchedule::lookup_problem(
    int family) const {
    if (family == AF_INET6 ? ipv6_lookup_pending_ : ipv4_lookup_pending_) {
        return deadline_.timeout_message();
    }
    return lookup_failures_.telling_failure(family);
}

// The problems of the lookups, e.g. "resolve the IPv6 addresses of myhost
// (...)". Without any address, one reason covers both families if possible.
std::string ConnectionSchedule::lookup_problems() const {
    const auto ipv6 = lookup_problem(AF_INET6);
    const auto ipv4 = lookup_problem(AF_INET);
    if (answers_.empty() && ipv6 == ipv4) {
        return "resolve the addresses of " + name_ + " (" +
               ipv6.value_or(lookup_failures_.reason()) + ")";
    }
    std::string problems;
    const auto add = [&](const std::string &family,
                         const std::optional<std::string> &problem) {
        if (problem) {
            problems += std::string{problems.empty() ? "" : " or "} +
                        "resolve the " + family + " addresses of " + name_ +
                        " (" + *problem + ")";
        }
    };
    add("IPv6", ipv6);
    add("IPv4", ipv4);
    return problems;
}

// Why nothing has connected: the failures, the timeouts, and the lookup
// problems. Anything else hides an IPv6 failure saying little.
std::string ConnectionSchedule::failure_reasons() const {
    std::string failures;
    const auto add = [&](const std::string &address,
                         const std::string &reason) {
        failures += (failures.empty() ? "" : " or ") + address + ":" +
                    std::to_string(port_) + " (" + reason + ")";
    };
    // Only the deadline leaves attempts, lookups or addresses waiting.
    const bool timed_out =
        !going_on_.empty() || lookups_pending() || !waiting_.empty();
    const auto problems = lookup_problems();
    const bool hides_little =
        timed_out || !problems.empty() || ipv4_failure_.err != 0;
    // Unlike for a socket timeout, EAGAIN from connect() isn't a timeout.
    for (const auto *failure : {&ipv6_failure_, &ipv4_failure_}) {
        if (failure->err != 0 && !(hides_little && failure->says_little)) {
            add(failure->address,
                std::generic_category().message(failure->err));
        }
    }
    // The oldest attempt of each family, so both show up as tried.
    for (const bool ipv6 : {true, false}) {
        const auto oldest =
            std::ranges::find_if(going_on_, [&](const addrinfo *attempt) {
                return (attempt->ai_family == AF_INET6) == ipv6;
            });
        if (oldest != going_on_.end()) {
            add(numeric_host(**oldest), deadline_.timeout_message());
        }
    }
    if (going_on_.empty() && !waiting_.empty()) {
        add(numeric_host(*waiting_.peek()), deadline_.timeout_message());
    }
    std::string reasons =
        failures.empty() ? "" : "connect to event console at " + failures;
    if (!problems.empty()) {
        reasons += std::string{reasons.empty() ? "" : " or "} + problems;
    }
    return "Cannot " + reasons;
}

}  // namespace check_mkevents
