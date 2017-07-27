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

#ifndef ListenSocket_h
#define ListenSocket_h

#include <string>
#include "types.h"

class LoggerAdaptor;
class WinApiAdaptor;

class ListenSocket {
    const LoggerAdaptor &_logger;
    const WinApiAdaptor &_winapi;
    SOCKET _socket;
    only_from_t _source_whitelist;
    bool _supports_ipv4;
    bool _use_ipv6;

public:
    ListenSocket(int port, const only_from_t &source_whitelist,
                 bool supportIPV6, const LoggerAdaptor &logger,
                 const WinApiAdaptor &winapi);
    ~ListenSocket();

    bool supportsIPV4() const;
    bool supportsIPV6() const;

    SOCKET acceptConnection();

    sockaddr_storage address(SOCKET connection) const;

    std::string readableIP(SOCKET connection) const;
    static std::string readableIP(const sockaddr_storage *address);

private:
    SOCKET init_listen_socket(int port);
    bool check_only_from(sockaddr *ip);
    sockaddr *create_sockaddr(int *addr_len);
    SOCKET RemoveSocketInheritance(SOCKET oldsocket) const;
};

#endif  // ListenSocket_h
