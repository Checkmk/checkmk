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
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#ifndef Poller_h
#define Poller_h

#include "config.h"  // IWYU pragma: keep
#include <sys/select.h>
#include <cerrno>
#include "ChronoUtils.h"

class Poller {
public:
    Poller() {
        FD_ZERO(&_readfds);
        FD_ZERO(&_writefds);
    }

    template <typename Rep, typename Period>
    int poll(int nfds, std::chrono::duration<Rep, Period> timeout) {
        int retval;
        timeval tv = to_timeval(timeout);
        // I/O primitives can fail when interrupted by a signal, so we should
        // retry the operation. In the plain C world, this is already
        // encapsulated in e.g. glibc's TEMP_FAILURE_RETRY macro, see:
        // https://www.gnu.org/software/libc/manual/html_node/Interrupted-Primitives.html
        do {
            retval = select(nfds, &_readfds, &_writefds, nullptr, &tv);
        } while (retval == -1 && errno == EINTR);
        return retval;
    }

    void addReadFD(int fd) { FD_SET(fd, &_readfds); }
    void addWriteFD(int fd) { FD_SET(fd, &_writefds); }

    bool isReadFDSet(int fd) const { return FD_ISSET(fd, &_readfds); }
    bool isWriteFDSet(int fd) const { return FD_ISSET(fd, &_writefds); }

private:
    fd_set _readfds;
    fd_set _writefds;
};

#endif  // Poller_h
