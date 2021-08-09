// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "DowntimeOrComment.h"

// TODO(sp): Remove ugly cast.
DowntimeOrComment::DowntimeOrComment(host *hst, service *svc,
                                     nebstruct_downtime_struct *dt,
                                     unsigned long id)
    : _type(dt->downtime_type)
    , _is_service(dt->service_description != nullptr)
    , _host(hst)
    , _service(svc)
    , _entry_time(dt->entry_time)
    , _author_name(dt->author_name)
    , _comment(dt->comment_data)
    , _id(id) {}

DowntimeOrComment::~DowntimeOrComment() = default;

Downtime::Downtime(host *hst, service *svc, nebstruct_downtime_struct *dt)
    : DowntimeOrComment(hst, svc, dt, dt->downtime_id)
    , _start_time(dt->start_time)
    , _end_time(dt->end_time)
    , _fixed(dt->fixed)
    , _duration{dt->duration}
    , _triggered_by{dt->triggered_by} {}

Comment::Comment(host *hst, service *svc, nebstruct_comment_struct *co)
    : DowntimeOrComment(hst, svc,
                        reinterpret_cast<nebstruct_downtime_struct *>(co),
                        co->comment_id)
    , _expire_time(co->expire_time)
    , _persistent(co->persistent)
    , _source(co->source)
    , _entry_type(co->entry_type)
    , _expires(co->expires) {}
