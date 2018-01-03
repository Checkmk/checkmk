// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
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

#include "ClientQueue.h"
#include <unistd.h>
#include <algorithm>

ClientQueue::ClientQueue() : _should_terminate(false) {}

ClientQueue::~ClientQueue() {
    std::for_each(_queue.begin(), _queue.end(), close);
}

void ClientQueue::addConnection(int fd) {
    {
        std::lock_guard<std::mutex> lg(_mutex);
        _queue.push_back(fd);
    }
    _cond.notify_one();
}

int ClientQueue::popConnection() {
    std::unique_lock<std::mutex> ul(_mutex);
    while (_queue.empty() && !_should_terminate) {
        _cond.wait(ul);
    }
    if (_queue.empty()) {
        return -1;
    }
    int fd = _queue.front();
    _queue.pop_front();
    return fd;
}

// Note: What we *really* want here is the functionality of
// notify_all_at_thread_exit.
void ClientQueue::terminate() {
    {
        std::lock_guard<std::mutex> lg(_mutex);
        _should_terminate = true;
    }
    _cond.notify_all();
}
