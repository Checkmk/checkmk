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
#include <poll.h>
#include <cerrno>
#include <chrono>
#include <string>
#include <unordered_map>
#include <vector>
#include "BitMask.h"

enum class PollEvents { in = 1 << 0, out = 1 << 1 };
IS_BIT_MASK(PollEvents);

class Poller {
public:
    template <typename Rep, typename Period>
    int poll(std::chrono::duration<Rep, Period> timeout) {
        int retval;
        // I/O primitives can fail when interrupted by a signal, so we should
        // retry the operation. In the plain C world, this is already
        // encapsulated in e.g. glibc's TEMP_FAILURE_RETRY macro, see:
        // https://www.gnu.org/software/libc/manual/html_node/Interrupted-Primitives.html
        do {
            auto millis =
                std::chrono::duration_cast<std::chrono::milliseconds>(timeout);
            // The cast below is OK because int has at least 32 bits on all
            // platforms we care about: The timeout is then limited to 24.85
            // days, which should be more than enough for our needs.
            retval = ::poll(&_pollfds[0], _pollfds.size(),
                            static_cast<int>(millis.count()));
        } while (retval == -1 && errno == EINTR);
        return retval;
    }

    void addFileDescriptor(int fd, PollEvents e) {
        _fd_to_pollfd[fd] = _pollfds.size();
        _pollfds.push_back({fd, toMask(e), 0});
    }

    bool isFileDescriptorSet(int fd, PollEvents e) const {
        auto it = _fd_to_pollfd.find(fd);
        return it != _fd_to_pollfd.end() &&
               (_pollfds[it->second].revents & toMask(e)) != 0;
    }

private:
    std::vector<pollfd> _pollfds;
    std::unordered_map<int, size_t> _fd_to_pollfd;

    static short toMask(PollEvents e) {
        // The cast below is OK because all POLLFOO values are within the
        // guaranteed short value range.
        return static_cast<short>(
            (is_empty_bit_mask(e & PollEvents::in) ? 0 : POLLIN) |
            (is_empty_bit_mask(e & PollEvents::out) ? 0 : POLLOUT));
    }
};

#endif  // Poller_h
