// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef DowntimesOrComments_h
#define DowntimesOrComments_h

// NOTE: We need the 2nd "keep" pragma for deleting DowntimesOrComments. Is this
// an IWYU bug?
#include "config.h"  // IWYU pragma: keep

#include <map>
#include <memory>

#include "DowntimeOrComment.h"  // IWYU pragma: keep
#include "nagios.h"
class MonitoringCore;

class DowntimesOrComments {
public:
    explicit DowntimesOrComments(MonitoringCore *mc);
    void registerDowntime(nebstruct_downtime_data *data);
    void registerComment(nebstruct_comment_data *data);
    [[nodiscard]] auto begin() const { return _entries.cbegin(); }
    [[nodiscard]] auto end() const { return _entries.cend(); }

private:
    std::map<unsigned long, std::unique_ptr<DowntimeOrComment>> _entries;
    MonitoringCore *const _mc;
};

#endif  // DowntimesOrComments_h
