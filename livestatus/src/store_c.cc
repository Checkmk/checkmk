// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2015             mk@mathias-kettner.de |
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

#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <strings.h>
#include <map>
#include <set>

#include "nagios.h"
#include "store_c.h"
#include "Store.h"
#include "Query.h"
#include "ClientQueue.h"
#include "InputBuffer.h"
#include "OutputBuffer.h"
#include "logger.h"
#include "TimeperiodsCache.h"

using namespace std;

Store *g_store = 0;
ClientQueue *g_client_queue = 0;
TimeperiodsCache *g_timeperiods_cache = 0;

void store_init()
{
	g_store = new Store();
    g_client_queue = new ClientQueue();
    g_timeperiods_cache = new TimeperiodsCache();
}

void store_deinit()
{
    if (g_store) {
        delete g_store;
        g_store = 0;
    }
    if (g_client_queue) {
        delete g_client_queue;
        g_client_queue = 0;
    }
    if (g_timeperiods_cache) {
        delete g_timeperiods_cache;
        g_timeperiods_cache = 0;
    }
}

void queue_add_connection(int cc)
{
    g_client_queue->addConnection(cc);
}

int queue_pop_connection()
{
    return g_client_queue->popConnection();
}

void queue_wakeup_all()
{
    return g_client_queue->wakeupAll();
}


void store_register_comment(nebstruct_comment_data *d)
{
    g_store->registerComment(d);
}

void store_register_downtime(nebstruct_downtime_data *d)
{
    g_store->registerDowntime(d);
}

int store_answer_request(void *ib, void *ob)
{
    return g_store->answerRequest((InputBuffer *)ib, (OutputBuffer *)ob);
}

void *create_outputbuffer()
{
    return new OutputBuffer();
}

void flush_output_buffer(void *ob, int fd, int *termination_flag)
{
    ((OutputBuffer *)ob)->flush(fd, termination_flag);
}

void delete_outputbuffer(void *ob)
{
    delete (OutputBuffer *)ob;
}

void *create_inputbuffer(int *termination_flag)
{
    return new InputBuffer(termination_flag);
}

void set_inputbuffer_fd(void *ib, int fd)
{
    ((InputBuffer *)ib)->setFd(fd);
}

void delete_inputbuffer(void *ib)
{
    delete (InputBuffer *)ib;
}

void update_timeperiods_cache(time_t now)
{
    g_timeperiods_cache->update(now);
}

void log_timeperiods_cache(){
	g_timeperiods_cache->logCurrentTimeperiods();
}


