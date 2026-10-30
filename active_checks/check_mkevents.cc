// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <fcntl.h>
#include <netdb.h>
#include <poll.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/un.h>
#include <unistd.h>

#include <algorithm>
#include <array>
#include <cerrno>
#include <chrono>
#include <climits>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <optional>
#include <span>
#include <sstream>  // IWYU pragma: keep
#include <string>
#include <string_view>
#include <system_error>
#include <thread>
#include <utility>
#include <variant>
#include <vector>

#include "active_checks/arguments.h"
#include "active_checks/connection_schedule.h"
#include "active_checks/deadline.h"

namespace {

using check_mkevents::Clock;
using check_mkevents::ConnectionSchedule;
using check_mkevents::Deadline;
using check_mkevents::GiveUp;
using check_mkevents::numeric_host;
using check_mkevents::parse_number;
using check_mkevents::parse_port;
using check_mkevents::parse_remote;
using check_mkevents::StartAttempt;
using check_mkevents::Wait;

enum class State { ok = 0, warn = 1, crit = 2, unknown = 3 };

std::ostream &operator<<(std::ostream &os, State state) {
    switch (state) {
        case State::ok:
            return os << "OK";
        case State::warn:
            return os << "WARN";
        case State::crit:
            return os << "CRIT";
        case State::unknown:
            return os << "UNKNOWN";
    }
    return os;  // make compilers happy
}

// The order of the states from best to worst. CRIT is worse than UNKNOWN, like
// in Livestatus' badness() and in State.worst() of the check API.
int severity(State state) {
    switch (state) {
        case State::ok:
            return 0;
        case State::warn:
            return 1;
        case State::unknown:
            return 2;
        case State::crit:
            return 3;
    }
    return 2;  // make compilers happy
}

// Parses an event state, which the event console sends as 0, 1, 2 or 3.
std::optional<State> parse_state(std::string_view s) {
    if (s.size() == 1 && s[0] >= '0' && s[0] <= '3') {
        return static_cast<State>(s[0] - '0');
    }
    return {};
}

void print_line(const std::string &output) {
    // Make sure that plugin output does not contain a vertical bar. If that is
    // the case then replace it with a Unicode "Light vertical bar". Same as in
    // Checkmk, which turns it back into a vertical bar for notifications. A
    // NUL byte would end the output for the core, so replace it by a space.
    for (const char i : output) {
        if (i == '|') {
            // \u2758 (utf-8 encoded light vertical bar)
            std::cout << "\xe2\x9d\x98";  // NOLINT
        } else if (i == '\0') {
            std::cout << ' ';
        } else {
            std::cout << i;
        }
    }
    std::cout << '\n';
}

// A lookup thread may still run, so we skip the exit handlers, which could
// destroy what it uses.
[[noreturn]] void exit_with(State state) {
    std::cout.flush();
    std::_Exit(static_cast<int>(state));
}

[[noreturn]] void reply_and_exit(State state, const std::string &output) {
    std::cout << state << " - ";
    print_line(output);
    exit_with(state);
}

constexpr std::chrono::seconds default_timeout{20};

// The caller saves errno first, as building the message may change it.
[[noreturn]] void io_error(const std::string &message, int err,
                           Deadline deadline) {
    // The timeouts of our blocking sockets expire with one of these errors.
    const std::string reason = err == EAGAIN || err == EWOULDBLOCK
                                   ? deadline.timeout_message()
                                   : std::generic_category().message(err);
    reply_and_exit(State::unknown, message + " (" + reason + ")");
}

// A socket timeout only expires while a call waits, so a peer that keeps
// sending or reading would keep a loop of such calls going past the deadline.
// That's why the loop checks the deadline before each call, reporting a timeout
// with the message of the call.
void check_deadline(const std::string &message, Deadline deadline) {
    if (deadline.has_passed()) {
        reply_and_exit(State::unknown,
                       message + " (" + deadline.timeout_message() + ")");
    }
}

// Limits the next blocking call on the socket to the time left until the
// deadline, via the timeout option SO_RCVTIMEO for receiving or SO_SNDTIMEO for
// sending. Linux uses the send timeout for connect(), too.
void limit_to_deadline(int sock, int option, Deadline deadline) {
    using std::chrono::duration_cast;
    using std::chrono::microseconds;
    using std::chrono::seconds;
    // A timeout of zero would mean no timeout at all.
    const auto left =
        std::max(duration_cast<microseconds>(deadline.end() - Clock::now()),
                 microseconds{1});
    const auto left_seconds = duration_cast<seconds>(left);
    const timeval tv{.tv_sec = left_seconds.count(),
                     .tv_usec = (left - left_seconds).count()};
    if (setsockopt(sock, SOL_SOCKET, option, &tv, sizeof(tv)) == -1) {
        const int err = errno;
        io_error("Cannot set socket timeout", err, deadline);
    }
}

// Cuts a string after at most max_size bytes, but doesn't cut a character in
// two, i.e. not in front of a continuation byte 10xxxxxx of UTF-8.
std::string cut_at(std::string_view str, std::string_view::size_type max_size) {
    if (str.size() <= max_size) {
        return std::string{str};
    }
    auto end = max_size;
    while (end > 0 && (static_cast<unsigned char>(str[end]) & 0xC0) == 0x80) {
        end--;
    }
    return std::string{str.substr(0, end)} + "[...]";
}

// An answer with thousands of events would flood the output, so we show only
// its start, cut at a line break if that keeps at least half of it, i.e. not
// after the header if a long row follows.
std::string start_of_response(const std::string &response) {
    constexpr std::string::size_type max_size = 1000;
    if (response.size() <= max_size) {
        return response;
    }
    const auto line_break = response.rfind('\n', max_size - 1);
    const bool keeps_enough =
        line_break != std::string::npos && line_break + 1 >= max_size / 2;
    return cut_at(response, keeps_enough ? line_break + 1 : max_size);
}

[[noreturn]] void invalid_response(const std::string &problem,
                                   const std::string &query,
                                   const std::string &response) {
    reply_and_exit(State::unknown,
                   "Event console answered with " + problem + "\nQuery was:\n" +
                       query + "\nReceived " + std::to_string(response.size()) +
                       " byte response:\n" + start_of_response(response));
}

[[noreturn]] void missing_header(const std::string &header,
                                 const std::string &query,
                                 const std::string &response) {
    invalid_response("incorrect header (missing " + header + ")", query,
                     response);
}

// The event console closes the connection without answering when it denies
// access via TCP or can't handle the query. Depending on the timing, we see
// one of these errors or an empty answer.
bool closed_by_peer(int err) {
    return err == EPIPE || err == ECONNRESET || err == ENOTCONN;
}

// An IPv6 peer hints at an access list lacking our IPv6 address.
[[noreturn]] void no_answer(const std::string &query, const std::string &peer) {
    reply_and_exit(State::unknown,
                   "Event console" + std::string{peer.empty() ? "" : " at "} +
                       peer +
                       " closed the connection without answering, "
                       "see its log file var/log/mkeventd.log for the reason, "
                       "e.g. a denied access via TCP or an invalid regular "
                       "expression for the application\nQuery was:\n" +
                       query);
}

// Splits the response into its lines, which stay in the response.
std::vector<std::string_view> split_lines(std::string_view response) {
    std::vector<std::string_view> lines;
    while (!response.empty()) {
        const auto end = std::min(response.find('\n'), response.size());
        lines.push_back(response.substr(0, end));
        response.remove_prefix(std::min(end + 1, response.size()));
    }
    return lines;
}

// Splits a line of the plain output format at the tabs, keeping empty columns
// like an empty event text at the end of the line.
std::vector<std::string_view> split_columns(std::string_view line) {
    std::vector<std::string_view> columns;
    std::string_view::size_type start = 0;
    while (true) {
        const auto end = line.find('\t', start);
        columns.push_back(line.substr(start, end - start));
        if (end == std::string_view::npos) {
            return columns;
        }
        start = end + 1;
    }
}

[[noreturn]] void usage() {
    reply_and_exit(
        State::unknown,
        "Usage: check_mkevents [-s SOCKETPATH] [-H REMOTE[:PORT]] [-p PORT] [-t SECONDS] [-a] [-l] [-L] [-q] [--] HOST [APPLICATION]\n"
        " -s    connect via this UNIX socket, by default $OMD_ROOT/tmp/run/mkeventd/status.\n"
        " -H    connect via TCP, e.g. to myhost:6558 or [2001:db8::1]:6558.\n"
        " -p    connect to PORT if REMOTE has none, 6558 by default.\n"
        " -t    time out after SECONDS, 20 by default.\n"
        " -a    do not take acknowledged events into account.\n"
        " -l    show last log message in summary/short output.\n"
        " -L    show last log message in details/long output.\n"
        " -q    take a backslash in HOST as quoting a following slash or backslash.\n"
        " --    end the options, e.g. for a HOST starting with a dash.\n"
        " HOST  may be a hostname, an IP address or hostname/IP-address.");
}

// More than an hour makes no sense for a check.
constexpr unsigned long max_timeout_seconds = 3600;

[[noreturn]] void invalid_remote(const std::string &remote) {
    reply_and_exit(State::unknown,
                   "Invalid remote address '" + remote +
                       "', expected HOST[:PORT], e.g. myhost:6558 or "
                       "[2001:db8::1]:6558");
}

// Splits a host specification like "myhost/10.1.2.3" at the slashes. If it is
// quoted, a backslash quotes a following slash or backslash, e.g. in
// "Router A\/B".
std::vector<std::string> split_host_spec(const std::string &spec, bool quoted) {
    std::vector<std::string> hosts{""};
    for (size_t i = 0; i < spec.size(); i++) {
        if (quoted && spec[i] == '\\' && i + 1 < spec.size() &&
            (spec[i + 1] == '/' || spec[i + 1] == '\\')) {
            hosts.back() += spec[++i];
        } else if (spec[i] == '/') {
            hosts.emplace_back();
        } else {
            hosts.back() += spec[i];
        }
    }
    return hosts;
}

// Drops the quoting of a host specification for showing it.
std::string unquote_host_spec(const std::string &spec, bool quoted) {
    const auto hosts = split_host_spec(spec, quoted);
    std::string result = hosts.front();
    for (size_t i = 1; i < hosts.size(); i++) {
        result += "/" + hosts[i];
    }
    return result;
}

// Host names and IP addresses consist of these characters only.
bool is_plain_host(const std::string &host) {
    return host.find_first_not_of(
               "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
               "0123456789.-_:") == std::string::npos;
}

std::string quote_regex(const std::string &s) {
    std::string result;
    for (const char c : s) {
        if (std::string_view{R"(\.^$*+?{}[]|())"}.find(c) !=
            std::string_view::npos) {
            result += '\\';
        }
        result += c;
    }
    return result;
}

// The event console drops whitespace around the value of a filter, so a single
// host loses it, and so does a host of a list.
std::string strip_whitespace(const std::string &s) {
    const char *const whitespace = " \t\n\v\f\r";
    const auto first = s.find_first_not_of(whitespace);
    return first == std::string::npos
               ? ""
               : s.substr(first, s.find_last_not_of(whitespace) - first + 1);
}

std::string host_filter(const std::string &spec, bool quoted) {
    const auto hosts = split_host_spec(spec, quoted);
    if (hosts.size() == 1) {
        return "Filter: event_host =~ " + hosts[0] + "\n";
    }
    // The event console splits the argument of "in" at whitespace, so we can
    // use it, which is faster than a regex, for plain hosts only.
    std::string in_list;
    std::string regex;
    bool all_plain = true;
    for (const auto &spec_host : hosts) {
        const auto host = strip_whitespace(spec_host);
        if (host.empty()) {
            continue;
        }
        all_plain = all_plain && is_plain_host(host);
        in_list += (in_list.empty() ? "" : " ") + host;
        regex += (regex.empty() ? "" : "|") + quote_regex(host);
    }
    // Unlike $, \Z doesn't match in front of a newline at the end, too.
    return all_plain ? "Filter: event_host in " + in_list + "\n"
                     : "Filter: event_host ~~ ^(?:" + regex + ")\\Z\n";
}

struct Options {
    const char *remote_host = nullptr;
    uint16_t remote_port = 6558;  // if remote_host has none
    std::string unixsocket_path;
    std::chrono::seconds timeout = default_timeout;
    bool ignore_acknowledged = false;
    bool last_log_in_summary = false;
    bool last_log_in_details = false;
    bool host_spec_quoted = false;
    const char *host = nullptr;
    const char *application = nullptr;
};

Options parse_options(int argc, char **argv) {
    Options options;
    opterr = 0;  // We show the usage instead of the error of getopt().
    // "+" ends the options at HOST, so APPLICATION may start with a dash.
    int option = 0;
    // NOLINTNEXTLINE(concurrency-mt-unsafe)
    while ((option = getopt(argc, argv, "+s:H:p:t:alLq")) != -1) {
        switch (option) {
            case 's':
                options.unixsocket_path = optarg;
                break;
            case 'H':
                options.remote_host = optarg;
                break;
            case 'p': {
                const auto port = parse_port(optarg);
                if (!port) {
                    reply_and_exit(State::unknown,
                                   "Invalid port '" + std::string{optarg} +
                                       "', expected 1 to 65535");
                }
                options.remote_port = *port;
                break;
            }
            case 't': {
                const auto seconds = parse_number(optarg, max_timeout_seconds);
                if (!seconds) {
                    reply_and_exit(State::unknown,
                                   "Invalid timeout '" + std::string{optarg} +
                                       "', expected 1 to " +
                                       std::to_string(max_timeout_seconds) +
                                       " seconds");
                }
                options.timeout = std::chrono::seconds{*seconds};
                break;
            }
            case 'a':
                options.ignore_acknowledged = true;
                break;
            case 'l':
                options.last_log_in_summary = true;
                break;
            case 'L':
                options.last_log_in_details = true;
                break;
            case 'q':
                options.host_spec_quoted = true;
                break;
            default:
                usage();
        }
    }
    const auto positional = std::span{argv, static_cast<size_t>(argc)}.subspan(
        static_cast<size_t>(optind));
    // For compatibility, arguments after APPLICATION are ignored.
    if (positional.empty()) {
        usage();
    }
    options.host = positional[0];
    options.application = positional.size() >= 2 ? positional[1] : nullptr;
    return options;
}

struct Attempt {
    const addrinfo *address;
    int sock;
};

// The answer of a lookup for one family
struct Answer {
    int family;
    int rc;   // the result of getaddrinfo()
    int err;  // errno, the reason for EAI_SYSTEM
    addrinfo *addresses;
};

// A lookup sends its answer through a pipe, which writes it in one go.
static_assert(sizeof(Answer) <= PIPE_BUF);

// getaddrinfo() has no timeout, so each family gets a detached thread, using
// only copies of our data. The pipe stays open, so writing can't raise SIGPIPE.
void start_lookup(const std::string &name, const std::string &service,
                  int family, int pipe_fd) {
    try {
        std::thread{[name, service, family, pipe_fd] {
            addrinfo hints{};
            hints.ai_family = family;
            hints.ai_socktype = SOCK_STREAM;
            Answer answer{
                .family = family, .rc = 0, .err = 0, .addresses = nullptr};
            answer.rc = ::getaddrinfo(name.c_str(), service.c_str(), &hints,
                                      &answer.addresses);
            answer.err = errno;
            [[maybe_unused]] const auto written =
                ::write(pipe_fd, &answer, sizeof(answer));
        }}.detach();
    } catch (const std::system_error &e) {
        reply_and_exit(State::unknown, "Cannot start resolving names (" +
                                           e.code().message() + ")");
    }
}

// Returns the result of a finished attempt to connect, 0 for success.
int connect_error(int sock) {
    int err = 0;
    socklen_t size = sizeof(err);
    if (::getsockopt(sock, SOL_SOCKET, SO_ERROR, &err, &size) == -1) {
        return errno;
    }
    return err;
}

// Happy Eyeballs: ConnectionSchedule decides, this class does the I/O.
class HappyEyeballs {
public:
    HappyEyeballs(const std::string &name, uint16_t port, Deadline deadline)
        : name_{name}, deadline_{deadline}, schedule_{name, port, deadline} {
        if (::pipe2(pipe_.data(), O_CLOEXEC) == -1) {
            const int err = errno;
            io_error("Cannot create a pipe for resolving names", err,
                     deadline_);
        }
        const auto service = std::to_string(port);
        start_lookup(name_, service, AF_INET6, pipe_[1]);  // IPv6 first
        start_lookup(name_, service, AF_INET, pipe_[1]);
    }

