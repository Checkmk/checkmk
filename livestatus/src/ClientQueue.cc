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
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include "ClientQueue.h"
#include <unistd.h>
#include <algorithm>

using mk::lock_guard;
using mk::mutex;
using mk::unique_lock;
using std::for_each;

ClientQueue::ClientQueue() : _should_terminate(false) {}

ClientQueue::~ClientQueue() { for_each(_queue.begin(), _queue.end(), close); }

void ClientQueue::addConnection(int fd) {
    {
        lock_guard<mutex> lg(_mutex);
        _queue.push_back(fd);
    }
    _cond.notify_one();
}

int ClientQueue::popConnection() {
    unique_lock<mutex> ul(_mutex);
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
        lock_guard<mutex> lg(_mutex);
        _should_terminate = true;
    }
    _cond.notify_all();
}
