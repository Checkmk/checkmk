// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <arpa/inet.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <poll.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <unistd.h>

#include <cerrno>
#include <charconv>
#include <chrono>
#include <csignal>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <iostream>
#include <memory>
#include <optional>
#include <span>
#include <sstream>
#include <string>
#include <string_view>
#include <system_error>
#include <thread>
#include <utility>

// mkevent finds the event pipe of mkeventd via -P PATH, else via OMD_ROOT, else
// via its own path in a site, e.g. /omd/sites/mysite/bin/mkevent.

namespace {

// Like those of notification plug-ins: The spooler retries temporary errors.
enum class ExitCode {
    success = 0,
    temporary_error = 1,
    permanent_error = 2,
};

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

ExitCode send_via_syslog(const std::string &remote,
                         const std::string &message) {
    sockaddr_in servaddr{};
    servaddr.sin_family = AF_INET;
    servaddr.sin_port = htons(514);
    // Like the GUI, only the usual form, not e.g. 010.0.0.1 like inet_aton()
    if (::inet_pton(AF_INET, remote.c_str(), &servaddr.sin_addr) != 1) {
        std::cerr << "Cannot send to remote host '" << remote
                  << "': Not an IPv4 address\n";
        return ExitCode::permanent_error;
    }
    const int fd = ::socket(AF_INET, SOCK_DGRAM, 0);
    if (fd == -1) {
        const int err = errno;
        std::cerr << "Cannot create socket: "
                  << std::generic_category().message(err) << '\n';
        return ExitCode::temporary_error;
    }
    const ssize_t bytes_sent = ::sendto(
        fd, message.data(), message.size(), 0,
        // NOLINTNEXTLINE(cppcoreguidelines-pro-type-reinterpret-cast)
        reinterpret_cast<struct sockaddr *>(&servaddr), sizeof(servaddr));
    const int err = errno;
    ::close(fd);
    if (bytes_sent == -1) {
        std::cerr << "Cannot send to remote host '" << remote
                  << "': " << std::generic_category().message(err) << '\n';
        // EACCES comes from a broadcast address or a security policy.
        return err == EACCES ? ExitCode::permanent_error
                             : ExitCode::temporary_error;
    }
    return ExitCode::success;
}

// How long mkevent waits for a reader of the event pipe, and with a
// notification, also for room in it: Well below the timeout of notification
// plug-ins, as mkevent would outlive its killed plug-in and deliver the
// notification twice.
constexpr std::chrono::milliseconds default_delivery_timeout{5000};

// Whether to give up on a full event pipe: The spooler retries a notification,
// but nobody retries a plain message.
enum class WaitWhileFull { until_deadline, without_deadline };

// The delivery timeout, which only tests change
std::chrono::milliseconds delivery_timeout() {
    // NOLINTNEXTLINE(concurrency-mt-unsafe)
    const char *value = getenv("MKEVENT_DELIVERY_TIMEOUT_MS");
    if (value == nullptr) {
        return default_delivery_timeout;
    }
    const std::string_view text{value};
    const char *text_end = std::to_address(text.end());
    std::chrono::milliseconds::rep ms{};
    const auto [end, ec] =
        std::from_chars(std::to_address(text.begin()), text_end, ms);
    // At most an hour, so that computing the deadline can't overflow.
    if (ec != std::errc{} || end != text_end || ms < 0 || ms > 3600000) {
        return default_delivery_timeout;
    }
    return std::chrono::milliseconds{ms};
}

// E.g. "5 seconds" or "0.1 seconds"
std::string seconds_text(std::chrono::milliseconds duration) {
    std::ostringstream os;
    os << std::chrono::duration<double>{duration}.count() << " seconds";
    return os.str();
}

// Why opening the path failed with ENXIO: 0 for a FIFO nobody reads, ENXIO
// e.g. for a UNIX socket, or the error of looking it up again
int cause_of_enxio(const std::string &path) {
    struct stat st{};
    if (::stat(path.c_str(), &st) == -1) {
        return errno;
    }
    return S_ISFIFO(st.st_mode) ? 0 : ENXIO;
}

using Deadline = std::chrono::steady_clock::time_point;

// Errors of opening the event pipe which retrying can't help with
bool is_permanent_open_error(int err) {
    switch (err) {
        case EACCES:
        case EISDIR:
        case ELOOP:
        case ENAMETOOLONG:
        case ENOTDIR:
        case ENXIO:  // for anything but a FIFO, e.g. a UNIX socket
        case EPERM:
        case EROFS:
            return true;
        default:
            return false;
    }
}

// The opened event pipe, or -1 and the exit code for failing to open it
struct OpenedPipe {
    int fd;
    ExitCode exit_code;
};

// Opens the event pipe for writing, or reports why it can't. Unlike a plain
// open(), it gives up if nobody reads the pipe by the deadline.
OpenedPipe open_event_pipe(const std::string &path, Deadline deadline,
                           std::chrono::milliseconds timeout) {
    auto fail = [&path](std::string_view reason,
                        ExitCode exit_code) -> OpenedPipe {
        std::cerr << "Cannot open event pipe '" << path << "': " << reason
                  << '\n';
        return OpenedPipe{.fd = -1, .exit_code = exit_code};
    };
    while (true) {
        // Without a reader, opening with O_NONBLOCK fails with ENXIO.
        // NOLINTNEXTLINE(cppcoreguidelines-pro-type-vararg)
        const int fd = ::open(path.c_str(), O_WRONLY | O_NONBLOCK);
        if (fd != -1) {
            auto close_and_fail = [fd, &fail](std::string_view reason,
                                              ExitCode exit_code) {
                ::close(fd);
                return fail(reason, exit_code);
            };
            // Writing to a regular file would overwrite it from its start.
            struct stat st{};
            if (::fstat(fd, &st) == -1) {
                return close_and_fail(std::generic_category().message(errno),
                                      ExitCode::temporary_error);
            }
            if (!S_ISFIFO(st.st_mode)) {
                return close_and_fail("Not a FIFO", ExitCode::permanent_error);
            }
            return OpenedPipe{.fd = fd, .exit_code = ExitCode::success};
        }
        int err = errno;
        if (err == ENXIO) {
            err = cause_of_enxio(path);
        }
        if (err != 0) {
            return fail(std::generic_category().message(err),
                        is_permanent_open_error(err)
                            ? ExitCode::permanent_error
                            : ExitCode::temporary_error);
        }
        if (std::chrono::steady_clock::now() >= deadline) {
            return fail("Nobody read it within " + seconds_text(timeout) +
                            ". Is the Event Console running?",
                        ExitCode::temporary_error);
        }
        std::this_thread::sleep_for(std::chrono::milliseconds{100});
    }
}

// Waits for room in the full pipe or for its reader to vanish. Returns 0 then,
// ETIMEDOUT at the deadline, if any, or the error of poll().
int wait_until_writable(int fd, std::optional<Deadline> deadline) {
    while (true) {
        int timeout_ms = -1;  // as long as it takes
        if (deadline) {
            const auto left = std::chrono::ceil<std::chrono::milliseconds>(
                *deadline - std::chrono::steady_clock::now());
            if (left <= std::chrono::milliseconds::zero()) {
                return ETIMEDOUT;
            }
            timeout_ms = static_cast<int>(left.count());
        }
        pollfd pfd{.fd = fd, .events = POLLOUT, .revents = 0};
        const int ready = ::poll(&pfd, 1, timeout_ms);
        if (ready > 0) {
            return 0;
        }
        if (ready == -1 && errno != EINTR) {
            return errno;
        }
    }
}

ExitCode write_to_pipe(const std::string &path, const std::string &message,
                       std::chrono::milliseconds timeout,
                       WaitWhileFull wait_while_full) {
    // Report a vanished reader instead of getting killed by SIGPIPE.
    (void)std::signal(SIGPIPE, SIG_IGN);
    const auto deadline = std::chrono::steady_clock::now() + timeout;
    const auto [fd, open_exit_code] = open_event_pipe(path, deadline, timeout);
    if (fd == -1) {
        return open_exit_code;
    }
    auto fail = [&path, fd](std::string_view reason) {
        std::cerr << "Cannot write to event pipe '" << path << "': " << reason
                  << '\n';
        ::close(fd);
        return ExitCode::temporary_error;
    };
    // Write the line at once, so that it doesn't get mixed up with the lines of
    // other writers. That's guaranteed only up to PIPE_BUF bytes, see pipe(7),
    // so once a part of a longer line is in, wait for room without a deadline.
    const std::string line = message + "\n";
    std::string_view rest{line};
    while (!rest.empty()) {
        const ssize_t bytes_written = ::write(fd, rest.data(), rest.size());
        if (bytes_written != -1) {
            rest.remove_prefix(static_cast<size_t>(bytes_written));
            continue;
        }
        const int err = errno;
        if (err == EINTR) {
            continue;
        }
        if (err != EAGAIN) {
            return fail(std::generic_category().message(err));
        }
        const bool started = rest.size() < line.size();
        const bool with_deadline =
            wait_while_full == WaitWhileFull::until_deadline && !started;
        const int wait_err = wait_until_writable(
            fd, with_deadline ? std::optional{deadline} : std::nullopt);
        if (wait_err == ETIMEDOUT) {
            return fail("Still full after " + seconds_text(timeout) +
                        ". Is the Event Console overloaded?");
        }
        if (wait_err != 0) {
            return fail(std::generic_category().message(wait_err));
        }
    }
    ::close(fd);
    return ExitCode::success;
}

void print_usage() {
    std::cerr
        << "Usage: mkevent [-P PIPE] 'Text of the message'\n"
           "       mkevent [-P PIPE] -n FACILITY REMOTE STATE HOST SERVICE "
           "MESSAGE SL CONTACT [HOST_SL HOST_CONTACT]\n";
}

}  // namespace