    // Returns the connected attempt or reports the failure. Its address lives
    // as long as this object.
    Attempt connect() {
        while (true) {
            const auto now = Clock::now();
            const auto action = schedule_.next_action(now);
            std::optional<Attempt> connected;
            if (const auto *start = std::get_if<StartAttempt>(&action)) {
                connected = start_attempt(now, *start->address);
            } else if (const auto *wait = std::get_if<Wait>(&action)) {
                connected = this->wait(wait->until);
            } else {
                reply_and_exit(State::unknown, std::get<GiveUp>(action).reason);
            }
            if (connected) {
                for (const auto &attempt : going_on_) {
                    ::close(attempt.sock);
                }
                return *connected;
            }
        }
    }

private:
    std::string name_;
    Deadline deadline_;
    std::array<int, 2> pipe_{};  // from the lookups, never closed
    ConnectionSchedule schedule_;
    std::vector<Attempt> going_on_;

    // Returns the attempt if it connects at once.
    std::optional<Attempt> start_attempt(Clock::time_point now,
                                         const addrinfo &address) {
        const int sock =
            ::socket(address.ai_family, address.ai_socktype | SOCK_NONBLOCK,
                     address.ai_protocol);
        if (sock == -1) {
            const int err = errno;
            schedule_.attempt_failed(now, address, err, /*got_socket=*/false);
            return {};
        }
        if (::connect(sock, address.ai_addr, address.ai_addrlen) == 0) {
            return Attempt{.address = &address, .sock = sock};
        }
        const int err = errno;
        if (err == EINPROGRESS) {
            going_on_.push_back({.address = &address, .sock = sock});
            schedule_.attempt_going_on(now, address);
        } else {
            schedule_.attempt_failed(now, address, err, /*got_socket=*/true);
            ::close(sock);
        }
        return {};
    }

