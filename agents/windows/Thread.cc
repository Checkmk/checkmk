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
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include "Thread.h"
#include <stdexcept>
#include "Environment.h"
#include "Logger.h"
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
