// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "DowntimesOrComments.h"

#include "DowntimeOrComment.h"
#include "Logger.h"

// static
void DowntimesOrComments::registerDowntime(
    std::map<unsigned long, std::unique_ptr<DowntimeOrComment>> &entries,
    Logger *logger, nebstruct_downtime_data *data) {
    unsigned long id = data->downtime_id;
    switch (data->type) {
        case NEBTYPE_DOWNTIME_ADD:
        case NEBTYPE_DOWNTIME_LOAD:
            entries[id] = std::make_unique<Downtime>(
                ::find_host(data->host_name),
                data->service_description == nullptr
                    ? nullptr
                    : ::find_service(data->host_name,
                                     data->service_description),
                data);
            break;
        case NEBTYPE_DOWNTIME_DELETE:
            if (entries.erase(id) == 0) {
                Informational(logger)
                    << "Cannot delete non-existing downtime " << id;
            }
            break;
        default:
            break;
    }
}

// static
void DowntimesOrComments::registerComment(
    std::map<unsigned long, std::unique_ptr<DowntimeOrComment>> &entries,
    Logger *logger, nebstruct_comment_data *data) {
    unsigned long id = data->comment_id;
    switch (data->type) {
        case NEBTYPE_COMMENT_ADD:
        case NEBTYPE_COMMENT_LOAD:
            entries[id] = std::make_unique<Comment>(
                ::find_host(data->host_name),
                data->service_description == nullptr
                    ? nullptr
                    : ::find_service(data->host_name,
                                     data->service_description),
                data);
            break;
        case NEBTYPE_COMMENT_DELETE:
            if (entries.erase(id) == 0) {
                Informational(logger)
                    << "Cannot delete non-existing comment " << id;
            }
            break;
        default:
            break;
    }
}
