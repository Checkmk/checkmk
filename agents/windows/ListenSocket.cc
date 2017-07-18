// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2017             mk@mathias-kettner.de |
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
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include "ListenSocket.h"
#include <winsock2.h>
#include <ws2ipdef.h>
#include <cassert>
#include <cstring>
#include <memory>
#include "LoggerAdaptor.h"
#include "stringutil.h"

static const size_t INET6_ADDRSTRLEN = 46;

ListenSocket::ListenSocket(int port, const only_from_t &source_whitelist,
                           bool supportIPV6, const LoggerAdaptor &logger)
    : _socket(init_listen_socket(port))
    , _source_whitelist(source_whitelist)
    , _supports_ipv4(true)
    , _use_ipv6(supportIPV6)
    , _logger(logger) {}

ListenSocket::~ListenSocket() { closesocket(_socket); }

bool ListenSocket::supportsIPV4() const { return _supports_ipv4; }

bool ListenSocket::supportsIPV6() const { return _use_ipv6; }

SOCKET RemoveSocketInheritance(SOCKET oldsocket) {
    HANDLE newhandle;
    // FIXME: this may not work on some setups!
    //   sockets are no simple handles, they may have additional information
    //   attached by layered
    //   service providers. This drops all of that information!
    //   Also, sockets are supposedly non-inheritable anyway
    DuplicateHandle(GetCurrentProcess(), (HANDLE)oldsocket, GetCurrentProcess(),
                    &newhandle, 0, FALSE,
                    DUPLICATE_CLOSE_SOURCE | DUPLICATE_SAME_ACCESS);
    return (SOCKET)newhandle;
}

bool ListenSocket::check_only_from(sockaddr *ip) {
    if (_source_whitelist.size() == 0) return true;  // no restriction set

    for (only_from_t::const_iterator it_from = _source_whitelist.begin();
         it_from != _source_whitelist.end(); ++it_from) {
        ipspec *only_from = *it_from;

        if (only_from->ipv6 != (ip->sa_family == AF_INET6)) {
            // test ipv6 address only against ipv6 filter and ipv4 address
            // against ipv4 filter.
            // the only_from list already contains v4->v6 converted addresses
            continue;
        }

        if (ip->sa_family == AF_INET6) {
            bool match = true;
            sockaddr_in6 *addrv6 = (sockaddr_in6 *)ip;
            for (int i = 0; i < 8 && match; ++i) {
                match =
                    only_from->ip.v6.address[i] ==
                    (addrv6->sin6_addr.u.Word[i] & only_from->ip.v6.netmask[i]);
            }
            if (match) {
                return true;
            }
        } else {
            uint32_t significant_bits =
                ((sockaddr_in *)ip)->sin_addr.s_addr & only_from->ip.v4.netmask;
            if (significant_bits == only_from->ip.v4.address) {
                return true;
            }
        }
    }
    return false;
}

SOCKET ListenSocket::init_listen_socket(int port) {
    // We need to create a socket which listens for incoming connections
    // but we do not want that it is inherited to child processes
    // (local/plugins)
    // Therefore we open the socket - this one is inherited by default
    // Now we duplicate this handle and explicitly say that inheritance is
    // forbidden
    // and use the duplicate from now on
    SOCKET tmp_s = socket(_use_ipv6 ? AF_INET6 : AF_INET, SOCK_STREAM, 0);
    if (tmp_s == INVALID_SOCKET) {
        int error_id = ::WSAGetLastError();
        if (error_id == WSAEAFNOSUPPORT) {
            // this will happen on Win2k and WinXP without the ipv6 patch
            _logger.verbose("IPV6 not supported");
            _use_ipv6 = false;
            tmp_s = socket(AF_INET, SOCK_STREAM, 0);
        }
        if (tmp_s == INVALID_SOCKET) {
            error_id = ::WSAGetLastError();
            fprintf(stderr, "Cannot create socket: %s (%d)\n",
                    get_win_error_as_string(error_id).c_str(), error_id);
            exit(1);
        }
    }
    SOCKET s = RemoveSocketInheritance(tmp_s);

    int addr_size = 0;
    std::unique_ptr<SOCKADDR> addr(create_sockaddr(&addr_size));

    int optval = 1;
    setsockopt(s, SOL_SOCKET, SO_REUSEADDR, (const char *)&optval,
               sizeof(optval));
    if (_use_ipv6) {
        ((SOCKADDR_IN6 *)addr.get())->sin6_port = htons(port);

        int v6only = 0;
        if (setsockopt(s, IPPROTO_IPV6, IPV6_V6ONLY, (char *)&v6only,
                       sizeof(int)) != 0) {
            _logger.verbose("failed to disable ipv6 only flag");
            _supports_ipv4 = false;
        }
    } else {
        ((SOCKADDR_IN *)addr.get())->sin_port = htons(port);
        ((SOCKADDR_IN *)addr.get())->sin_addr.s_addr = ADDR_ANY;
    }

    if (SOCKET_ERROR == bind(s, addr.get(), addr_size)) {
        int error_id = ::WSAGetLastError();
        fprintf(stderr, "Cannot bind socket to port %d: %s (%d)\n", port,
                get_win_error_as_string(error_id).c_str(), error_id);
        exit(1);
    }

    if (SOCKET_ERROR == listen(s, 5)) {
        fprintf(stderr, "Cannot listen to socket\n");
        exit(1);
    }

    return s;
}

