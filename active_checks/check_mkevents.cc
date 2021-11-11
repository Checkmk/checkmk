// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// NOTE: We really need <sstream>, IWYU bug?
#include <arpa/inet.h>
#include <netdb.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/un.h>
#include <unistd.h>

#include <cerrno>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <memory>
#include <sstream>
#include <string>
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

[[noreturn]] void reply(State state, const std::string &output) {
    std::cout << state << " - ";
    // Make sure that plugin output does not contain a vertical bar. If that is
    // the case then replace it with a Uniocode "Light vertical bar". Same as in
    // Check_MK.
    for (char i : output) {
        if (i == '|') {
            // \u2758 (utf-8 encoded light vertical bar)
            std::cout << "\xe2\x94\x82";  // NOLINT
        } else {
            std::cout << i;
        }
    }
    std::cout << std::endl;
    exit(static_cast<int>(state));
}

[[noreturn]] void ioError(const std::string &message) {
    reply(State::unknown, message + " (" + strerror(errno) + ")");
}

[[noreturn]] void missingHeader(const std::string &header,
                                const std::string &query,
                                const std::stringstream &response) {
    auto resp = response.str();
    reply(State::unknown,
          "Event console answered with incorrect header (missing " + header +
              ")\nQuery was:\n" + query + "\nReceived " +
              std::to_string(resp.size()) + " byte response:\n" + resp);
}

void usage() {
    reply(
        State::unknown,
        "Usage: check_mkevents [-s SOCKETPATH] [-H REMOTE:PORT] [-a] HOST [APPLICATION]\n"
        " -a    do not take acknowledged events into account.\n"
        " HOST  may be a hostname, and IP address or hostname/IP-address.");
}

std::string prepare_host_match_list(const char *s) {
    const char *scan = s;
    std::string result;
    while (*scan != 0) {
        if (*scan == '/') {
            result += " ";
        } else {
            result += *scan;
        }
        scan++;
    }
    return result;
}

int main(int argc, char **argv) {
    // Parse arguments
    char *host = nullptr;
    char *remote_host = nullptr;
    char *application = nullptr;
    bool ignore_acknowledged = false;
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
            reply(State::unknown, "Unable to resolve remote host address: " +
                                      std::string(remote_hostaddress));
        }

        auto addr_list = reinterpret_cast<struct in_addr **>(he->h_addr_list);
        char remote_hostipaddress[64];
        for (int i = 0; addr_list[i] != nullptr; i++) {
            strncpy(remote_hostipaddress, inet_ntoa(*addr_list[i]),
                    sizeof(remote_hostipaddress));
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

        struct sockaddr_in addr;
        memset(&addr, 0, sizeof(addr));
        addr.sin_family = AF_INET;
        inet_aton(remote_hostipaddress, &addr.sin_addr);
        addr.sin_port = htons(remote_port);

        if (connect(sock, reinterpret_cast<struct sockaddr *>(&addr),
                    sizeof(struct sockaddr_in)) == -1) {
            ioError("Cannot connect to event console at " +
                    std::string(remote_hostipaddress) + ":" +
                    std::to_string(remote_port));
        }

    } else {
        // Get omd environment
        if (unixsocket_path.empty()) {
            char *omd_path = getenv("OMD_ROOT");
            if (omd_path == nullptr) {
                reply(State::unknown,
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
        tv.tv_sec = 3;
        tv.tv_usec = 0;
        if (setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv,
                       sizeof(struct timeval)) == -1) {
            ioError("Cannot set socket reveive timeout");
        }

        struct sockaddr_un addr;
        memset(&addr, 0, sizeof(addr));
        addr.sun_family = AF_UNIX;
        strncpy(addr.sun_path, unixsocket_path.c_str(),
                sizeof(addr.sun_path) - 1);
        addr.sun_path[sizeof(addr.sun_path) - 1] = '\0';

        if (connect(sock, reinterpret_cast<struct sockaddr *>(&addr),
                    sizeof(addr)) == -1) {
            ioError("Cannot connect to event daemon via UNIX socket " +
                    unixsocket_path);
        }
    }

    // Create query message
    std::string query_message;
    query_message += "GET events\n";
    query_message += "Columns: event_phase event_state event_text\n";

    query_message += "Filter: event_host ";
    if (strchr(host, '/') != nullptr) {
        query_message += "in ";
        query_message += prepare_host_match_list(host);
    } else {
        query_message += "=~ ";
        query_message += host;
    }
    query_message += "\nFilter: event_phase in open ack\n";
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

    // Get data
    std::vector<std::vector<std::string> > data;
    while (getline(response_stream, line)) {
        if (line.size() < headers.size()) {
            break;  // broken / empty line
        }
        linestream.str("");
        linestream.clear();
        linestream << line;
        std::vector<std::string> data_line;
        bool has_data = false;
        while (getline(linestream, token, '\t')) {
            has_data = true;
            data_line.push_back(token);
        }
        if (has_data) {
            data.push_back(data_line);
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
        if (strcmp(p, "open") == 0 || !ignore_acknowledged) {
            auto s = static_cast<State>(atoi(it.at(idx_event_state).c_str()));
            if (s == State::unknown) {
                if (worst_state < State::crit) {
                    worst_state = State::unknown;
                    worst_row_event_text = it.at(idx_event_text);
                }
            } else if (s >= worst_state) {
                worst_state = s;
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
        reply(State::ok, "no events for " + app + host);
    }

    std::stringstream output;
    output << count << " events (" << unhandled << " unacknowledged)";
    if (!worst_row_event_text.empty()) {
        output << ", worst state is " << worst_state
               << " (Last line: " << worst_row_event_text << ")";
    }
    reply(worst_state, output.str());
    return 0;  // never reached
}
