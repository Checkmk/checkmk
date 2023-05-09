// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TableComments_h
#define TableComments_h

#include "config.h"  // IWYU pragma: keep

#include <string>

#include "Table.h"
#include "contact_fwd.h"
class MonitoringCore;
class Query;
class Row;

class TableComments : public Table {
public:
    explicit TableComments(MonitoringCore *mc);
    [[nodiscard]] std::string name() const override;
    [[nodiscard]] std::string namePrefix() const override;
    void answerQuery(Query *query) override;
    bool isAuthorized(Row row, const contact *ctc) const override;
};

#endif  // TableComments_h
