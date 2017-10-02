// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

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
#include <sstream>  // IWYU pragma: keep
#include <string>
#include <vector>

using std::cout;
using std::endl;
using std::ostream;
using std::string;
using std::stringstream;
using std::to_string;
using std::vector;

enum class State { ok = 0, warn = 1, crit = 2, unknown = 3 };

ostream &operator<<(ostream &os, const State &state) {
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

[[noreturn]] void reply(State state, const string &output) {
    cout << state << " - ";
    // Make sure that plugin output does not contain a vertical bar. If that is
    // the case then replace it with a Uniocode "Light vertical bar". Same as in
    // Check_MK.
    for (char i : output) {
        if (i == '|') {
            // \u2758 (utf-8 encoded light vertical bar)
            cout << "\xe2\x94\x82";  // NOLINT
        } else {
            cout << i;
        }
    }
    cout << endl;
    exit(static_cast<int>(state));
}

[[noreturn]] void ioError(const string &message) {
    reply(State::unknown, message + " (" + strerror(errno) + ")");
}

[[noreturn]] void tcpError(const string &message, const string &addr,
                           int port) {
    ioError(message + " to event daemon via TCP " + addr + ":" +
            to_string(port));
}

void usage() {
    reply(
        State::unknown,
        "Usage: check_mkevents [-s SOCKETPATH] [-H REMOTE:PORT] [-a] HOST [APPLICATION]\n"
        " -a    do not take into account acknowledged events.\n"
        " HOST  may be a hostname, and IP address or hostname/IP-address.");
}

string prepare_host_match_list(const char *s) {
    const char *scan = s;
    string result;
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
    char remote_hostipaddress[64];
    int remote_port = 6558;
    char *application = nullptr;
    bool ignore_acknowledged = false;
    string unixsocket_path;

    int argc_count = argc;
    for (int i = 1; i < argc; i++) {
        if (strcmp("-H", argv[i]) == 0 && i < argc + 1) {
            remote_host = argv[i + 1];
            i++;
            argc_count -= 2;
        } else if (strcmp("-s", argv[i]) == 0 && i < argc + 1) {
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

    // Get omd environment
    if (unixsocket_path.empty() && remote_host == nullptr) {
        char *omd_path = getenv("OMD_ROOT");
        if (omd_path == nullptr) {
            reply(State::unknown,
                  "OMD_ROOT is not set, no socket path is defined.");
        }
        unixsocket_path = string(omd_path) + "/tmp/run/mkeventd/status";
    }

    if (remote_host != nullptr) {
        struct hostent *he;
        struct in_addr **addr_list;
        char *remote_hostaddress = strtok(remote_host, ":");
        if ((he = gethostbyname(remote_hostaddress)) == nullptr) {
            reply(State::unknown,
                  "Unable to resolve remote host address: " +
                      string(remote_hostaddress));
        }
        addr_list = reinterpret_cast<struct in_addr **>(he->h_addr_list);
        for (int i = 0; addr_list[i] != nullptr; i++) {
            strncpy(remote_hostipaddress, inet_ntoa(*addr_list[i]),
                    sizeof(remote_hostipaddress));
        }

        char *port_str = strtok(nullptr, ":");
        if (port_str != nullptr) {
            remote_port = atoi(port_str);
        }
    }

    // Create socket and setup connection
    int sock;
    struct timeval tv;
    if (remote_host != nullptr) {
        sock = socket(AF_INET, SOCK_STREAM, 0);
        tv.tv_sec = 10;
        setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(struct timeval));
        // Right now, there is no send timeout..
        // setsockopt(sock, SOL_SOCKET, SO_SNDTIMEO, (struct timeval *)&tv,
        // sizeof(struct timeval));

        struct sockaddr_in addr;
        memset(&addr, 0, sizeof(addr));
        addr.sin_family = AF_INET;
        inet_aton(remote_hostipaddress, &addr.sin_addr);
        addr.sin_port = htons(remote_port);

        if (0 > connect(sock, reinterpret_cast<struct sockaddr *>(&addr),
                        sizeof(struct sockaddr_in))) {
            tcpError("Cannot connect", remote_hostipaddress, remote_port);
        }
    } else {
        sock = socket(PF_UNIX, SOCK_STREAM, 0);
        if (sock < 0) {
            ioError("Cannot create client socket");
        }

        tv.tv_sec = 3;
        setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(struct timeval));

        struct sockaddr_un addr;
        memset(&addr, 0, sizeof(struct sockaddr_un));
        addr.sun_family = AF_UNIX;
        strncpy(addr.sun_path, unixsocket_path.c_str(), sizeof(addr.sun_path));

        if (0 > connect(sock, reinterpret_cast<struct sockaddr *>(&addr),
                        sizeof(struct sockaddr_un))) {
            ioError("Cannot connect to event daemon via UNIX socket " +
                    unixsocket_path);
        }
    }

    // Create query message
    string query_message;
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
            ssize_t bytes_written = write(sock, buffer, bytes_to_write);
            if (bytes_written == -1) {
                tcpError("Cannot send query", remote_hostipaddress,
                         remote_port);
            }
            buffer += bytes_written;
            bytes_to_write -= bytes_written;
        }
        if (shutdown(sock, SHUT_WR) == -1) {
            tcpError("Cannot shutdown socket", remote_hostipaddress,
                     remote_port);
        }
    }

    // Get response
    char response_chunk[4096];
    memset(response_chunk, 0, sizeof(response_chunk));
    stringstream response_stream;
    ssize_t read_length;
    while (0 <
           (read_length = read(sock, response_chunk, sizeof(response_chunk)))) {
        // replace binary 0 in response with space
        for (int i = 0; i < read_length; i++) {
            if (response_chunk[i] == 0) {
                response_chunk[i] = ' ';
            }
        }
        response_stream << string(response_chunk, read_length);
        memset(response_chunk, 0, sizeof(response_chunk));
    }
    close(sock);

    // Start processing data
    string line;
    getline(response_stream, line);

    stringstream linestream;
    linestream << line;

    // Get headers
    string token;
    int idx_event_phase = -1;
    int idx_event_state = -1;
    int idx_event_text = -1;
    int current_index = 0;
    vector<string> headers;
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
    if (idx_event_phase == -1 || idx_event_state == -1 ||
        idx_event_text == -1) {
        reply(State::unknown,
              "Invalid answer from event daemon\n" + response_stream.str() +
                  "\nQuery was:\n" + query_message);
    }

    // Get data
    vector<vector<string> > data;
    while (getline(response_stream, line)) {
        if (line.size() < headers.size()) {
            break;  // broken / empty line
        }
        linestream.str("");
        linestream.clear();
        linestream << line;
        vector<string> data_line;
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
    string worst_row_event_text;
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
        string app =
            application == nullptr ? "" : (string(application) + " on ");
        reply(State::ok, "no events for " + app + host);
    }

    stringstream output;
    output << count << " events (" << unhandled << " unacknowledged)";
    if (!worst_row_event_text.empty()) {
        output << ", worst state is " << worst_state
               << " (Last line: " << worst_row_event_text << ")";
    }
    reply(worst_state, output.str());
    return 0;  // never reached
}
