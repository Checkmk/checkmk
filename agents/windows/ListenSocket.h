// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#ifndef ListenSocket_h
#define ListenSocket_h

#include <string>
#include "types.h"

class Logger;
class WinApiInterface;

struct SocketHandleTraits {
    using HandleT = SOCKET;
    static HandleT invalidValue() { return INVALID_SOCKET; }

    static void closeHandle(HandleT value, const WinApiInterface &winapi) {
        winapi.closesocket(value);
    }
};

using SocketHandle = WrappedHandle<SocketHandleTraits>;

class ListenSocket {
public:
    ListenSocket(int port, const only_from_t &source_whitelist,
                 bool supportIPV6, Logger *logger,
                 const WinApiInterface &winapi);

    bool supportsIPV4() const;
    bool supportsIPV6() const;

    SocketHandle acceptConnection() const;

    sockaddr_storage address(SOCKET connection) const;

private:
    SOCKET init_listen_socket(int port);
    bool check_only_from(const SOCKADDR &ip) const;
    SOCKET RemoveSocketInheritance(SOCKET oldsocket) const;

    Logger *_logger;
    const WinApiInterface &_winapi;
    const bool _use_ipv6;
    SocketHandle _socket;
    const only_from_t _source_whitelist;
    bool _supports_ipv4;
};

#endif  // ListenSocket_h
