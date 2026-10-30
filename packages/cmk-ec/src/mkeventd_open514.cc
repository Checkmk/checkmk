// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// This small helper program needs the capability CAP_NET_BIND_SERVICE, which
// the packaging gives it, otherwise it is pointless. Where the Debian package
// can't set capabilities, it installs the program SUID root instead, see
// omd/debian/postinst.in. It binds the privileged ports for syslog via UDP and
// TCP and for SNMP traps, as its options request, moves the sockets to the file
// descriptors given there and executes mkeventd with the same arguments.
// mkeventd can then simply use these sockets.

#include <arpa/inet.h>
#include <netdb.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#include <cerrno>
#include <charconv>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <iostream>
#include <memory>
#include <optional>
#include <span>
#include <string>
#include <string_view>
#include <system_error>
#include <utility>

// Example command line:
// mkeventd_open514 --syslog --syslog-fd 3 --syslog-tcp --syslog-tcp-fd 4
// --snmptrap --snmptrap-fd 5

namespace {

[[noreturn]] void fail(const std::string &message) {
    std::cerr << message << '\n';
    ::exit(1);  // NOLINT(concurrency-mt-unsafe)
}

// The port of the service for the protocol, as /etc/services has it, or the
// fallback port if it lacks the service or is missing altogether.
std::string lookup_port(const char *service, const char *protocol,
                        const char *fallback_port) {
    // NOLINTNEXTLINE(concurrency-mt-unsafe): We have only one thread.
    const servent *entry = ::getservbyname(service, protocol);
    return entry == nullptr
               ? fallback_port
               : std::to_string(ntohs(static_cast<in_port_t>(entry->s_port)));
}

// A socket bound to one of the addresses, IPv6 ones first, or -1 and the errno
// of the last failed attempt to bind one.
std::pair<int, int> bind_socket(const addrinfo *addresses,
                                const std::string &description) {
    int error = 0;
    auto create_bound_socket = [&error, &description](const addrinfo *curr) {
        auto result = ::socket(curr->ai_family, curr->ai_socktype, 0);
        if (result == -1) {
            error = errno;
            return -1;
        }

        int optval = 1;
        if (::setsockopt(result, SOL_SOCKET, SO_REUSEADDR, &optval,
                         sizeof(optval)) != 0) {
            const std::string reason = std::generic_category().message(errno);
            fail("Cannot set SO_REUSEADDR on " + description + ": " + reason);
        }

        if (::bind(result, curr->ai_addr, curr->ai_addrlen) == 0) {
            return result;
        }
        error = errno;
        ::close(result);
        return -1;
    };

    int result = -1;
    for (const addrinfo *curr = addresses; curr != nullptr && result == -1;
         curr = curr->ai_next) {
        if (curr->ai_family == AF_INET6) {
            result = create_bound_socket(curr);
        }
    }

    for (const addrinfo *curr = addresses; curr != nullptr && result == -1;
         curr = curr->ai_next) {
        if (curr->ai_family == AF_INET) {
            result = create_bound_socket(curr);
        }
    }

    return {result, error};
}

void open_socket_as_fd(int type, const std::string &port, int target_fd,
                       const std::string &description) {
    const auto cannot_bind = "Cannot bind " + description + " to port " + port;
    addrinfo query{};
    query.ai_flags = AI_PASSIVE | AI_NUMERICSERV;
    query.ai_family = AF_UNSPEC;
    query.ai_socktype = type;

    addrinfo *info = nullptr;
    if (const int rc = ::getaddrinfo(nullptr, port.c_str(), &query, &info);
        rc != 0) {
        const std::string reason = rc == EAI_SYSTEM
                                       ? std::generic_category().message(errno)
                                       : ::gai_strerror(rc);
        fail(cannot_bind + ": " + reason);
    }
    const auto [sock, error] = bind_socket(info, description);
    ::freeaddrinfo(info);

    if (sock == -1) {
        auto message =
            cannot_bind + ": " + std::generic_category().message(error);
        // Binding a privileged port fails with EACCES without the privilege,
        // other errors like EADDRINUSE have nothing to do with it.
        if (error == EACCES) {
            message +=
                " (Does mkeventd_open514 have the capability "
                "CAP_NET_BIND_SERVICE, or is it SUID root? Is the filesystem "
                "mounted without \"nosuid\"?)";
        }
        fail(message);
    }

    // Make sure it is at the correct FD
    if (sock != target_fd) {
        if (::dup2(sock, target_fd) == -1) {
            const std::string reason = std::generic_category().message(errno);
            fail("Cannot move " + description + " to file descriptor " +
                 std::to_string(target_fd) + ": " + reason);
        }
        ::close(sock);
    }
}

// The file descriptor the option value names, or -1 if it names none.
int file_descriptor(std::string_view value) {
    const auto *const end = std::to_address(value.end());
    int fd = -1;
    const auto [rest, error] =
        std::from_chars(std::to_address(value.begin()), end, fd);
    return error == std::errc{} && rest == end ? fd : -1;
}

}  // namespace

