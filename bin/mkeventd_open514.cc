// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

/* This small helper program is intended to be installed SUID root.
   Otherwise it is pointless. It creates a UDP socket with port 514.
   This is a privileged operation. Then it drops the privileges,
   moves that port to file descriptor 3 and executes the mkeventd.

   That can then simply use filedescriptor 3 and receive syslog
   messages */

#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <string>
#include <vector>

#define SYSLOG_PORT 514
#define SNMPTRAP_PORT 162

// Example command line:
// mkeventd_open514 --syslog --syslog-fd 3 --syslog-tcp --syslog-tcp-fd 4
// --snmptrap --snmptrap-fd 5

// Opens syslog udp socket
// Protocols versions are tried in the following sequence:
// IPv6 dualstack -> IPv6 only -> IPv4
void open_syslog(int syslog_fd) {
    // Create socket
    int syslog_sock = ::socket(AF_INET6, SOCK_DGRAM, 0);
    if (syslog_sock == -1) {
        // If creating an IPv6 socket fails, create an IPv4 socket instead
        syslog_sock = ::socket(AF_INET, SOCK_DGRAM, 0);
        if (syslog_sock == -1) {
            perror("Cannot create UDP socket for syslog");
            exit(1);
        }
        // Bind it to the port (this requires privileges)
        sockaddr_in addr{};
        addr.sin_family = AF_INET;
        addr.sin_port = htons(SYSLOG_PORT);
        addr.sin_addr.s_addr = INADDR_ANY;
        // NOLINTNEXTLINE(cppcoreguidelines-pro-type-reinterpret-cast)
        if (::bind(syslog_sock, reinterpret_cast<struct sockaddr *>(&addr),
                   sizeof(addr)) != 0) {
            perror(
                "Cannot bind UDP socket for syslog to port "
                "(Is SUID bit set on mkeventd_open514? Is \"nosuid\" not set on the filesystem?)");
            exit(1);
        }

    } else {
        // set IPV6_V6ONLY
        int optvalipv6 = 0;
        if (setsockopt(syslog_sock, IPPROTO_IPV6, IPV6_V6ONLY, &optvalipv6,
                       sizeof(optvalipv6)) != 0) {
            // TODO: find out which errno is triggered on an IPv6 only host
            if (errno != EINVAL && errno != ENOPROTOOPT) {
                perror(
                    "Unknown error during socket option setting for syslog-udp");
                exit(1);
            }
            perror(
                "ipv6 dualstack failed. Continuing in ipv6-only mode for syslog UDP socket");
        }
        // Bind it to the port (this requires privileges)
        sockaddr_in6 addr{};
        addr.sin6_family = AF_INET6;
        addr.sin6_port = htons(SYSLOG_PORT);
        addr.sin6_addr = in6addr_any;
        // TODO(sp): What about sin6_scope_id?
        // NOLINTNEXTLINE(cppcoreguidelines-pro-type-reinterpret-cast)
        if (::bind(syslog_sock, reinterpret_cast<struct sockaddr *>(&addr),
                   sizeof(addr)) != 0) {
            perror(
                "Cannot bind UDP socket for syslog to port "
                "(Is SUID bit set on mkeventd_open514? Is \"nosuid\" not set on the filesystem?)");
            exit(1);
        }
    }

    // set REUSEADDR
    int optval = 1;
    if (setsockopt(syslog_sock, SOL_SOCKET, SO_REUSEADDR, &optval,
                   sizeof(optval)) != 0) {
        perror("Cannot set UDP socket for syslog to SO_REUSEADDR");
        exit(1);
    }

    // Make sure it is at the correct FD
    if (syslog_sock != 0 && syslog_sock != syslog_fd) {
        ::dup2(syslog_sock, syslog_fd);
        ::close(syslog_sock);
    }
}

