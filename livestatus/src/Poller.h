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
#include <algorithm>
#include <cerrno>
#include "BitMask.h"
#include "ChronoUtils.h"

enum class PollEvents { in = 1 << 0, out = 1 << 1 };
IS_BIT_MASK(PollEvents);

class Poller {
public:
    Poller() {
        FD_ZERO(&_readfds);
        FD_ZERO(&_writefds);
        _maxfd = -1;
    }

    template <typename Rep, typename Period>
    int poll(std::chrono::duration<Rep, Period> timeout) {
        int retval;
        timeval tv = to_timeval(timeout);
        // I/O primitives can fail when interrupted by a signal, so we should
        // retry the operation. In the plain C world, this is already
        // encapsulated in e.g. glibc's TEMP_FAILURE_RETRY macro, see:
        // https://www.gnu.org/software/libc/manual/html_node/Interrupted-Primitives.html
        do {
            retval = select(_maxfd + 1, &_readfds, &_writefds, nullptr, &tv);
        } while (retval == -1 && errno == EINTR);
        return retval;
    }

    void addFileDescriptor(int fd, PollEvents e) {
        addFileDescriptor(fd, e, PollEvents::in, _readfds);
        addFileDescriptor(fd, e, PollEvents::out, _writefds);
    }

    bool isFileDescriptorSet(int fd, PollEvents e) const {
        return isFileDescriptorSet(fd, e, PollEvents::in, _readfds) ||
               isFileDescriptorSet(fd, e, PollEvents::out, _writefds);
    }

private:
#ifdef __clang_analyzer__
    // Workaround for https://llvm.org/bugs/show_bug.cgi?id=8920
    fd_set _readfds{};
    fd_set _writefds{};
#else
    fd_set _readfds;
    fd_set _writefds;
#endif
    int _maxfd;

    void addFileDescriptor(int fd, PollEvents e, PollEvents mask, fd_set &fds) {
        if (!is_empty_bit_mask(e & mask)) {
            FD_SET(fd, &fds);
            _maxfd = std::max(_maxfd, fd);
        }
    }

    bool isFileDescriptorSet(int fd, PollEvents e, PollEvents mask,
                             const fd_set &fds) const {
        return !is_empty_bit_mask(e & mask) && FD_ISSET(fd, &fds);
    }
};

#endif  // Poller_h
