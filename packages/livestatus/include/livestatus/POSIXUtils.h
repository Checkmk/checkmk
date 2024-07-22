// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef POSIXUtils_h
#define POSIXUtils_h

#include <fcntl.h>
#include <semaphore.h>
#include <sys/types.h>

#include <array>
#include <cerrno>
#include <chrono>
#include <filesystem>
#include <functional>
#include <optional>
#include <string>
#include <string_view>
#include <utility>
class Logger;

class SocketPair {
public:
    enum class Mode { blocking, local_non_blocking };
    enum class Direction { bidirectional, remote_to_local };

    static std::optional<SocketPair> make(Mode mode, Direction direction,
                                          Logger *logger);
    void close();

    [[nodiscard]] int local() const { return fd_[0]; }
    [[nodiscard]] int remote() const { return fd_[1]; }

private:
    std::array<int, 2> fd_;  // We do not own these FDs.

    SocketPair(int local, int remote) : fd_{local, remote} {}
};

void setThreadName(std::string name);
std::string getThreadName();

// TODO(sp) Emulate with C++ features
class Semaphore {
public:
    enum class Shared { between_threads, between_processes };

    Semaphore() : Semaphore{Shared::between_threads, 0U} {}
    explicit Semaphore(Shared shared) : Semaphore{shared, 0U} {}
    Semaphore(Shared shared, unsigned int value) {
        sem_init(&_semaphore, shared == Shared::between_threads ? 0 : 1, value);
    }
    ~Semaphore() { sem_destroy(&_semaphore); }
    void post() { sem_post(&_semaphore); }
    void wait() {
        while (sem_wait(&_semaphore) == -1 && errno == EINTR) {
        }
    }

private:
    sem_t _semaphore{};
};

// a POSIX-only variant of boost::interprocess::file_lock
class file_lock {
public:
    file_lock(const file_lock &) = delete;
    file_lock &operator=(const file_lock &) = delete;

    file_lock() : fd_(-1) {}
    explicit file_lock(const std::filesystem::path &name);
    file_lock(file_lock &&moved) noexcept : fd_(-1) { this->swap(moved); }

    file_lock &operator=(file_lock &&moved) noexcept {
        file_lock tmp(std::move(moved));
        this->swap(tmp);
        return *this;
    }

    ~file_lock();

    void swap(file_lock &other) noexcept { std::swap(fd_, other.fd_); }

    void lock() { fcntl_impl(F_WRLCK, F_SETLKW, "lock"); }

    bool try_lock() { return fcntl_impl(F_WRLCK, F_SETLK, "try_lock", true); }

    template <typename Clock, typename Duration>
    bool try_lock_until(const std::chrono::time_point<Clock, Duration> &time) {
        return try_lock_until_impl(time, F_WRLCK, "try_lock_until");
    }

    template <typename Rep, typename Period>
    bool try_lock_for(const std::chrono::duration<Rep, Period> &duration) {
        return try_lock_until_impl(std::chrono::steady_clock::now() + duration,
                                   F_WRLCK, "try_lock_for");
    }

    void unlock() { fcntl_impl(F_UNLCK, F_SETLK, "unlock"); }

    void lock_sharable() { fcntl_impl(F_RDLCK, F_SETLKW, "lock_sharable"); }

    bool try_lock_sharable() {
        return fcntl_impl(F_RDLCK, F_SETLK, "try_lock_sharable", true);
    }

    template <typename Clock, typename Duration>
    bool try_lock_sharable_until(
        const std::chrono::time_point<Clock, Duration> &time) {
        return try_lock_until_impl(time, F_RDLCK, "try_lock_sharable_until");
    }

    template <typename Rep, typename Period>
    bool try_lock_sharable_for(
        const std::chrono::duration<Rep, Period> &duration) {
        return try_lock_until_impl(std::chrono::steady_clock::now() + duration,
                                   F_RDLCK, "try_lock_sharable_for");
    }

    void unlock_sharable() { fcntl_impl(F_UNLCK, F_SETLK, "unlock_sharable"); }

private:
    int fd_;

    bool fcntl_impl(short l_type, int cmd, const char *msg) const {
        return fcntl_impl(l_type, cmd, msg, false);
    }

    bool fcntl_impl(short l_type, int cmd, const char *msg,
                    bool accecpt_timeout) const;

    bool try_lock_until_impl(const std::chrono::steady_clock::time_point &time,
                             short l_type, const char *msg);
};

ssize_t writeWithTimeoutWhile(int fd, std::string_view buffer,
                              std::chrono::nanoseconds timeout,
                              const std::function<bool()> &pred);

ssize_t writeWithTimeout(int fd, std::string_view buffer,
                         std::chrono::nanoseconds timeout);

#endif  // POSIXUtils_h