sockaddr_storage ListenSocket::address(SOCKET connection) const {
    sockaddr_storage addr;
    int addrlen = sizeof(sockaddr_storage);
    getpeername(connection, (sockaddr *)&addr, &addrlen);
    return addr;
}

std::string ListenSocket::readableIP(SOCKET connection) {
    sockaddr_storage addr;
    int addrlen = sizeof(sockaddr_storage);
    getpeername(connection, (sockaddr *)&addr, &addrlen);
    return readableIP(&addr);
}

std::string ListenSocket::readableIP(const sockaddr_storage *addr) {
    char ip_hr[INET6_ADDRSTRLEN];

    if (addr->ss_family == AF_INET) {
        sockaddr_in *s = (sockaddr_in *)addr;
        u_char *ip = (u_char *)&s->sin_addr;
        snprintf(ip_hr, INET6_ADDRSTRLEN, "%u.%u.%u.%u", ip[0], ip[1], ip[2],
                 ip[3]);
    } else if (addr->ss_family == AF_INET6) {  // AF_INET6
        sockaddr_in6 *s = (sockaddr_in6 *)addr;
        uint16_t *ip = s->sin6_addr.u.Word;
        snprintf(ip_hr, INET6_ADDRSTRLEN, "%x:%x:%x:%x:%x:%x:%x:%x", ip[0],
                 ip[1], ip[2], ip[3], ip[4], ip[5], ip[6], ip[7]);
    } else {
        snprintf(ip_hr, INET6_ADDRSTRLEN, "None");
    }
    return ip_hr;
}

sockaddr *ListenSocket::create_sockaddr(int *addr_len) {
    assert(addr_len != NULL);

    sockaddr *result = NULL;
    if (_use_ipv6) {
        result = (sockaddr *)new sockaddr_in6();
        *addr_len = sizeof(sockaddr_in6);
    } else {
        result = (sockaddr *)new sockaddr_in();
        *addr_len = sizeof(sockaddr_in);
    }
    memset((void *)result, 0, *addr_len);
    result->sa_family = _use_ipv6 ? AF_INET6 : AF_INET;

    return result;
}

SOCKET ListenSocket::acceptConnection() {
    SOCKET connection;
    // Loop forever.

    fd_set fds;
    FD_ZERO(&fds);
    FD_SET(_socket, &fds);
    struct timeval timeout;
    timeout.tv_sec = 0;
    timeout.tv_usec = 500000;

    // FIXME: every failed connect resets the timeout so technically this may
    // never return
    while (1 == select(1, &fds, NULL, NULL, &timeout)) {
        int addr_len = 0;
        std::unique_ptr<sockaddr> remote_addr(create_sockaddr(&addr_len));
        connection = accept(_socket, remote_addr.get(), &addr_len);
        connection = RemoveSocketInheritance(connection);
        if (connection != INVALID_SOCKET) {
            bool allowed = check_only_from(remote_addr.get());

            if (allowed) {
                return connection;
            } else {
                closesocket(connection);
            }
        }
    }
    return 0;
}
