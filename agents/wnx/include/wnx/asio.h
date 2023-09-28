// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// Wrapping asio.hpp to hook socket creation with
// internal control of the options and mode
//

// Reasons:
// asio gives us no access to native handles before completion routines
// asio
// installed we have to set native handle as NOT INHERITABLE immediately upon
// creation

#ifndef ASIO_H
#define ASIO_H

#if defined(_WIN32)  // Windows MSDN 32/64 bits for ARM/x86
#include <WinSock2.h>

// asio will call this function instead of the WSASocketW
// we will modify behavior of the socket
SOCKET WSASocketW_Hook(int af, int type, int protocol,
                       LPWSAPROTOCOL_INFOW protocol_info, GROUP g, DWORD flags);

#define WSASocketW WSASocketW_Hook
#include <asio.hpp>
#undef WSASocketW
#else
#error \
    "Please, double check, that your handles are not kept by spawning processes"
#include <asio.hpp>
#endif
#endif  // ASIO_H
