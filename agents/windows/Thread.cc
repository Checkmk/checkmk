// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#include "Thread.h"
#include <stdexcept>
#include "Environment.h"
#include "Logger.h"
#include "WinApiInterface.h"
#include "win_error.h"

Thread::~Thread() {
    if (_thread_handle != INVALID_HANDLE_VALUE) {
        DWORD exitCode;
        _winapi.GetExitCodeThread(_thread_handle, &exitCode);
        if (exitCode == STILL_ACTIVE) {
            // baaad
            Logger *logger = static_cast<ThreadData *>(_data)->logger;
            Warning(logger) << "thread didn't finish, have to kill it";
            _winapi.TerminateThread(_thread_handle, 3);
        }
    }
}

int Thread::join() const {
    if (_thread_handle == INVALID_HANDLE_VALUE) {
        throw std::runtime_error("thread not started");
    }
    DWORD res = _winapi.WaitForSingleObject(_thread_handle, INFINITE);
    if (res != WAIT_OBJECT_0) {
        throw std::runtime_error(get_win_error_as_string(_winapi));
    }

    DWORD exitCode;
    _winapi.GetExitCodeThread(_thread_handle, &exitCode);
    return static_cast<int>(exitCode);
}

void Thread::start() {
    if (wasStarted()) {
        throw std::runtime_error("thread already started");
    }
    _thread_handle = _winapi.CreateThread(NULL, 0, _func, _data, 0, NULL);
    if (_thread_handle == NULL) {
        throw std::runtime_error(get_win_error_as_string(_winapi));
    }
}

bool Thread::wasStarted() const {
    return _thread_handle != INVALID_HANDLE_VALUE;
}
