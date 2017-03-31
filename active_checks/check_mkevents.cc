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
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <memory>
#include <sstream>
#include <string>
#include <vector>

using std::string;
using std::stringstream;
using std::vector;

void usage() {
    printf(
        "Usage: check_mkevents [-s SOCKETPATH] [-H REMOTE:PORT] [-a] HOST [APPLICATION]");
    printf("\n -a    do not take into account acknowledged events.\n");
    printf(
        " HOST  may be a hostname, and IP address or hostname/IP-address.\n");
}

string prepare_hostname_regex(const char *s) {
    const char *scan = s;
    string result;
    while (*scan != 0) {
        if (strchr(R"([](){}^$.*+?|\)", *scan) != nullptr) {
            result += R"(\)";
            result += *scan;
        } else if (*scan == '/') {
            result += "|";
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
    char unixsocket_path[1024];
    unixsocket_path[0] = 0;

    int argc_count = argc;
    for (int i = 1; i < argc; i++) {
        if (strcmp("-H", argv[i]) == 0 && i < argc + 1) {
            remote_host = argv[i + 1];
            i++;
            argc_count -= 2;
        } else if (strcmp("-s", argv[i]) == 0 && i < argc + 1) {
            strncpy(unixsocket_path, argv[i + 1], sizeof(unixsocket_path));
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
        exit(3);
    }

    // Get omd environment
    if (unixsocket_path[0] == 0 && remote_host == nullptr) {
        char *omd_path = getenv("OMD_ROOT");
        if (omd_path != nullptr) {
            snprintf(unixsocket_path, sizeof(unixsocket_path),
                     "%s/tmp/run/mkeventd/status", omd_path);
        } else {
            printf(
                "UNKNOWN - OMD_ROOT is not set, no socket path is defined.\n");
            exit(3);
        }
    }

    if (remote_host != nullptr) {
        struct hostent *he;
        struct in_addr **addr_list;
        char *remote_hostaddress = strtok(remote_host, ":");
        if ((he = gethostbyname(remote_hostaddress)) == nullptr) {
            printf("UNKNOWN - Unable to resolve remote host address: %s\n",
                   remote_hostaddress);
            return 3;
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
            printf(
                "UNKNOWN - Cannot connect to event daemon via TCP %s:%d (%s)\n",
                remote_hostipaddress, remote_port, strerror(errno));
            exit(3);
        }
    } else {
        sock = socket(PF_UNIX, SOCK_STREAM, 0);
        if (sock < 0) {
            printf("UNKNOWN - Cannot create client socket: %s\n",
                   strerror(errno));
            exit(3);
        }

        tv.tv_sec = 3;
        setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(struct timeval));

        struct sockaddr_un addr;
        memset(&addr, 0, sizeof(struct sockaddr_un));
        addr.sun_family = AF_UNIX;
        strncpy(addr.sun_path, unixsocket_path, sizeof(addr.sun_path));

        if (0 > connect(sock, reinterpret_cast<struct sockaddr *>(&addr),
                        sizeof(struct sockaddr_un))) {
            printf(
                "UNKNOWN - Cannot connect to event daemon via UNIX socket %s (%s)\n",
                unixsocket_path, strerror(errno));
            exit(3);
        }
    }

    // Create query message
    string query_message;
    query_message += "GET events\nFilter: event_host ";
    if (strchr(host, '/') != nullptr) {
        query_message += "~~ ^(";
        query_message += prepare_hostname_regex(host);
        query_message += ")$";
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
                printf(
                    "UNKNOWN - Cannot send query to event daemon via TCP %s:%d (%s)\n",
                    remote_hostipaddress, remote_port, strerror(errno));
                exit(3);
            }
            buffer += bytes_written;
            bytes_to_write -= bytes_written;
        }
        if (shutdown(sock, SHUT_WR) == -1) {
            printf(
                "UNKNOWN - Cannot shutdown socket to event daemon via TCP %s:%d (%s)\n",
                remote_hostipaddress, remote_port, strerror(errno));
            exit(3);
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
        printf(
            "UNKNOWN - Invalid answer from event daemon\n%s\nQuery was:\n%s\n",
            response_stream.str().c_str(), query_message.c_str());
        exit(3);
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
    int worst_state = 0;
    int count = 0;
    int unhandled = 0;

    for (auto &it : data) {
        count++;
        const char *p = it.at(idx_event_phase).c_str();
        if (strcmp(p, "open") == 0 || !ignore_acknowledged) {
            int s = atoi(it.at(idx_event_state).c_str());
            if (s == 3) {
                if (worst_state < 2) {
                    worst_state = 3;
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

    // make sure that plugin output does not contain a vertical bar. If that is
    // the case then replace it with a Uniocode "Light vertical bar". Same as in
    // Check_MK.
    string text;
    text.reserve(worst_row_event_text.size());
    for (char i : worst_row_event_text) {
        if (i == '|') {
            // \u2758 (utf-8 encoded light vertical bar)
            text += "\xe2\x94\x82";  // NOLINT
        } else {
            text += i;
        }
    }

    if (count == 0 && application != nullptr) {
        printf("OK - no events for %s on host %s\n", application, host);
    } else if (count == 0) {
        printf("OK - no events for %s\n", host);
    } else {
        const char *state_text =
            worst_state == 0
                ? "OK"
                : worst_state == 1 ? "WARN"
                                   : worst_state == 2 ? "CRIT" : "UNKNOWN";
        printf("%s - %d events (%d unacknowledged)", state_text, count,
               unhandled);
        if (text.length() > 0) {
            printf(", worst state is %s (Last line: %s)", state_text,
                   text.c_str());
        }
        printf("\n");
    }
    return worst_state;
}
