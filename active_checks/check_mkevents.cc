// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// NOTE: We really need <sstream>, IWYU bug?
#include <arpa/inet.h>
#include <netdb.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/un.h>
#include <unistd.h>

#include <cerrno>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <optional>
#include <sstream>
#include <string>
#include <string_view>
#include <vector>

enum class State { ok = 0, warn = 1, crit = 2, unknown = 3 };

std::ostream &operator<<(std::ostream &os, const State &state) {
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
std::optional<State> parse_state(const std::string &s) {
    if (s.size() == 1 && s[0] >= '0' && s[0] <= '3') {
        return static_cast<State>(s[0] - '0');
    }
    return {};
}

void print_line(const std::string &output) {
    // Make sure that plugin output does not contain a vertical bar. If that is
    // the case then replace it with a Unicode "Light vertical bar". Same as in
    // Checkmk, which turns it back into a vertical bar for notifications.
    for (char i : output) {
        if (i == '|') {
            // \u2758 (utf-8 encoded light vertical bar)
            std::cout << "\xe2\x9d\x98";  // NOLINT
        } else {
            std::cout << i;
        }
    }
    std::cout << std::endl;
}

[[noreturn]] void exit(State state) { ::exit(static_cast<int>(state)); }

[[noreturn]] void reply_and_exit(State state, const std::string &output) {
    std::cout << state << " - ";
    print_line(output);
    exit(state);
}

[[noreturn]] void ioError(const std::string &message) {
    reply_and_exit(State::unknown, message + " (" + strerror(errno) + ")");
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

[[noreturn]] void invalidResponse(const std::string &problem,
                                  const std::string &query,
                                  const std::stringstream &response) {
    auto resp = response.str();
    reply_and_exit(State::unknown,
                   "Event console answered with " + problem + "\nQuery was:\n" +
                       query + "\nReceived " + std::to_string(resp.size()) +
                       " byte response:\n" + start_of_response(resp));
}

[[noreturn]] void missingHeader(const std::string &header,
                                const std::string &query,
                                const std::stringstream &response) {
    invalidResponse("incorrect header (missing " + header + ")", query,
                    response);
}

// Splits a line of the plain output format at the tabs, keeping empty columns
// like an empty event text at the end of the line.
std::vector<std::string> split_columns(const std::string &line) {
    std::vector<std::string> columns;
    std::string::size_type start = 0;
    while (true) {
        auto end = line.find('\t', start);
        columns.push_back(line.substr(start, end - start));
        if (end == std::string::npos) {
            return columns;
        }
        start = end + 1;
    }
}

void usage() {
    reply_and_exit(
        State::unknown,
        "Usage: check_mkevents [-s SOCKETPATH] [-H REMOTE:PORT] [-a] [-l|-L] [-q] HOST [APPLICATION]\n"
        " -a    do not take acknowledged events into account.\n"
        " -l    show last log message in summary/short output\n"
        " -L    show last log message in details/long output\n"
        " -q    take a backslash in HOST as quoting a following slash or backslash.\n"
        " HOST  may be a hostname, and IP address or hostname/IP-address.");
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
    for (char c : s) {
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
    auto hosts = split_host_spec(spec, quoted);
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

int main(int argc, char **argv) {
    // Parse arguments
    char *host = nullptr;
    char *remote_host = nullptr;
    char *application = nullptr;
    bool ignore_acknowledged = false;
    bool last_log_in_summary = false;
    bool last_log_in_details = false;
    bool host_spec_quoted = false;
    std::string unixsocket_path;

    int argc_count = argc;
    for (int i = 1; i < argc; i++) {
        if (i < argc + 1 && strcmp("-H", argv[i]) == 0) {
            remote_host = argv[i + 1];
            i++;
            argc_count -= 2;
        } else if (i < argc + 1 && strcmp("-s", argv[i]) == 0) {
            unixsocket_path = argv[i + 1];
            i++;
            argc_count -= 2;
        } else if (strcmp("-a", argv[i]) == 0) {
            ignore_acknowledged = true;
            argc_count--;
        } else if (strcmp("-l", argv[i]) == 0) {
            last_log_in_summary = true;
            argc_count--;
        } else if (strcmp("-L", argv[i]) == 0) {
            last_log_in_details = true;
            argc_count--;
        } else if (strcmp("-q", argv[i]) == 0) {
            host_spec_quoted = true;
            argc_count--;
        } else if (argc_count > 2) {
            host = argv[i];
            application = argv[i + 1];
            break;
        } else if (argc_count > 1) {
            host = argv[i];
            break;
        }
    }

    if (host == nullptr) {
        usage();
    }

    int sock;
    if (remote_host != nullptr) {
        char *remote_hostaddress = strtok(remote_host, ":");
        struct hostent *he = gethostbyname(remote_hostaddress);
        if (he == nullptr) {
            reply_and_exit(State::unknown,
                           "Unable to resolve remote host address: " +
                               std::string(remote_hostaddress));
        }

        auto addr_list = reinterpret_cast<struct in_addr **>(he->h_addr_list);
        std::string remote_hostipaddress;
        for (int i = 0; addr_list[i] != nullptr; i++) {
            remote_hostipaddress = std::string{inet_ntoa(*addr_list[i])};
        }

        char *port_str = strtok(nullptr, ":");
        uint16_t remote_port = port_str != nullptr ? atoi(port_str) : 6558;

        sock = ::socket(AF_INET, SOCK_STREAM, 0);
        if (sock == -1) {
            ioError("Cannot create client socket");
        }

        struct timeval tv;
        tv.tv_sec = 10;
        tv.tv_usec = 0;
        if (setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv,
                       sizeof(struct timeval)) == -1) {
            ioError("Cannot set socket reveive timeout");
        }

        sockaddr_in addr{};
        addr.sin_family = AF_INET;
        inet_aton(remote_hostipaddress.c_str(), &addr.sin_addr);
        addr.sin_port = htons(remote_port);

        // NOLINTNEXTLINE(cppcoreguidelines-pro-type-reinterpret-cast)
        if (::connect(sock, reinterpret_cast<struct sockaddr *>(&addr),
                      sizeof(sockaddr_in)) == -1) {
            ioError("Cannot connect to event console at " +
                    remote_hostipaddress + ":" + std::to_string(remote_port));
        }

    } else {
        // Get omd environment
        if (unixsocket_path.empty()) {
            char *omd_path = getenv("OMD_ROOT");
            if (omd_path == nullptr) {
                reply_and_exit(
                    State::unknown,
                    "OMD_ROOT is not set, no socket path is defined.");
            }
            unixsocket_path =
                std::string(omd_path) + "/tmp/run/mkeventd/status";
        }

        sock = ::socket(PF_UNIX, SOCK_STREAM, 0);
        if (sock == -1) {
            ioError("Cannot create client socket");
        }

        struct timeval tv;
        tv.tv_sec = 10;
        tv.tv_usec = 0;
        if (setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv,
                       sizeof(struct timeval)) == -1) {
            ioError("Cannot set socket reveive timeout");
        }

        struct sockaddr_un addr{.sun_family = AF_UNIX, .sun_path = ""};
        unixsocket_path.copy(&addr.sun_path[0], sizeof(addr.sun_path) - 1);
        addr.sun_path[sizeof(addr.sun_path) - 1] = '\0';
        // NOLINTNEXTLINE(cppcoreguidelines-pro-type-reinterpret-cast)
        if (::connect(sock, reinterpret_cast<struct sockaddr *>(&addr),
                      sizeof(addr)) == -1) {
            ioError("Cannot connect to event daemon via UNIX socket " +
                    unixsocket_path);
        }
    }

    // Create query message
    std::string query_message;
    query_message += "GET events\n";
    query_message += "Columns: event_phase event_state event_text\n";

    query_message += host_filter(host, host_spec_quoted);
    query_message += "Filter: event_phase in open ack\n";
    query_message += "OutputFormat: plain\n";

    if (application != nullptr) {
        query_message += "Filter: event_application ~~ ";
        query_message += application;
        query_message += "\n";
    }

    // Send message
    {
        const char *buffer = query_message.c_str();
        size_t bytes_to_write = query_message.size();
        while (bytes_to_write > 0) {
            ssize_t bytes_written = ::write(sock, buffer, bytes_to_write);
            if (bytes_written == -1) {
                ioError("Cannot send query to event console");
            }
            buffer += bytes_written;
            bytes_to_write -= bytes_written;
        }
        if (shutdown(sock, SHUT_WR) == -1) {
            ioError("Cannot shutdown socket to event console");
        }
    }

    // Get response
    std::stringstream response_stream;
    while (true) {
        char response_chunk[4096];
        memset(response_chunk, 0, sizeof(response_chunk));
        ssize_t bytes_read =
            ::read(sock, response_chunk, sizeof(response_chunk));
        if (bytes_read == -1) {
            if (errno != EINTR) {
                ioError("Error while reading response");
            }
        } else if (bytes_read == 0) {
            break;
        } else {
            for (int i = 0; i < bytes_read; i++) {
                if (response_chunk[i] == 0) {
                    response_chunk[i] = ' ';
                }
            }
            response_stream << std::string(response_chunk, bytes_read);
        }
    }
    if (::close(sock) == -1) {
        ioError("Error while closing connection");
    }

    // Start processing data
    std::string line;
    getline(response_stream, line);

    std::stringstream linestream;
    linestream << line;

    // Get headers
    std::string token;
    int idx_event_phase = -1;
    int idx_event_state = -1;
    int idx_event_text = -1;
    int current_index = 0;
    std::vector<std::string> headers;
    while (getline(linestream, token, '\t')) {
        if (strcmp(token.c_str(), "event_phase") == 0) {
            idx_event_phase = current_index;
        } else if (strcmp(token.c_str(), "event_state") == 0) {
            idx_event_state = current_index;
        } else if (strcmp(token.c_str(), "event_text") == 0) {
            idx_event_text = current_index;
        }
        headers.push_back(token);
        current_index++;
    }

    // Basic header validation
    if (idx_event_phase == -1) {
        missingHeader("event_phase", query_message, response_stream);
    }
    if (idx_event_state == -1) {
        missingHeader("event_state", query_message, response_stream);
    }
    if (idx_event_text == -1) {
        missingHeader("event_text", query_message, response_stream);
    }

    // The event console ends every line with a newline, so an answer without
    // one at its end was cut off, e.g. by an event console stopped while
    // answering. Its last row would continue the event text of the row before.
    if (response_stream.str().back() != '\n') {
        invalidResponse("an incomplete last line", query_message,
                        response_stream);
    }

    // Get data. The event console replaces tabs within the columns by spaces,
    // but it keeps newlines, so a line with too few columns continues the last
    // column of the previous row, i.e. the event text we have requested last.
    std::vector<std::vector<std::string> > data;
    while (getline(response_stream, line)) {
        auto row = split_columns(line);
        if (row.size() >= headers.size()) {
            data.push_back(row);
        } else if (data.empty()) {
            invalidResponse("an incomplete row", query_message,
                            response_stream);
        } else {
            data.back().back() += "\n" + line;
        }
    }

    // Generate output
    std::string worst_row_event_text;
    State worst_state = State::ok;
    int count = 0;
    int unhandled = 0;

    for (auto &it : data) {
        count++;
        const char *p = it.at(idx_event_phase).c_str();
        auto s = parse_state(it.at(idx_event_state));
        if (!s) {
            // A valid state has a single digit, so its start is enough.
            invalidResponse("an invalid event state '" +
                                cut_at(it.at(idx_event_state), 20) + "'",
                            query_message, response_stream);
        }
        if (strcmp(p, "open") == 0 || !ignore_acknowledged) {
            if (severity(*s) >= severity(worst_state)) {
                worst_state = *s;
                worst_row_event_text = it.at(idx_event_text);
            }
        }
        if (strcmp(p, "open") == 0) {
            unhandled++;
        }
    }

    if (count == 0) {
        std::string app =
            application == nullptr ? "" : (std::string(application) + " on ");
        reply_and_exit(
            State::ok,
            "no events for " + app + unquote_host_spec(host, host_spec_quoted));
    }

    std::cout << worst_state << " - ";

    std::stringstream output;
    output << count << " events (" << unhandled << " unacknowledged)";
    if (!worst_row_event_text.empty() && last_log_in_summary) {
        output << ", Last line: ";
        // The core would take everything after a newline as the details.
        for (const char c : worst_row_event_text) {
            output << (c == '\n' ? ' ' : c);
        }
    }
    print_line(output.str());

    if (!worst_row_event_text.empty() && last_log_in_details) {
        print_line("Last line: " + worst_row_event_text);
    }

    exit(worst_state);

    return 0;  // never reached
}