// Opens syslog tcp socket
// Protocols versions are tried in the following sequence:
// IPv6 dualstack -> IPv6 only -> IPv4
void open_syslog_tcp(int syslog_tcp_fd) {
    // Create socket
    int syslog_tcp_sock = ::socket(AF_INET6, SOCK_STREAM, 0);

    if (syslog_tcp_sock == -1) {
        // If creating an IPv6 socket fails, create an IPv4 socket
        // instead
        syslog_tcp_sock = ::socket(AF_INET, SOCK_STREAM, 0);
        if (syslog_tcp_sock == -1) {
            perror("Cannot create UDP socket for syslog");
            exit(1);
        } else {
            // Bind it to the port (this requires privileges)
            sockaddr_in addr{};
            addr.sin_family = AF_INET;
            addr.sin_port = htons(SYSLOG_PORT);
            addr.sin_addr.s_addr = INADDR_ANY;
            if (::bind(
                    syslog_tcp_sock,
                    // NOLINTNEXTLINE(cppcoreguidelines-pro-type-reinterpret-cast)
                    reinterpret_cast<struct sockaddr *>(&addr),
                    sizeof(addr)) != 0) {
                perror(
                    "Cannot bind UDP socket for syslog to port "
                    "(Is SUID bit set on mkeventd_open514? Is \"nosuid\" not set on the filesystem?)");
                exit(1);
            }
        }
    } else {
        // set IPV6_V6ONLY
        int optvalipv6 = 0;
        if (setsockopt(syslog_tcp_sock, IPPROTO_IPV6, IPV6_V6ONLY, &optvalipv6,
                       sizeof(optvalipv6)) != 0) {
            // TODO: find out which errno is triggered on an IPv6 only host
            if (errno != EINVAL && errno != ENOPROTOOPT) {
                perror(
                    "Unknown error during socket option setting for syslog-tcp");
                exit(1);
            }
            perror(
                "ipv6 dualstack failed. Continuing in ipv6-only mode for syslog TCP socket");
        }
        // Bind it to the port (this requires privileges)
        sockaddr_in6 addr{};
        addr.sin6_family = AF_INET6;
        addr.sin6_port = htons(SYSLOG_PORT);
        addr.sin6_addr = in6addr_any;
        // TODO(sp): What about sin6_scope_id?
        // NOLINTNEXTLINE(cppcoreguidelines-pro-type-reinterpret-cast)
        if (::bind(syslog_tcp_sock, reinterpret_cast<struct sockaddr *>(&addr),
                   sizeof(addr)) != 0) {
            perror(
                "Cannot bind UDP socket for syslog to port "
                "(Is SUID bit set on mkeventd_open514? Is \"nosuid\" not set on the filesystem?)");
            exit(1);
        }
    }

    // set REUSEADDR
    int optval = 1;
    if (setsockopt(syslog_tcp_sock, SOL_SOCKET, SO_REUSEADDR, &optval,
                   sizeof(optval)) != 0) {
        perror("Cannot set TCP socket for syslog-tcp to SO_REUSEADDR");
        exit(1);
    }

    // Make sure it is at the correct FD
    if (syslog_tcp_sock != 0 && syslog_tcp_sock != syslog_tcp_fd) {
        ::dup2(syslog_tcp_sock, syslog_tcp_fd);
        ::close(syslog_tcp_sock);
    }
}

