// Copyright (C) 2019 tribe29 GmbH - License: Check_MK Enterprise License
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef POSIXUtils_h
#define POSIXUtils_h

#include "config.h"  // IWYU pragma: keep

#include <fcntl.h>
#include <semaphore.h>

#include <cerrno>
#include <chrono>
#include <string>
#include <utility>
class Logger;

class FileDescriptorPair {
public:
    // ATTENTION: blocking is Alert, Notify, RRD, nonblocking - Check && Icmp
    enum class Mode { blocking, nonblocking };

    static FileDescriptorPair invalid() { return FileDescriptorPair{-1, -1}; }
    [[nodiscard]] bool isInvalid() const {
        return local_ == -1 && remote_ == -1;
    }

    // TODO(sp) One of these pairs must die...

    static FileDescriptorPair createSocketPair(Mode mode, Logger *logger);
    static FileDescriptorPair createPipePair(Mode mode, Logger *logger);

    static FileDescriptorPair makePipePair(Mode mode, Logger *logger);

    [[nodiscard]] int local() const { return local_; }
    [[nodiscard]] int remote() const { return remote_; }

private:
    FileDescriptorPair(int local, int remote)
        : local_{local}, remote_{remote} {}

    int local_;
    int remote_;
};

void setThreadName(std::string name);
std::string getThreadName();

// TODO(sp) Emulate with C++ features
class Semaphore {
public:
    enum class Shared { between_threads, between_processes };

    explicit Semaphore(Shared shared = Shared::between_threads,
                       unsigned int value = 0) {
        sem_init(&_semaphore, shared == Shared::between_threads ? 0 : 1, value);
    }
    ~Semaphore() { sem_destroy(&_semaphore); }
    void post() { sem_post(&_semaphore); }
    void wait() {
        while (sem_wait(&_semaphore) == -1 && errno == EINTR) {
        }
    }

private:
    sem_t _semaphore;
};

// a POSIX-only variant of boost::interprocess::file_lock
class file_lock {
public:
    file_lock(const file_lock &) = delete;
    file_lock &operator=(const file_lock &) = delete;

    file_lock() : fd_(-1) {}
    explicit file_lock(const char *name);
    file_lock(file_lock &&moved) noexcept : fd_(-1) { this->swap(moved); }

    file_lock &operator=(file_lock &&moved) noexcept {
        file_lock tmp(std::move(moved));
        this->swap(tmp);
        return *this;
    }

    ~file_lock();

    void swap(file_lock &other) { std::swap(fd_, other.fd_); }

    void lock() { fcntl_impl(F_WRLCK, F_SETLKW, "lock"); }

    bool try_lock() { return fcntl_impl(F_WRLCK, F_SETLK, "try_lock", true); }

    template <class Clock, class Duration>
    bool try_lock_until(const std::chrono::time_point<Clock, Duration> &time) {
        return try_lock_until_impl(time, F_WRLCK, "try_lock_until");
    }

    template <class Rep, class Period>
    bool try_lock_for(const std::chrono::duration<Rep, Period> &duration) {
        return try_lock_until_impl(std::chrono::steady_clock::now() + duration,
                                   F_WRLCK, "try_lock_for");
    }

    void unlock() { fcntl_impl(F_UNLCK, F_SETLK, "unlock"); }

    void lock_sharable() { fcntl_impl(F_RDLCK, F_SETLKW, "lock_sharable"); }

    bool try_lock_sharable() {
        return fcntl_impl(F_RDLCK, F_SETLK, "try_lock_sharable", true);
    }

    template <class Clock, class Duration>
    bool try_lock_sharable_until(
        const std::chrono::time_point<Clock, Duration> &time) {
        return try_lock_until_impl(time, F_RDLCK, "try_lock_sharable_until");
    }

    template <class Rep, class Period>
    bool try_lock_sharable_for(
        const std::chrono::duration<Rep, Period> &duration) {
        return try_lock_until_impl(std::chrono::steady_clock::now() + duration,
                                   F_RDLCK, "try_lock_sharable_for");
    }

    void unlock_sharable() { fcntl_impl(F_UNLCK, F_SETLK, "unlock_sharable"); }

private:
    int fd_;

    bool fcntl_impl(short l_type, int cmd, const char *msg,
                    bool accecpt_timeout = false) const;

    bool try_lock_until_impl(const std::chrono::steady_clock::time_point &time,
                             short l_type, const char *msg);
};
#endif  // POSIXUtils_h