    // Waits for attempts, answers or the time, returning a connected attempt.
    std::optional<Attempt> wait(Clock::time_point until) {
        std::vector<pollfd> fds;
        fds.reserve(going_on_.size() + 1);
        for (const auto &attempt : going_on_) {
            fds.push_back(
                {.fd = attempt.sock, .events = POLLOUT, .revents = 0});
        }
        const bool lookups_pending = schedule_.lookups_pending();
        if (lookups_pending) {
            fds.push_back({.fd = pipe_[0], .events = POLLIN, .revents = 0});
        }
        // A negative timeout would mean no timeout at all.
        const auto timeout = std::max(
            std::chrono::ceil<std::chrono::milliseconds>(until - Clock::now()),
            std::chrono::milliseconds{0});
        if (::poll(fds.data(), fds.size(), static_cast<int>(timeout.count())) ==
            -1) {
            const int err = errno;
            if (err != EINTR) {
                io_error("Cannot wait for the connection to the event console",
                         err, deadline_);
            }
            return {};
        }
        const auto now = Clock::now();
        if (lookups_pending && fds.back().revents != 0) {
            take_answer(now);
        }
        std::optional<Attempt> connected;
        std::vector<Attempt> still_going_on;
        for (size_t i = 0; i < going_on_.size(); i++) {
            if (connected || fds[i].revents == 0) {
                still_going_on.push_back(going_on_[i]);
            } else if (const int err = connect_error(going_on_[i].sock);
                       err == 0) {
                connected = going_on_[i];
            } else {
                schedule_.attempt_failed(now, *going_on_[i].address, err,
                                         /*got_socket=*/true);
                ::close(going_on_[i].sock);
            }
        }
        going_on_ = std::move(still_going_on);
        return connected;
    }

