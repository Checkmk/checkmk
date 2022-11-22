// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef Poller_h
#define Poller_h

#include "config.h"  // IWYU pragma: keep

#include <poll.h>

#include <asio/basic_socket.hpp>
#include <cassert>
#include <cerrno>
#include <chrono>
#include <string>
#include <unordered_map>
#include <vector>

#include "BitMask.h"
#include "ChronoUtils.h"
#include "Logger.h"

enum class PollEvents { in = 1 << 0, out = 1 << 1, hup = 1 << 2 };
IS_BIT_MASK(PollEvents);

class Poller {
public:
    template <typename Rep, typename Period>
    int poll(std::chrono::duration<Rep, Period> timeout) {
        int retval{0};
        // I/O primitives can fail when interrupted by a signal, so we should
        // retry the operation. In the plain C world, this is already
        // encapsulated in e.g. glibc's TEMP_FAILURE_RETRY macro, see:
        // https://www.gnu.org/software/libc/manual/html_node/Interrupted-Primitives.html
        do {
            auto millis = mk::ticks<std::chrono::milliseconds>(timeout);
            // The cast below is OK because int has at least 32 bits on all
            // platforms we care about: The timeout is then limited to 24.85
            // days, which should be more than enough for our needs.
            retval = ::poll(_pollfds.data(), _pollfds.size(),
                            static_cast<int>(millis));
        } while (retval == -1 && errno == EINTR);

        return retval;
    }

    template <typename Rep, typename Period>
    [[nodiscard]] bool wait(std::chrono::duration<Rep, Period> timeout,
                            const int fd, const PollEvents e,
                            Logger *const logger) {
        addFileDescriptor(fd, e);
        const int retval = poll(timeout);
        if (retval == -1) {
            generic_error ge{"Polling failed"};
            Error(logger) << ge;
            return false;
        }
        if (retval == 0) {
            errno = ETIMEDOUT;
            generic_error ge{"Polling failed"};
            Debug(logger) << ge;
            return false;
        }
        if (!isFileDescriptorSet(fd, e)) {
            errno = EBADF;
            generic_error ge{"Polling failed"};
            Error(logger) << ge;
            return false;
        }
        return true;
    }

    template <typename Rep, typename Period>
    [[nodiscard]] bool wait(std::chrono::duration<Rep, Period> timeout,
                            const int fd, const PollEvents e) {
        this->addFileDescriptor(fd, e);
        const int retval = this->poll(timeout);
        if (retval == -1) {
            return false;
        }
        if (retval == 0) {
            errno = ETIMEDOUT;
            return false;
        }
        if (!this->isFileDescriptorSet(fd, e)) {
            errno = EBADF;
            return false;
        }
        return true;
    }

    void addFileDescriptor(int fd, PollEvents e) {
        assert(_fd_to_pollfd.find(fd) == std::cend(_fd_to_pollfd));
        _fd_to_pollfd[fd] = _pollfds.size();
        _pollfds.push_back({fd, toMask(e), 0});
    }

    template <class Protocol, class SocketService>
    void addFileDescriptor(
        const asio::basic_socket<Protocol, SocketService> &sock, PollEvents e) {
        addFileDescriptor(native_handle(sock), e);
    }

    bool isFileDescriptorSet(int fd, PollEvents e) const {
        auto it = _fd_to_pollfd.find(fd);
        return it != _fd_to_pollfd.end() &&
               (_pollfds[it->second].revents & toMask(e)) != 0;
    }

    template <class Protocol, class SocketService>
    bool isFileDescriptorSet(
        const asio::basic_socket<Protocol, SocketService> &sock,
        PollEvents e) const {
        return isFileDescriptorSet(native_handle(sock), e);
    }

private:
    friend class PollerFixture_ToMask_Test;       // CONTEXT: Google-Fuchsia
    friend class PollerFixture_Descriptors_Test;  // whitebox style testing

    std::vector<pollfd> _pollfds;
    std::unordered_map<int, size_t> _fd_to_pollfd;

    static short toMask(PollEvents e) {
        // The cast below is OK because all POLLFOO values are within the
        // guaranteed short value range.
        return static_cast<short>(
            (is_empty_bit_mask(e & PollEvents::in) ? 0 : POLLIN) |
            (is_empty_bit_mask(e & PollEvents::out) ? 0 : POLLOUT) |
            (is_empty_bit_mask(e & PollEvents::hup) ? 0 : POLLHUP));
    }

    template <class Protocol, class SocketService>
    static int native_handle(
        const asio::basic_socket<Protocol, SocketService> &sock) {
        // socket::native_handle is not const but we just want the copy of an
        // int here.
        return const_cast<asio::basic_socket<Protocol, SocketService> &>(sock)
            .native_handle();
    }
};

struct POSIXPollEvents {
    short value;
};

inline std::ostream &operator<<(std::ostream &os, const POSIXPollEvents &e) {
    os << "{";
    auto emit_separator{false};
    for (const auto &[mask, description] : {std::pair{POLLIN, "in"},
                                            {POLLPRI, "pri"},
                                            {POLLOUT, "out"},
                                            {POLLERR, "err"},
                                            {POLLHUP, "hup"},
                                            {POLLNVAL, "nval"}}) {
        if ((e.value & mask) != 0) {
            os << (emit_separator ? "," : "") << description;
            emit_separator = true;
        }
    }
    return os << "}";
}

inline std::ostream &operator<<(std::ostream &os, const pollfd &p) {
    return os << "pollfd{fd=" << p.fd << ",events=" << POSIXPollEvents{p.events}
              << ",revents=" << POSIXPollEvents{p.revents} << "}";
}

#endif  // Poller_h
