// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2012             mk@mathias-kettner.de |
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

#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <strings.h>
#include <map>
#include <set>

#include "nagios.h"
#include "store.h"
#include "Store.h"
#include "Query.h"
#include "ClientQueue.h"
#include "InputBuffer.h"
#include "OutputBuffer.h"
#include "logger.h"
#include "TimeperiodsCache.h"
#include "LogCache.h"

using namespace std;

Store *g_store = 0;
ClientQueue *g_client_queue = 0;
TimeperiodsCache *g_timeperiods_cache = 0;

/* API functions for event broker module (with C linkage) */
extern unsigned long g_max_cached_messages;


void store_init()
{
	new LogCache(g_max_cached_messages);
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

