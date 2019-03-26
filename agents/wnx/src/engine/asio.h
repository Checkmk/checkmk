
// Wrapping asio.hpp to hook socket creation with
// internal control of the options and mode
//

// Reasons:
// asio gives us no access to native handles before completion routines
// asio
// installed we have to set native handle as NOT INHERITABLE immediately upon
// creation

#ifndef asio_h__
#define asio_h__

#if defined(WIN32)
#include <WinSock2.h>

// asio will call this function nstead of the WSASocketW
// we will modify behavior of the socket
SOCKET WSASocketW_Hook(int af, int type, int protocol,
                       LPWSAPROTOCOL_INFOW lpProtocolInfo, GROUP g,
                       DWORD dwFlags);

#define WSASocketW WSASocketW_Hook
#include "asio.hpp"
#undef WSASocketW
#else
#include "asio.hpp"
#endif
#endif  // asio_h__
