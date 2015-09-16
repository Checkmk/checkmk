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
// Copyright by Mathias Kettner and Mathias Kettner GmbH.  All rights reserved.
//
// Check_MK is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.
//
// Check_MK is  distributed in the hope that it will be useful, but
// WITHOUT ANY WARRANTY;  without even the implied warranty of
// MERCHANTABILITY  or  FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU General Public License for more details.
//
// You should have  received  a copy of the  GNU  General Public
// License along with Check_MK.  If  not, email to mk@mathias-kettner.de
// or write to the postal address provided at www.mathias-kettner.de

#include "ClientQueue.h"
#include <unistd.h>

ClientQueue::ClientQueue()
{
    pthread_mutex_init(&_lock, 0);
    pthread_cond_init(&_signal, 0);
}

ClientQueue::~ClientQueue()
{
    for (_queue_t::iterator it = _queue.begin();
            it != _queue.end();
            ++it)
    {
        close(*it);
    }
    pthread_mutex_destroy(&_lock);
    pthread_cond_destroy(&_signal);
}

void ClientQueue::addConnection(int fd)
{
    pthread_mutex_lock(&_lock);
    _queue.push_back(fd);
    pthread_mutex_unlock(&_lock);
    pthread_cond_signal(&_signal);
}


int ClientQueue::popConnection()
{
    pthread_mutex_lock(&_lock);
    if (_queue.size() == 0) {
        pthread_cond_wait(&_signal, &_lock);
    }

    int fd = -1;
    if (_queue.size() > 0) {
        fd = _queue.front();
        _queue.pop_front();
    }
    pthread_mutex_unlock(&_lock);
    return fd;
}

void ClientQueue::wakeupAll()
{
    pthread_cond_broadcast(&_signal);
}
