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
#include "Logger.h"
#include "WinApiAdaptor.h"
#include "win_error.h"

static const size_t INET6_ADDRSTRLEN = 46;

ListenSocket::ListenSocket(int port, const only_from_t &source_whitelist,
                           bool supportIPV6, Logger *logger,
                           const WinApiAdaptor &winapi)
    : _logger(logger)
    , _winapi(winapi)
    , _use_ipv6(supportIPV6)
    , _socket(init_listen_socket(port), winapi)
    , _source_whitelist(source_whitelist)
    , _supports_ipv4(true) {}

bool ListenSocket::supportsIPV4() const { return _supports_ipv4; }

bool ListenSocket::supportsIPV6() const { return _use_ipv6; }

SOCKET ListenSocket::RemoveSocketInheritance(SOCKET oldsocket) const {
    HANDLE newhandle;
    // FIXME: this may not work on some setups!
    //   sockets are no simple handles, they may have additional information
    //   attached by layered
    //   service providers. This drops all of that information!
    //   Also, sockets are supposedly non-inheritable anyway
    _winapi.DuplicateHandle(_winapi.GetCurrentProcess(), (HANDLE)oldsocket,
                            _winapi.GetCurrentProcess(), &newhandle, 0, FALSE,
                            DUPLICATE_CLOSE_SOURCE | DUPLICATE_SAME_ACCESS);
    return (SOCKET)newhandle;
}

bool ListenSocket::check_only_from(sockaddr *ip) const {
    if (_source_whitelist.size() == 0) return true;  // no restriction set

    for (only_from_t::const_iterator it_from = _source_whitelist.begin();
         it_from != _source_whitelist.end(); ++it_from) {
        const ipspec &only_from = *it_from;

        if (only_from.ipv6 != (ip->sa_family == AF_INET6)) {
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
                    only_from.ip.v6.address[i] ==
                    (addrv6->sin6_addr.u.Word[i] & only_from.ip.v6.netmask[i]);
            }
            if (match) {
                return true;
            }
        } else {
            uint32_t significant_bits =
                ((sockaddr_in *)ip)->sin_addr.S_un.S_addr &
                only_from.ip.v4.netmask;

            if (significant_bits == only_from.ip.v4.address) {
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
    SOCKET tmp_s =
        _winapi.socket(_use_ipv6 ? AF_INET6 : AF_INET, SOCK_STREAM, 0);
    if (tmp_s == INVALID_SOCKET) {
        int error_id = _winapi.WSAGetLastError();
        Error(_logger) << "Cannot create socket: "
                       << get_win_error_as_string(_winapi, error_id) << " ("
                       << error_id << ")";
        exit(1);
    }
    SOCKET s = RemoveSocketInheritance(tmp_s);

    int addr_size = 0;
    SOCKADDR *addr = nullptr;
    SOCKADDR_IN6 addr6{0};
    SOCKADDR_IN addr4{0};

    int optval = 1;
    _winapi.setsockopt(s, SOL_SOCKET, SO_REUSEADDR,
                       reinterpret_cast<const char *>(&optval), sizeof(optval));
    if (_use_ipv6) {
        addr6.sin6_port = _winapi.htons(port);
        int v6only = 0;
        if (_winapi.setsockopt(s, IPPROTO_IPV6, IPV6_V6ONLY, (char *)&v6only,
                               sizeof(int)) != 0) {
            Notice(_logger) << "failed to disable ipv6 only flag";
            _supports_ipv4 = false;
        }
        addr = reinterpret_cast<SOCKADDR *>(&addr6);
        addr->sa_family = AF_INET6;
        addr_size = sizeof(SOCKADDR_IN6);
    } else {
        addr4.sin_port = _winapi.htons(port);
        addr4.sin_addr.S_un.S_addr = ADDR_ANY;
        addr = reinterpret_cast<SOCKADDR *>(&addr4);
        addr->sa_family = AF_INET;
        addr_size = sizeof(SOCKADDR_IN);
    }

    if (SOCKET_ERROR == _winapi.bind(s, addr, addr_size)) {
        int error_id = _winapi.WSAGetLastError();
        Error(_logger) << "Cannot bind socket to port " << port << ": "
                       << get_win_error_as_string(_winapi, error_id) << " ("
                       << error_id << ")";
        exit(1);
    }

    if (SOCKET_ERROR == _winapi.listen(s, 5)) {
        Error(_logger) << "Cannot listen to socket";
        exit(1);
    }

    return s;
}

sockaddr_storage ListenSocket::address(SOCKET connection) const {
    sockaddr_storage addr;
    int addrlen = sizeof(sockaddr_storage);
    _winapi.getpeername(connection, (sockaddr *)&addr, &addrlen);
    return addr;
}

std::string ListenSocket::readableIP(SOCKET connection) const {
    sockaddr_storage addr;
    int addrlen = sizeof(sockaddr_storage);
    _winapi.getpeername(connection, (sockaddr *)&addr, &addrlen);
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

SocketHandle ListenSocket::acceptConnection() const {
    // Loop forever.
    fd_set fds;
    FD_ZERO(&fds);
    FD_SET(_socket.get(), &fds);
    struct timeval timeout{0};
    timeout.tv_sec = 0;
    timeout.tv_usec = 500000;

    // FIXME: every failed connect resets the timeout so technically this may
    // never return
    while (1 == _winapi.select(1, &fds, NULL, NULL, &timeout)) {
        int addr_len = 0;
        SOCKADDR *remoteAddr = nullptr;
        SOCKADDR_IN6 addr6{0};
        SOCKADDR_IN addr4{0};

        if (_use_ipv6) {
            remoteAddr = reinterpret_cast<SOCKADDR *>(&addr6);
            remoteAddr->sa_family = AF_INET6;
            addr_len = sizeof(SOCKADDR_IN6);
        } else {
            remoteAddr = reinterpret_cast<SOCKADDR *>(&addr4);
            remoteAddr->sa_family = AF_INET;
            addr_len = sizeof(SOCKADDR_IN);
        }

        SOCKET rawSocket = _winapi.accept(_socket.get(), remoteAddr, &addr_len);
        SocketHandle connection(RemoveSocketInheritance(rawSocket), _winapi);
        if (connection && check_only_from(remoteAddr)) {
            return connection;
        }
    }

    return SocketHandle(_winapi);
}
