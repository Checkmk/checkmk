// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TableComments.h"

#include <chrono>
#include <map>
#include <memory>
#include <type_traits>

#include "Column.h"
#include "DowntimeOrComment.h"
#include "IntColumn.h"
#include "MonitoringCore.h"
#include "NagiosCore.h"
#include "Query.h"
#include "Row.h"
#include "StringColumn.h"
#include "TableHosts.h"
#include "TableServices.h"
#include "TimeColumn.h"
#include "auth.h"
#include "nagios.h"  // IWYU pragma: keep

// TODO(sp): the dynamic data in this table must be locked with a mutex

TableComments::TableComments(MonitoringCore *mc) : Table(mc) {
    ColumnOffsets offsets{};
    addColumn(std::make_unique<StringColumn<Comment>>(
        "author", "The contact that entered the comment", offsets,
        [](const Comment &r) { return r._author; }));
    addColumn(std::make_unique<StringColumn<Comment>>(
        "comment", "A comment text", offsets,
        [](const Comment &r) { return r._comment; }));
    addColumn(std::make_unique<IntColumn<Comment>>(
        "id", "The id of the comment", offsets,
        [](const Comment &r) { return r._id; }));
    addColumn(std::make_unique<TimeColumn<Comment>>(
        "entry_time", "The time the entry was made as UNIX timestamp", offsets,
        [](const Comment &r) { return r._entry_time; }));
    addColumn(std::make_unique<IntColumn<Comment>>(
        "type", "The type of the comment: 1 is host, 2 is service", offsets,
        [](const Comment &r) { return r._type; }));
    addColumn(std::make_unique<BoolColumn<Comment>>(
        "is_service",
        "0, if this entry is for a host, 1 if it is for a service", offsets,
        [](const Comment &r) { return r._is_service; }));

    addColumn(std::make_unique<IntColumn<Comment>>(
        "persistent", "Whether this comment is persistent (0/1)", offsets,
        [](const Comment &r) { return r._persistent; }));
    addColumn(std::make_unique<IntColumn<Comment>>(
        "source", "The source of the comment (0 is internal and 1 is external)",
        offsets, [](const Comment &r) { return r._source; }));
    addColumn(std::make_unique<IntColumn<Comment>>(
        "entry_type",
        "The type of the comment: 1 is user, 2 is downtime, 3 is flapping and 4 is acknowledgement",
        offsets, [](const Comment &r) { return r._entry_type; }));
    addColumn(std::make_unique<IntColumn<Comment>>(
        "expires", "Whether this comment expires", offsets,
        [](const Comment &r) { return r._expires; }));
    addColumn(std::make_unique<TimeColumn<Comment>>(
        "expire_time", "The time of expiry of this comment as a UNIX timestamp",
        offsets, [](const Comment &r) { return r._expire_time; }));

    TableHosts::addColumns(this, "host_", offsets.add([](Row r) {
        return r.rawData<Comment>()->_host;
    }));
    TableServices::addColumns(this, "service_", offsets.add([](Row r) {
        return r.rawData<Comment>()->_service;
    }),
                              false /* no hosts table */);
}

std::string TableComments::name() const { return "comments"; }

std::string TableComments::namePrefix() const { return "comment_"; }

void TableComments::answerQuery(Query *query) {
    auto is_authorized = [service_auth = core()->serviceAuthorization(),
                          auth_user =
                              query->authUser()](const Comment *comment) {
        return comment->_service == nullptr
                   ? is_authorized_for_hst(auth_user, comment->_host)
                   : is_authorized_for_svc(service_auth, auth_user,
                                           comment->_service);
    };

    for (const auto &[id, co] : core()->impl<NagiosCore>()->_comments) {
        if (is_authorized(co.get()) && !query->processDataset(Row{co.get()})) {
            return;
        }
    }
}