// Opens snmptrap socket
//  Protocols versions are tried in the following sequence:
//  IPv6 dualstack -> IPv6 only -> IPv4
void open_snmptrap(int snmptrap_fd) {
    // Create socket
    int snmptrap_sock = ::socket(AF_INET6, SOCK_DGRAM, 0);
    if (snmptrap_sock == -1) {
        // If creating an IPv6 socket fails, create an IPv4 socket
        // instead
        snmptrap_sock = ::socket(AF_INET, SOCK_DGRAM, 0);
        if (snmptrap_sock == -1) {
            perror("Cannot create UDP socket for syslog");
            exit(1);
        } else {
            // Bind it to the port (this requires privileges)
            sockaddr_in addr{};
            addr.sin_family = AF_INET;
            addr.sin_port = htons(SNMPTRAP_PORT);
            addr.sin_addr.s_addr = INADDR_ANY;
            if (::bind(snmptrap_sock,
                       reinterpret_cast<struct sockaddr *>(&addr),
                       sizeof(addr)) != 0) {
                perror(
                    "Cannot bind UDP socket for syslog to port "
                    "(Is SUID bit set on mkeventd_open514? Is \"nosuid\" not set on the filesystem?)");
                exit(1);
            }
        }
    } else {
        // set IPV6_V6ONLY
        int optvalipv6 = 0;
        if (setsockopt(snmptrap_sock, IPPROTO_IPV6, IPV6_V6ONLY, &optvalipv6,
                       sizeof(optvalipv6)) != 0) {
            // TODO: find out which errno is triggered on an IPv6 only host
            if (errno != EINVAL && errno != ENOPROTOOPT) {
                perror(
                    "Unknown error during socket option setting for snmptrap");
                exit(1);
            }
            perror(
                "ipv6 dualstack failed. Continuing in ipv6-only mode for snmptrap");
        }
        // Bind it to the port (this requires privileges)
        sockaddr_in6 addr{};
        addr.sin6_family = AF_INET6;
        addr.sin6_port = htons(SNMPTRAP_PORT);
        addr.sin6_addr = in6addr_any;
        // TODO(sp): What about sin6_scope_id?
        // NOLINTNEXTLINE(cppcoreguidelines-pro-type-reinterpret-cast)
        if (::bind(snmptrap_sock, reinterpret_cast<struct sockaddr *>(&addr),
                   sizeof(addr)) != 0) {
            perror(
                "Cannot bind UDP socket for syslog to port "
                "(Is SUID bit set on mkeventd_open514? Is \"nosuid\" not set on the filesystem?)");
            exit(1);
        }
    }

    // set REUSEADDR
    int optval = 1;
    if (setsockopt(snmptrap_sock, SOL_SOCKET, SO_REUSEADDR, &optval,
                   sizeof(optval)) != 0) {
        perror("Cannot set UDP socket for snmptrap to SO_REUSEADDR");
        exit(1);
    }

    // Make sure it is at the correct FD
    if (snmptrap_sock != 0 && snmptrap_sock != snmptrap_fd) {
        ::dup2(snmptrap_sock, snmptrap_fd);
        ::close(snmptrap_sock);
    }
}

int main(int argc, char **argv) {
    int do_syslog = 0;
    int do_syslog_tcp = 0;
    int do_snmptrap = 0;

    int syslog_fd = -1;
    int syslog_tcp_fd = -1;
    int snmptrap_fd = -1;

    std::vector<std::string> arguments{argv, argv + argc};
    for (int i = 1; i < argc; i++) {
        if (arguments[i] == "--syslog") {
            do_syslog = 1;
        } else if (arguments[i] == "--syslog-tcp") {
            do_syslog_tcp = 1;
        } else if (arguments[i] == "--snmptrap") {
            do_snmptrap = 1;
        } else if (arguments[i] == "--syslog-fd") {
            syslog_fd = atoi(arguments[i+1].c_str());
        } else if (arguments[i] == "--syslog-tcp-fd") {
            syslog_tcp_fd = atoi(arguments[i+1].c_str());
        } else if (arguments[i] == "--snmptrap-fd") {
            snmptrap_fd = atoi(arguments[i+1].c_str());
        }
    }

    // Syslog via UDP
    if (do_syslog != 0 && syslog_fd > 0) {
        open_syslog(syslog_fd);
    }

    // Syslog via TCP
    if (do_syslog_tcp != 0 && syslog_tcp_fd > 0) {
        open_syslog_tcp(syslog_tcp_fd);
    }

    // SNMP traps
    if (do_snmptrap != 0 && snmptrap_fd > 0) {
        open_snmptrap(snmptrap_fd);
    }

    // Drop privileges
    if (getuid() != geteuid() && seteuid(getuid())) {
        perror("Cannot drop privileges");
        exit(1);
    }

    // Execute the actual program that needs access to the socket.
    ::execv((std::filesystem::path{argv[0]}.parent_path() / "mkeventd").c_str(),
            argv);
    perror("Cannot execute mkeventd");
}
