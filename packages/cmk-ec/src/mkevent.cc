// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <arpa/inet.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#include <cctype>
#include <cerrno>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <iostream>
#include <optional>
#include <span>
#include <string>
#include <string_view>
#include <system_error>
#include <utility>

// mkevent finds the event pipe of mkeventd via -P PATH, else via OMD_ROOT, else
// via its own path in a site, e.g. /omd/sites/mysite/bin/mkevent.

namespace {

// NOLINTBEGIN(cppcoreguidelines-avoid-c-arrays,modernize-avoid-c-arrays,cppcoreguidelines-pro-bounds-array-to-pointer-decay,cppcoreguidelines-pro-bounds-constant-array-index,cppcoreguidelines-pro-bounds-pointer-arithmetic,misc-const-correctness)
char *append_str(std::string_view str, char *dest) {
    memcpy(dest, str.data(), str.size());
    return dest + str.size();
}

char *append_int(long n, char *dest) {
    static char digits[] = "0123456789";
    char buf[32];
    buf[31] = 0;
    char *b = buf + 31;
    do {
        *(--b) = digits[n % 10];
    } while ((n /= 10) > 0);
    return append_str(b, dest);
}
// NOLINTEND(cppcoreguidelines-avoid-c-arrays,modernize-avoid-c-arrays,cppcoreguidelines-pro-bounds-array-to-pointer-decay,cppcoreguidelines-pro-bounds-constant-array-index,cppcoreguidelines-pro-bounds-pointer-arithmetic,misc-const-correctness)

std::string default_pipe_path(std::string_view program) {
    // NOLINTNEXTLINE(concurrency-mt-unsafe)
    if (const char *omd_root = getenv("OMD_ROOT")) {
        return std::string{omd_root} + "/tmp/run/mkeventd/events";
    }
    constexpr std::string_view bin_mkevent{"/bin/mkevent"};
    if (program.starts_with("/omd/sites/") && program.ends_with(bin_mkevent)) {
        program.remove_suffix(bin_mkevent.size());
        return std::string{program} + "/tmp/run/mkeventd/events";
    }
    return {};
}

int syslog_priority(int state, bool is_host) {
    if (state == 0) {
        return 5;
    }
    if (is_host) {
        state += 1;  // shift host states in order to map service states
    }
    if (state == 1) {
        return 4;  // warn
    }
    if (state == 3) {
        return 3;  // map UNKNOWN/UNREAD to err
    }
    return 2;  // CRIT/DOWN goes to crit
}

struct Notification {
    std::string remote;  // empty for the local Event Console
    std::string message;
};

// Parses the arguments after -n: FACILITY REMOTE STATE HOST SERVICE MESSAGE SL
// CONTACT [HOST_SL HOST_CONTACT], SERVICE is empty for host notifications.
// Returns nothing for too few arguments.
std::optional<Notification> parse_notification(std::span<char *const> args) {
    if (args.size() < 8) {
        return {};
    }
    const int facility = atoi(args[0]);
    const int state = atoi(args[2]);
    const std::string_view hostname{args[3]};
    const std::string_view service{args[4]};
    const std::string_view text{args[5]};
    const char *sl_text = args[6];
    std::string_view contact{args[7]};

    // If this is a service and sl/contact is unset then we use the values of
    // the host that are coming as HOST_SL and HOST_CONTACT.
    if (std::string_view{sl_text}.starts_with('$') && args.size() > 9) {
        sl_text = args[8];
    }
    if (contact.starts_with('$') && args.size() > 9) {
        contact = args[9];
    }
    if (contact.starts_with('$')) {
        contact = "";
    }

    // NOLINTBEGIN(cppcoreguidelines-avoid-c-arrays,modernize-avoid-c-arrays,cppcoreguidelines-pro-bounds-array-to-pointer-decay,cppcoreguidelines-pro-bounds-pointer-arithmetic)
    char message[8192];
    char *w = message;
    *w++ = '<';
    w = append_int((static_cast<long>(facility) << 3) +
                       syslog_priority(state, service.empty()),
                   w);
    *w++ = '>';
    *w++ = '@';
    w = append_int(std::time(nullptr), w);
    *w++ = ';';
    w = append_int(atoi(sl_text), w);
    *w++ = ';';
    w = append_str(contact, w);
    *w++ = ';';
    *w++ = ' ';
    w = append_str(hostname, w);
    *w++ = ' ';
    w = append_str(service.empty() ? "HOST" : service, w);
    *w++ = ':';
    *w++ = ' ';
    w = append_str(text, w);
    *w = 0;
    return Notification{.remote = args[1], .message = message};
    // NOLINTEND(cppcoreguidelines-avoid-c-arrays,modernize-avoid-c-arrays,cppcoreguidelines-pro-bounds-array-to-pointer-decay,cppcoreguidelines-pro-bounds-pointer-arithmetic)
}

void print_usage() {
    std::cerr << "Usage: mkevent [-P PIPE] 'Text of the message'\n";
}

}  // namespace