int main(int argc, char **argv) {
    bool do_syslog = false;
    bool do_syslog_tcp = false;
    bool do_snmptrap = false;

    int syslog_fd = -1;
    int syslog_tcp_fd = -1;
    int snmptrap_fd = -1;

    const auto args = std::span{argv, static_cast<size_t>(argc)};
    // We need our path to find mkeventd next to us. Linux before 5.18 allows
    // calling a program without even its name, newer kernels pass an empty one
    // instead, and shells pass only the name when they find it via PATH.
    const std::filesystem::path program{args.empty() ? "" : args[0]};
    if (!program.has_parent_path()) {
        std::cerr << "Cannot find mkeventd: Called without a path\n";
        return 1;
    }
    for (size_t i = 1; i < args.size(); i++) {
        // Like the argparse of mkeventd, take "--option value" as well as
        // "--option=value".
        std::string_view option{args[i]};
        std::optional<std::string_view> value;
        if (const auto pos = option.find('='); pos != std::string_view::npos) {
            value = option.substr(pos + 1);
            option = option.substr(0, pos);
        } else if (i + 1 < args.size()) {
            value = args[i + 1];
        }
        if (option == "--syslog") {
            do_syslog = true;
        } else if (option == "--syslog-tcp") {
            do_syslog_tcp = true;
        } else if (option == "--snmptrap") {
            do_snmptrap = true;
        } else if (option == "--syslog-fd" && value) {
            syslog_fd = file_descriptor(*value);
        } else if (option == "--syslog-tcp-fd" && value) {
            syslog_tcp_fd = file_descriptor(*value);
        } else if (option == "--snmptrap-fd" && value) {
            snmptrap_fd = file_descriptor(*value);
        }
    }

    // Syslog via UDP
    if (do_syslog && syslog_fd > 0) {
        open_socket_as_fd(SOCK_DGRAM, lookup_port("syslog", "udp", "514"),
                          syslog_fd, "UDP socket for syslog");
    }

    // Syslog via TCP has no service of its own: 514/tcp is "shell", sometimes
    // with the alias "syslog".
    if (do_syslog_tcp && syslog_tcp_fd > 0) {
        open_socket_as_fd(SOCK_STREAM, "514", syslog_tcp_fd,
                          "TCP socket for syslog");
    }

    // SNMP traps
    if (do_snmptrap && snmptrap_fd > 0) {
        open_socket_as_fd(SOCK_DGRAM, lookup_port("snmptrap", "udp", "162"),
                          snmptrap_fd, "UDP socket for snmptrap");
    }

    // Drop root privileges when installed SUID root, see the setuid fallback in
    // omd/debian/postinst.in. execv() drops the capability anyway.
    if (::getuid() != ::geteuid() && ::seteuid(::getuid()) != 0) {
        ::perror("Cannot drop privileges");
        return 1;
    }

    // Execute the actual program that needs access to the socket.
    ::execv((program.parent_path() / "mkeventd").c_str(), argv);
    ::perror("Cannot execute mkeventd");
    return 1;
}