    // Takes the answer of a lookup, which has arrived.
    void take_answer(Clock::time_point now) {
        Answer answer{};
        const ssize_t bytes = ::read(pipe_[0], &answer, sizeof(answer));
        if (bytes != sizeof(answer)) {
            const int err = bytes == -1 ? errno : EIO;
            io_error("Cannot resolve the addresses of " + name_, err,
                     deadline_);
        }
        schedule_.lookup_answered(now, answer.family, answer.rc, answer.err,
                                  answer.addresses);
    }
};

// The socket timeouts for sending and receiving need a blocking socket.
void make_blocking(int sock, Deadline deadline) {
    // NOLINTNEXTLINE(cppcoreguidelines-pro-type-vararg)
    const int flags = ::fcntl(sock, F_GETFL);
    // NOLINTNEXTLINE(cppcoreguidelines-pro-type-vararg)
    if (flags == -1 || ::fcntl(sock, F_SETFL, flags & ~O_NONBLOCK) == -1) {
        const int err = errno;
        io_error("Cannot make the socket blocking", err, deadline);
    }
}

// A connection to the event console
struct Connection {
    int sock;
    std::string peer;  // the address for TCP, e.g. "[2001:db8::1]:6558"
};

Connection connect_via_tcp(const std::string &remote, uint16_t default_port,
                           Deadline deadline) {
    const auto parsed = parse_remote(remote, default_port);
    if (!parsed) {
        invalid_remote(remote);
    }
    const auto &[remote_hostaddress, remote_port] = *parsed;
    HappyEyeballs happy_eyeballs{remote_hostaddress, remote_port, deadline};
    const auto attempt = happy_eyeballs.connect();
    make_blocking(attempt.sock, deadline);
    return {.sock = attempt.sock,
            .peer = numeric_host(*attempt.address) + ":" +
                    std::to_string(remote_port)};
}

Connection connect_via_unix_socket(std::string unixsocket_path,
                                   Deadline deadline) {
    // Get omd environment
    if (unixsocket_path.empty()) {
        // NOLINTNEXTLINE(concurrency-mt-unsafe)
        const char *omd_path = getenv("OMD_ROOT");
        if (omd_path == nullptr) {
            reply_and_exit(State::unknown,
                           "OMD_ROOT is not set, no socket path is defined.");
        }
        unixsocket_path = std::string(omd_path) + "/tmp/run/mkeventd/status";
    }

    struct sockaddr_un addr{.sun_family = AF_UNIX, .sun_path = ""};
    if (unixsocket_path.size() >= sizeof(addr.sun_path)) {
        reply_and_exit(State::unknown,
                       "Cannot connect to event daemon via UNIX socket " +
                           unixsocket_path + " (path longer than " +
                           std::to_string(sizeof(addr.sun_path) - 1) +
                           " bytes)");
    }
    unixsocket_path.copy(&addr.sun_path[0], sizeof(addr.sun_path) - 1);
    addr.sun_path[sizeof(addr.sun_path) - 1] = '\0';

    const int sock = ::socket(AF_UNIX, SOCK_STREAM, 0);
    if (sock == -1) {
        const int err = errno;
        io_error("Cannot create client socket", err, deadline);
    }
    limit_to_deadline(sock, SO_SNDTIMEO, deadline);  // for connect()
    // NOLINTNEXTLINE(cppcoreguidelines-pro-type-reinterpret-cast)
    if (::connect(sock, reinterpret_cast<struct sockaddr *>(&addr),
                  sizeof(addr)) == -1) {
        const int err = errno;
        io_error(
            "Cannot connect to event daemon via UNIX socket " + unixsocket_path,
            err, deadline);
    }
    return {.sock = sock, .peer = ""};
}

std::string make_query(const char *host, bool host_spec_quoted,
                       const char *application) {
    std::string query;
    query += "GET events\n";
    query += "Columns: event_phase event_state event_text\n";

    query += host_filter(host, host_spec_quoted);
    query += "Filter: event_phase in open ack\n";
    query += "OutputFormat: plain\n";

    if (application != nullptr) {
        query += "Filter: event_application ~~ ";
        query += application;
        query += "\n";
    }
    return query;
}

void send_query(const Connection &connection, const std::string &query,
                Deadline deadline) {
    const std::string message = "Cannot send query to event console";
    std::string_view rest{query};
    while (!rest.empty()) {
        check_deadline(message, deadline);
        limit_to_deadline(connection.sock, SO_SNDTIMEO, deadline);
        // Report a closed connection instead of dying from SIGPIPE.
        const ssize_t bytes_written =
            ::send(connection.sock, rest.data(), rest.size(), MSG_NOSIGNAL);
        if (bytes_written == -1) {
            const int err = errno;
            if (closed_by_peer(err)) {
                no_answer(query, connection.peer);
            }
            if (err != EINTR) {
                io_error(message, err, deadline);
            }
        } else {
            rest.remove_prefix(bytes_written);
        }
    }
    if (shutdown(connection.sock, SHUT_WR) == -1) {
        const int err = errno;
        if (closed_by_peer(err)) {
            no_answer(query, connection.peer);
        }
        io_error("Cannot shutdown socket to event console", err, deadline);
    }
}

std::string receive_response(const Connection &connection,
                             const std::string &query, Deadline deadline) {
    const std::string message = "Error while reading response";
    std::string response;
    std::array<char, 65536> response_chunk{};
    while (true) {
        check_deadline(message, deadline);
        limit_to_deadline(connection.sock, SO_RCVTIMEO, deadline);
        const ssize_t bytes_read = ::read(
            connection.sock, response_chunk.data(), response_chunk.size());
        if (bytes_read == -1) {
            const int err = errno;
            if (closed_by_peer(err) && response.empty()) {
                no_answer(query, connection.peer);
            }
            if (err != EINTR) {
                io_error(message, err, deadline);
            }
        } else if (bytes_read == 0) {
            break;
        } else {
            response.append(response_chunk.data(), bytes_read);
        }
    }
    // We have read the complete answer, so a failing close() doesn't matter.
    ::close(connection.sock);
    if (response.empty()) {
        no_answer(query, connection.peer);
    }
    return response;
}

struct Event {
    std::string phase;
    State state;
    std::string text;
};

std::vector<Event> parse_events(const std::string &response,
                                const std::string &query) {
    const auto lines = split_lines(response);

    // Get headers
    const auto headers = split_columns(lines.empty() ? "" : lines.front());
    const auto index_of = [&](const std::string &column) {
        const auto pos = std::ranges::find(headers, column);
        if (pos == headers.end()) {
            missing_header(column, query, response);
        }
        return static_cast<size_t>(pos - headers.begin());
    };
    const auto idx_event_phase = index_of("event_phase");
    const auto idx_event_state = index_of("event_state");
    const auto idx_event_text = index_of("event_text");

    // The event console ends every line with a newline, so an answer without
    // one at its end was cut off, e.g. by an event console stopped while
    // answering. Its last row would continue the event text of the row before.
    if (response.back() != '\n') {
        invalid_response("an incomplete last line", query, response);
    }

    // Get data. The event console replaces tabs within the columns by spaces,
    // but it keeps newlines, so a line with too few columns continues the event
    // text of the previous row, which we have requested as the last column.
    std::vector<Event> events;
    for (size_t i = 1; i < lines.size(); i++) {
        const auto row = split_columns(lines[i]);
        if (row.size() < headers.size()) {
            if (events.empty()) {
                invalid_response("an incomplete row", query, response);
            }
            events.back().text.append("\n").append(lines[i]);
            continue;
        }
        const auto state = parse_state(row.at(idx_event_state));
        if (!state) {
            // A valid state has a single digit, so its start is enough.
            invalid_response("an invalid event state '" +
                                 cut_at(row.at(idx_event_state), 20) + "'",
                             query, response);
        }
        events.push_back({std::string{row.at(idx_event_phase)}, *state,
                          std::string{row.at(idx_event_text)}});
    }
    return events;
}

[[noreturn]] void reply_with_events(const std::vector<Event> &events,
                                    const Options &options) {
    if (events.empty()) {
        const std::string app =
            options.application == nullptr
                ? ""
                : (std::string(options.application) + " on ");
        reply_and_exit(
            State::ok,
            "no events for " + app +
                unquote_host_spec(options.host, options.host_spec_quoted));
    }

    std::string worst_row_event_text;
    State worst_state = State::ok;
    int unhandled = 0;
    for (const auto &event : events) {
        if (event.phase == "open" || !options.ignore_acknowledged) {
            if (severity(event.state) >= severity(worst_state)) {
                worst_state = event.state;
                worst_row_event_text = event.text;
            }
        }
        if (event.phase == "open") {
            unhandled++;
        }
    }

    std::cout << worst_state << " - ";

    std::stringstream output;
    output << events.size() << " events (" << unhandled << " unacknowledged)";
    if (!worst_row_event_text.empty() && options.last_log_in_summary) {
        output << ", Last line: ";
        // The core would take everything after a newline as the details.
        for (const char c : worst_row_event_text) {
            output << (c == '\n' ? ' ' : c);
        }
    }
    print_line(output.str());

    if (!worst_row_event_text.empty() && options.last_log_in_details) {
        print_line("Last line: " + worst_row_event_text);
    }

    exit_with(worst_state);
}

}  // namespace

int main(int argc, char **argv) {
    const auto start = Clock::now();
    const auto options = parse_options(argc, argv);
    const Deadline deadline{.start = start, .timeout = options.timeout};
    const auto connection =
        options.remote_host != nullptr
            ? connect_via_tcp(options.remote_host, options.remote_port,
                              deadline)
            : connect_via_unix_socket(options.unixsocket_path, deadline);
    const auto query =
        make_query(options.host, options.host_spec_quoted, options.application);
    send_query(connection, query, deadline);
    const auto response = receive_response(connection, query, deadline);
    reply_with_events(parse_events(response, query), options);
}
