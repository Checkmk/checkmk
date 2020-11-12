// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "DowntimesOrComments.h"

#include "Logger.h"
#include "MonitoringCore.h"

DowntimesOrComments::DowntimesOrComments(MonitoringCore *mc) : _mc(mc) {}

void DowntimesOrComments::registerDowntime(nebstruct_downtime_data *data) {
    unsigned long id = data->downtime_id;
    switch (data->type) {
        case NEBTYPE_DOWNTIME_ADD:
        case NEBTYPE_DOWNTIME_LOAD:
            _entries[id] = std::make_unique<Downtime>(_mc, data);
            break;
        case NEBTYPE_DOWNTIME_DELETE:
            if (_entries.erase(id) == 0) {
                Informational(_mc->loggerLivestatus())
                    << "Cannot delete non-existing downtime " << id;
            }
            break;
        default:
            break;
    }
}

void DowntimesOrComments::registerComment(nebstruct_comment_data *data) {
    unsigned long id = data->comment_id;
    switch (data->type) {
        case NEBTYPE_COMMENT_ADD:
        case NEBTYPE_COMMENT_LOAD:
            _entries[id] = std::make_unique<Comment>(_mc, data);
            break;
        case NEBTYPE_COMMENT_DELETE:
            if (_entries.erase(id) == 0) {
                Informational(_mc->loggerLivestatus())
                    << "Cannot delete non-existing comment " << id;
            }
            break;
        default:
            break;
    }
}
