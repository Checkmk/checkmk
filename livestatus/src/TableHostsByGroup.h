// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TableHostsByGroup_h
#define TableHostsByGroup_h

#include "config.h"  // IWYU pragma: keep

#include <string>

#include "Table.h"
#include "contact_fwd.h"
class MonitoringCore;
class Query;
class Row;

class TableHostsByGroup : public Table {
public:
    explicit TableHostsByGroup(MonitoringCore *mc);
    [[nodiscard]] std::string name() const override;
    [[nodiscard]] std::string namePrefix() const override;
    void answerQuery(Query *query) override;
    bool isAuthorized(Row row, const contact *ctc) const override;
    // NOTE: We do *not* implement findObject() here, because we don't know
    // which host group we should refer to: Every host can be part of many host
    // groups.
};

#endif  // TableHostsByGroup_h
