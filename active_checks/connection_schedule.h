// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef connection_schedule_h
#define connection_schedule_h

#include <netdb.h>

#include <chrono>
#include <cstdint>
#include <deque>
#include <memory>
#include <optional>
#include <string>
#include <variant>
#include <vector>

#include "active_checks/deadline.h"

namespace check_mkevents {

// Returns the numeric address, an IPv6 one in brackets to append the port.
std::string numeric_host(const addrinfo &address);

// The "Connection Attempt Delay" of Happy Eyeballs (RFC 8305).
constexpr std::chrono::milliseconds attempt_delay{250};

// How long IPv4 waits for IPv6, the "Resolution Delay" of Happy Eyeballs.
constexpr std::chrono::milliseconds resolution_delay{50};

// What to do next for connecting, see ConnectionSchedule::next_action().
struct StartAttempt {
    const addrinfo *address;
};

struct Wait {
    Clock::time_point until;
};

struct GiveUp {
    std::string reason;  // e.g. "Cannot connect to event console at ..."
};

using Action = std::variant<StartAttempt, Wait, GiveUp>;

// The last failure of a family, but an IPv6 one saying little, e.g. for want of
// a route, doesn't replace one saying more.
struct Failure {
    std::string address;
    int err = 0;
    bool says_little = false;

    void record(const addrinfo &failed, int error, bool got_socket);
};

// The failures of the lookups. Without a telling one, we report the one saying
// the most, IPv6 on a tie, regardless of the order of the answers.
class LookupFailures {
public:
    void record(int family, int rc, int err);

    [[nodiscard]] std::string reason() const;

    // The family's failure if it says more than "no addresses", e.g. SERVFAIL.
    [[nodiscard]] std::optional<std::string> telling_failure(int family) const;

private:
    struct Lookup {
        int rc = 0;   // the result of getaddrinfo(), 0 if not failed (yet)
        int err = 0;  // errno, the reason for EAI_SYSTEM
    };
    Lookup ipv6_;
    Lookup ipv4_;

    static std::string message(const Lookup &failure);
    static int weight(int rc);
};

// The addresses waiting for their turn, the families alternating, IPv6 first.
// Unlike in RFC 8305, an IPv4 preference in /etc/gai.conf doesn't count.
class WaitingAddresses {
public:
    void add(const addrinfo *addresses);

    [[nodiscard]] bool empty() const { return ipv6_.empty() && ipv4_.empty(); }

    // The address whose turn is next, there must be one.
    [[nodiscard]] const addrinfo *peek() const;

    // Takes the address whose turn is next, there must be one.
    const addrinfo *next();

private:
    std::deque<const addrinfo *> ipv6_;
    std::deque<const addrinfo *> ipv4_;  // and any other family
    bool last_was_ipv6_ = false;

    [[nodiscard]] const std::deque<const addrinfo *> &queue() const;
};

// The decisions of Happy Eyeballs (RFC 8305) without any I/O: The caller
// reports what happened when, so tests can use any times.
class ConnectionSchedule {
public:
    ConnectionSchedule(std::string name, uint16_t port, Deadline deadline);

    // A lookup has answered, see getaddrinfo(). We own the addresses now.
    void lookup_answered(Clock::time_point now, int family, int rc, int err,
                         addrinfo *addresses);

    // The attempt next_action() has started goes on.
    void attempt_going_on(Clock::time_point now, const addrinfo &address);

    // The attempt has failed, at once or later, maybe without a socket.
    void attempt_failed(Clock::time_point now, const addrinfo &address, int err,
                        bool got_socket);

    // Start the next attempt, wait for something to happen, or give up.
    Action next_action(Clock::time_point now);

    [[nodiscard]] bool lookups_pending() const {
        return ipv6_lookup_pending_ || ipv4_lookup_pending_;
    }

private:
    std::string name_;
    uint16_t port_;
    Deadline deadline_;
    bool ipv6_lookup_pending_ = true;
    bool ipv4_lookup_pending_ = true;
    LookupFailures lookup_failures_;
    std::vector<std::unique_ptr<addrinfo, decltype(&freeaddrinfo)>> answers_;
    WaitingAddresses waiting_;
    std::optional<Clock::time_point> ipv6_awaited_until_;
    Clock::time_point next_turn_;
    std::vector<const addrinfo *> going_on_;  // the oldest first
    Failure ipv6_failure_;
    Failure ipv4_failure_;  // and any other family

    [[nodiscard]] bool may_start_attempt(Clock::time_point now) const;
    [[nodiscard]] std::optional<std::string> lookup_problem(int family) const;
    [[nodiscard]] std::string lookup_problems() const;
    [[nodiscard]] std::string failure_reasons() const;
};

}  // namespace check_mkevents

#endif  // connection_schedule_h
