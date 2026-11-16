// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <arpa/inet.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <unistd.h>

#include <cctype>
#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <iostream>
#include <string>

/* Methods for specified the path to the pipe of
   mkeventd:

   1. Run mkevent within the environment of a
      OMD site -> will find pipe itself

   2. Specify pipe with -P PATH before message

   3. Run mkeventd with absolute path in a site,
      e.g. /omd/sites/mysite/bin/mkevent -> will
      find pipe itself

   4. Uses hardcoded path /var/run/mkeventd.pipe.

*/

int file_exists(const std::string &path) {
    struct stat st;
    return static_cast<int>(stat(path.c_str(), &st) == 0);
}

// Like with the old message buffer of 8192 bytes, including the NUL
constexpr std::string::size_type max_message_length = 8191;

// Is the byte a continuation byte (10xxxxxx) of a UTF-8 character?
bool is_continuation_byte(char byte) {
    return (static_cast<unsigned char>(byte) & 0xC0U) == 0x80U;
}

// The length of the message cut off after at most max_message_length bytes,
// but not within a UTF-8 character
std::string::size_type truncated_length(const std::string &message) {
    if (message.size() <= max_message_length) {
        return message.size();
    }
    // Cut off the start of a split character, too, which has at most 4 bytes.
    auto length = max_message_length;
    for (int i = 0; i < 3 && is_continuation_byte(message[length]); ++i) {
        --length;
    }
    return length;
}

int main(int argc, char **argv) {
    if (argc < 2) {
        std::cerr << "Usage: mkevent [-P PIPE] 'Text of the messsage'"
                  << std::endl;
        exit(1);
    }

    std::string path_to_pipe;

    /* Path to pipe can be specified with -P */
    if (argc > 2 && (strcmp(argv[1], "-P") == 0)) {
        path_to_pipe = argv[2];
        argc -= 2;
        argv += 2;
    }

    if (path_to_pipe.empty()) {
        if (const char *omd_root = getenv("OMD_ROOT")) {
            path_to_pipe = std::string(omd_root) + "/tmp/run/mkeventd/events";
        } else if (strncmp(argv[0], "/omd/sites/", 11) == 0) {
            // cut off /bin/mkevent
            path_to_pipe = std::string(argv[0], strlen(argv[0]) - 12) +
                           "/tmp/run/mkeventd/events";
        }
    }

    /* Nagios notification mode is triggered with option -n */
    std::string message;
    const char *remote = "";

    if (argc > 9 && (strcmp(argv[1], "-n") == 0)) {
        /* Arguments: -n FACILITY REMOTE STATE HOST SERVICE MESSAGE */
        /* SERVICE is empty for host notification */
        int facility = atoi(argv[2]);
        remote = argv[3];
        int state = atoi(argv[4]);
        char *hostname = argv[5];
        char *service = argv[6];
        char *text = argv[7];
        char *sl_text = argv[8];
        const char *contact = argv[9];

        /* If this is a service and sl/contact is unset then we use
           the values of the host that are coming as arg 10 and 11 */
        if (sl_text[0] == '$' && argc > 11) {
            sl_text = argv[10];
        }
        if (contact[0] == '$' && argc > 11) {
            contact = argv[11];
        }

        int sl = atoi(sl_text);
        if (contact[0] == '$') {
            contact = "";
        }

        int priority;
        if (state == 0) {
            priority = 5;
        } else {
            if (service[0] == 0) {
                state += 1;  // shift host states in order to map service states
            }
            if (state == 1) {
                priority = 4;  // warn
            } else if (state == 3) {
                priority = 3;  // map UNKNOWN/UNREAD to err
            } else {
                priority = 2;  // CRIT/DOWN goes to crit
            }
        }

        message =
            "<" +
            std::to_string((static_cast<long>(facility) << 3) + priority) +
            ">@" + std::to_string(time(nullptr)) + ";" + std::to_string(sl) +
            ";";
        message += contact;
        message += "; ";
        message += hostname;
        message += " ";
        message += service[0] != 0 ? service : "HOST";
        message += ": ";
        message += text;
    } else {
        message = argv[1];
    }
    message.resize(truncated_length(message));

    /* If we have a remote host, send the message via syslog to the remote host. */
    int fd;
    if (remote[0] != 0) {
        if (isdigit(remote[0]) == 0) {
            std::cerr
                << "ERROR: Please specify the remote host as IPv4 address, not '"
                << remote << "'" << std::endl;
            exit(1);
        }
        fd = ::socket(AF_INET, SOCK_DGRAM, 0);
        if (fd == -1) {
          std::cerr << "ERROR: could not create socket" << std::endl;
          exit(1);
        }
        sockaddr_in servaddr{};
        servaddr.sin_family = AF_INET;
        servaddr.sin_addr.s_addr = inet_addr(remote);
        servaddr.sin_port = htons(514);
        ::sendto(fd, message.data(), message.size(), 0,
                 // NOLINTNEXTLINE(cppcoreguidelines-pro-type-reinterpret-cast)
                 reinterpret_cast<struct sockaddr *>(&servaddr),
                 sizeof(servaddr));
    } else {
        fd = open(path_to_pipe.c_str(), O_WRONLY);
        if (fd < 0) {
            int errno_saved = errno;
            std::cerr << "Cannot open event pipe '" << path_to_pipe
                      << "': " << strerror(errno_saved) << std::endl;
            exit(1);
        }
        // TODO(sp) Handle errors and partial writes.
        if (::write(fd, message.data(), message.size()) < 0 ||
            ::write(fd, "\n", 1) < 0) {
        }
    }
    ::close(fd);
    return 0;
}