int main(int argc, char **argv) {
    auto args = std::span{argv, static_cast<size_t>(argc)};
    if (args.size() < 2) {
        print_usage();
        return static_cast<int>(ExitCode::permanent_error);
    }
    const std::string_view program{args[0]};

    // Path to pipe can be specified with -P
    std::string path_to_pipe;
    if (std::string_view{args[1]} == "-P") {
        if (args.size() < 4) {
            print_usage();
            return static_cast<int>(ExitCode::permanent_error);
        }
        path_to_pipe = args[2];
        args = args.subspan(2);
    }
    if (path_to_pipe.empty()) {
        path_to_pipe = default_pipe_path(program);
    }

    // Nagios notification mode is triggered with option -n
    const bool is_notification = std::string_view{args[1]} == "-n";
    std::string remote;
    std::string message;
    if (is_notification) {
        auto notification = parse_notification(args.subspan(2));
        if (!notification) {
            print_usage();
            return static_cast<int>(ExitCode::permanent_error);
        }
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
    if (!remote.empty()) {
        return static_cast<int>(send_via_syslog(remote, message));
    }
    if (path_to_pipe.empty()) {
        std::cerr << "Cannot find event pipe: Use -P PIPE outside of a site\n";
        return static_cast<int>(ExitCode::permanent_error);
    }
    return static_cast<int>(
        write_to_pipe(path_to_pipe, message, delivery_timeout(),
                      is_notification ? WaitWhileFull::until_deadline
                                      : WaitWhileFull::without_deadline));
}
