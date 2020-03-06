// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#ifndef Thread_h
#define Thread_h

#include <winsock2.h>
#include <functional>
#include <memory>
#include <mutex>

class Environment;
class Logger;
class WinApiInterface;

struct ThreadData {
    ThreadData(const Environment &env_, Logger *logger_)
        : env(env_), logger(logger_) {}
    ThreadData(const ThreadData &) = delete;
    ThreadData &operator=(const ThreadData &) = delete;

    time_t push_until{0};
    bool terminate{false};
    const Environment &env;
    Logger *logger;
    bool new_request{false};
    sockaddr_storage last_address{0};
    std::mutex mutex;
};

class Thread {
public:
    using ThreadFunc = DWORD WINAPI (*)(void *);

public:
    // the caller keeps ownership
    template <typename T>
    Thread(ThreadFunc func, T &data, const WinApiInterface &winapi)
        : _func(func), _data(static_cast<void *>(&data)), _winapi(winapi) {}
    ~Thread();
    Thread(const Thread &) = delete;

    // wait for the thread to finish and return its exit code.
    // this will block if the thread hasn't finished already
    int join() const;
    void start();

    // return true if the thread was stated. If this is false,
    // a call to join would throw an exception
    bool wasStarted() const;

private:
    static void nop(void *) {}

    ThreadFunc _func;
    HANDLE _thread_handle{INVALID_HANDLE_VALUE};
    void *_data;
    const WinApiInterface &_winapi;
};

#endif  // Thread_h
