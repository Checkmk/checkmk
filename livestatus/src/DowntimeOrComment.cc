// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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

#include "DowntimeOrComment.h"
#include "logger.h"

DowntimeOrComment::DowntimeOrComment(nebstruct_downtime_struct *dt,
        unsigned long id)
    : _type(dt->downtime_type)
    , _entry_time(dt->entry_time)
    , _author_name(strdup(dt->author_name))
    , _comment(strdup(dt->comment_data))
      , _id(id)
{
    _host = find_host(dt->host_name);
    if (dt->service_description) {
        _service = find_service(dt->host_name, dt->service_description);
        _is_service = 1;
    }
    else {
        _service = 0;
        _is_service = 0;
    }
}


DowntimeOrComment::~DowntimeOrComment()
{
    free(_author_name);
    free(_comment);
}


    Downtime::Downtime(nebstruct_downtime_struct *dt)
    : DowntimeOrComment(dt, dt->downtime_id)
    , _start_time(dt->start_time)
    , _end_time(dt->end_time)
    , _fixed(dt->fixed)
    , _duration(dt->duration)
      , _triggered_by(dt->triggered_by)
{
}

    Comment::Comment(nebstruct_comment_struct *co)
    : DowntimeOrComment((nebstruct_downtime_struct *)co, co->comment_id)
    , _expire_time(co->expire_time)
    , _persistent(co->persistent)
    , _source(co->source)
    , _entry_type(co->entry_type)
      , _expires(co->expires)
{
}
