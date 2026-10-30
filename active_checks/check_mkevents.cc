// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <arpa/inet.h>
#include <netdb.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/un.h>
#include <unistd.h>

#include <algorithm>
#include <array>
#include <cctype>
#include <cerrno>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <optional>
#include <span>
#include <sstream>  // IWYU pragma: keep
#include <string>
#include <string_view>
#include <system_error>
#include <utility>
#include <vector>

namespace {

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

[[noreturn]] void exit_with(State state) {
    std::exit(static_cast<int>(state));  // NOLINT(concurrency-mt-unsafe)
}

[[noreturn]] void reply_and_exit(State state, const std::string &output) {
    std::cout << state << " - ";
    print_line(output);
    exit_with(state);
}

constexpr int timeout_seconds = 20;

[[noreturn]] void io_error(const std::string &message) {
    // All our sockets have timeouts, which expire with one of these errors.
    const auto err = errno;
    const std::string reason =
        err == EAGAIN || err == EWOULDBLOCK || err == EINPROGRESS
            ? "timeout after " + std::to_string(timeout_seconds) + " seconds"
            : std::generic_category().message(err);
    reply_and_exit(State::unknown, message + " (" + reason + ")");
}

// The exchange with the event console, from connecting to reading the whole
// answer, shares one deadline, so the timeouts of its steps don't add up.
std::chrono::steady_clock::time_point deadline() {
    static const auto deadline = std::chrono::steady_clock::now() +
                                 std::chrono::seconds{timeout_seconds};
    return deadline;
}

// A socket timeout only expires while a call waits, so a peer that keeps
// sending or reading would keep a loop of such calls going past the deadline.
// That's why the loop checks the deadline before each call, reporting a timeout
// with the message of the call.
void check_deadline(const std::string &message) {
    if (std::chrono::steady_clock::now() >= deadline()) {
        reply_and_exit(State::unknown, message + " (timeout after " +
                                           std::to_string(timeout_seconds) +
                                           " seconds)");
    }
}

// Limits the next blocking call on the socket to the time left until the
// deadline, via the timeout option SO_RCVTIMEO for receiving or SO_SNDTIMEO for
// sending. Linux uses the send timeout for connect(), too.
void limit_to_deadline(int sock, int option) {
    using std::chrono::duration_cast;
    using std::chrono::microseconds;
    using std::chrono::seconds;
    // A timeout of zero would mean no timeout at all.
    const auto left =
        std::max(duration_cast<microseconds>(deadline() -
                                             std::chrono::steady_clock::now()),
                 microseconds{1});
    const auto left_seconds = duration_cast<seconds>(left);
    const timeval tv{.tv_sec = left_seconds.count(),
                     .tv_usec = (left - left_seconds).count()};
    if (setsockopt(sock, SOL_SOCKET, option, &tv, sizeof(tv)) == -1) {
        io_error("Cannot set socket timeout");
    }
}

int create_socket(int domain) {
    const int sock = ::socket(domain, SOCK_STREAM, 0);
    if (sock == -1) {
        io_error("Cannot create client socket");
    }
    limit_to_deadline(sock, SO_SNDTIMEO);  // for connect()
    return sock;
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

[[noreturn]] void no_answer(const std::string &query) {
    reply_and_exit(State::unknown,
                   "Event console closed the connection without answering, "
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
        "Usage: check_mkevents [-s SOCKETPATH] [-H REMOTE[:PORT]] [-a] [-l] [-L] [-q] [--] HOST [APPLICATION]\n"
        " -s    connect via this UNIX socket, by default $OMD_ROOT/tmp/run/mkeventd/status.\n"
        " -H    connect via TCP, e.g. to myhost:6558.\n"
        " -a    do not take acknowledged events into account.\n"
        " -l    show last log message in summary/short output.\n"
        " -L    show last log message in details/long output.\n"
        " -q    take a backslash in HOST as quoting a following slash or backslash.\n"
        " --    end the options, e.g. for a HOST starting with a dash.\n"
        " HOST  may be a hostname, an IP address or hostname/IP-address.");
}

// Parses a port number from 1 to 65535, leading zeros don't count.
std::optional<uint16_t> parse_port(const std::string &s) {
    if (!std::ranges::all_of(
            s, [](unsigned char c) { return std::isdigit(c) != 0; })) {
        return {};
    }
    const auto digits = s.substr(std::min(s.find_first_not_of('0'), s.size()));
    if (digits.empty() || digits.size() > 5) {
        return {};
    }
    const auto port = std::stoul(digits);  // can't throw for at most 5 digits
    if (port > 65535) {
        return {};
    }
    return static_cast<uint16_t>(port);
}

// Parses a remote address like "myhost:6558", the port is optional and may be
// empty.
std::pair<std::string, uint16_t> parse_remote(const std::string &remote) {
    const auto colon = std::min(remote.find(':'), remote.size());
    const auto address = remote.substr(0, colon);
    const auto port = colon + 1 >= remote.size()
                          ? std::optional<uint16_t>{6558}
                          : parse_port(remote.substr(colon + 1));
    if (address.empty() || !port) {
        reply_and_exit(State::unknown, "Invalid remote address '" + remote +
                                           "', expected HOST[:PORT]");
    }
    return {address, *port};
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
    std::string unixsocket_path;
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
    while ((option = getopt(argc, argv, "+s:H:alLq")) != -1) {
        switch (option) {
            case 's':
                options.unixsocket_path = optarg;
                break;
            case 'H':
                options.remote_host = optarg;
                break;
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

int connect_via_tcp(const std::string &remote) {
    const auto [remote_hostaddress, remote_port] = parse_remote(remote);
    // NOLINTNEXTLINE(concurrency-mt-unsafe)
    const struct hostent *he = gethostbyname(remote_hostaddress.c_str());
    if (he == nullptr) {
        reply_and_exit(
            State::unknown,
            "Unable to resolve remote host address: " + remote_hostaddress);
    }

    // NOLINTNEXTLINE(cppcoreguidelines-pro-type-reinterpret-cast)
    auto *addr_list = reinterpret_cast<struct in_addr **>(he->h_addr_list);
    std::string remote_hostipaddress;
    // NOLINTBEGIN(cppcoreguidelines-pro-bounds-pointer-arithmetic,concurrency-mt-unsafe)
    for (int i = 0; addr_list[i] != nullptr; i++) {
        remote_hostipaddress = std::string{inet_ntoa(*addr_list[i])};
    }
    // NOLINTEND(cppcoreguidelines-pro-bounds-pointer-arithmetic,concurrency-mt-unsafe)

    const int sock = create_socket(AF_INET);

    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    inet_aton(remote_hostipaddress.c_str(), &addr.sin_addr);
    addr.sin_port = htons(remote_port);

    // NOLINTNEXTLINE(cppcoreguidelines-pro-type-reinterpret-cast)
    if (::connect(sock, reinterpret_cast<struct sockaddr *>(&addr),
                  sizeof(sockaddr_in)) == -1) {
        io_error("Cannot connect to event console at " + remote_hostipaddress +
                 ":" + std::to_string(remote_port));
    }
    return sock;
}

int connect_via_unix_socket(std::string unixsocket_path) {
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

    const int sock = create_socket(AF_UNIX);
    // NOLINTNEXTLINE(cppcoreguidelines-pro-type-reinterpret-cast)
    if (::connect(sock, reinterpret_cast<struct sockaddr *>(&addr),
                  sizeof(addr)) == -1) {
        io_error("Cannot connect to event daemon via UNIX socket " +
                 unixsocket_path);
    }
    return sock;
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

void send_query(int sock, const std::string &query) {
    const std::string message = "Cannot send query to event console";
    std::string_view rest{query};
    while (!rest.empty()) {
        check_deadline(message);
        limit_to_deadline(sock, SO_SNDTIMEO);
        // Report a closed connection instead of dying from SIGPIPE.
        const ssize_t bytes_written =
            ::send(sock, rest.data(), rest.size(), MSG_NOSIGNAL);
        if (bytes_written == -1) {
            if (closed_by_peer(errno)) {
                no_answer(query);
            }
            if (errno != EINTR) {
                io_error(message);
            }
        } else {
            rest.remove_prefix(bytes_written);
        }
    }
    if (shutdown(sock, SHUT_WR) == -1) {
        if (closed_by_peer(errno)) {
            no_answer(query);
        }
        io_error("Cannot shutdown socket to event console");
    }
}

std::string receive_response(int sock, const std::string &query) {
    const std::string message = "Error while reading response";
    std::string response;
    std::array<char, 65536> response_chunk{};
    while (true) {
        check_deadline(message);
        limit_to_deadline(sock, SO_RCVTIMEO);
        const ssize_t bytes_read =
            ::read(sock, response_chunk.data(), response_chunk.size());
        if (bytes_read == -1) {
            if (closed_by_peer(errno) && response.empty()) {
                no_answer(query);
            }
            if (errno != EINTR) {
                io_error(message);
            }
        } else if (bytes_read == 0) {
            break;
        } else {
            response.append(response_chunk.data(), bytes_read);
        }
    }
    // We have read the complete answer, so a failing close() doesn't matter.
    ::close(sock);
    if (response.empty()) {
        no_answer(query);
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
    const auto options = parse_options(argc, argv);
    const int sock = options.remote_host != nullptr
                         ? connect_via_tcp(options.remote_host)
                         : connect_via_unix_socket(options.unixsocket_path);
    const auto query =
        make_query(options.host, options.host_spec_quoted, options.application);
    send_query(sock, query);
    const auto response = receive_response(sock, query);
    reply_with_events(parse_events(response, query), options);
}
