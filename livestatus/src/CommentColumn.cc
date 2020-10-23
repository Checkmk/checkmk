// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "CommentColumn.h"

#include <algorithm>
#include <iterator>

#include "MonitoringCore.h"
#include "Renderer.h"
#include "Row.h"
#include "nagios.h"

void CommentColumn::output(Row row, RowRenderer &r,
                           const contact * /*auth_user*/,
                           std::chrono::seconds /*timezone_offset*/) const {
    ListRenderer l(r);
    for (const auto &comment : comments_for_row(row)) {
        if (_with_info) {
            SublistRenderer s(l);
            s.output(comment._id);
            s.output(comment._author);
            s.output(comment._comment);
            if (_with_extra_info) {
                s.output(comment._entry_type);
                s.output(comment._entry_time);
            }
        } else {
            l.output(comment._id);
        }
    }
}

std::vector<std::string> CommentColumn::getValue(
    Row row, const contact * /*auth_user*/,
    std::chrono::seconds /*timezone_offset*/) const {
    std::vector<std::string> ids;
    auto comments = comments_for_row(row);
    std::transform(
        comments.begin(), comments.end(), std::back_inserter(ids),
        [](const auto &comment) { return std::to_string(comment._id); });
    return ids;
}

std::vector<CommentData> CommentColumn::comments_for_row(Row row) const {
    if (const auto *const data = columnData<void>(row)) {
        return _is_service
                   ? _mc->comments_for_service(
                         reinterpret_cast<const MonitoringCore::Service *>(
                             data))
                   : _mc->comments_for_host(
                         reinterpret_cast<const MonitoringCore::Host *>(data));
    }
    return {};
}