int main(int argc, char **argv) {
    auto args = std::span{argv, static_cast<size_t>(argc)};
    if (args.size() < 2) {
        print_usage();
        return 1;
    }
    const std::string_view program{args[0]};

    // Path to pipe can be specified with -P
    std::string path_to_pipe;
    if (std::string_view{args[1]} == "-P") {
        if (args.size() < 4) {
            print_usage();
            return 1;
        }
        path_to_pipe = args[2];
        args = args.subspan(2);
    }
    if (path_to_pipe.empty()) {
        path_to_pipe = default_pipe_path(program);
    }

    // Nagios notification mode is triggered with option -n
    std::string remote;
    std::string message;
    if (auto notification = std::string_view{args[1]} == "-n"
                                ? parse_notification(args.subspan(2))
                                : std::nullopt) {
        remote = std::move(notification->remote);
        message = std::move(notification->message);
    } else {
        // NOLINTBEGIN(cppcoreguidelines-avoid-c-arrays,modernize-avoid-c-arrays,cppcoreguidelines-pro-bounds-array-to-pointer-decay)
        char buffer[8192];
        strncpy(buffer, args[1], sizeof(buffer) - 1);
        message = buffer;
        // NOLINTEND(cppcoreguidelines-avoid-c-arrays,modernize-avoid-c-arrays,cppcoreguidelines-pro-bounds-array-to-pointer-decay)
    }

    // If we have a remote host, send the message to it via syslog.
    int fd = -1;
    if (!remote.empty()) {
        if (std::isdigit(static_cast<unsigned char>(remote[0])) == 0) {
            std::cerr << "ERROR: Please specify the remote host as IPv4 "
                         "address, not '"
                      << remote << "'\n";
            return 1;
        }
        fd = ::socket(AF_INET, SOCK_DGRAM, 0);
        if (fd == -1) {
            std::cerr << "ERROR: could not create socket\n";
            return 1;
        }
        sockaddr_in servaddr{};
        servaddr.sin_family = AF_INET;
        servaddr.sin_addr.s_addr = ::inet_addr(remote.c_str());
        servaddr.sin_port = htons(514);
        ::sendto(fd, message.data(), message.size(), 0,
                 // NOLINTNEXTLINE(cppcoreguidelines-pro-type-reinterpret-cast)
                 reinterpret_cast<struct sockaddr *>(&servaddr),
                 sizeof(servaddr));
    } else {
        // NOLINTNEXTLINE(cppcoreguidelines-pro-type-vararg)
        fd = ::open(path_to_pipe.c_str(), O_WRONLY);
        if (fd == -1) {
            const int err = errno;
            std::cerr << "Cannot open event pipe '" << path_to_pipe
                      << "': " << std::generic_category().message(err) << '\n';
            return 1;
        }
        // Write the message and its newline with a single write(): The Event
        // Console takes each line from its event pipe as a message, and other
        // programs write into the same pipe at the same time. A write() of at
        // most PIPE_BUF bytes to a pipe is atomic, so nothing of theirs can
        // come between our message and its newline then, which would mix up
        // both messages.
        const std::string line = message + '\n';
        // TODO(sp) Handle errors and partial writes.
        if (::write(fd, line.data(), line.size()) < 0) {
        }
    }
    ::close(fd);
    return 0;
}
