// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TableLog_h
#define TableLog_h

#include <string>

#include "livestatus/Table.h"
class ICore;
class LogCache;

class TableLog : public Table {
public:
    TableLog(ICore *mc, LogCache *log_cache);

    [[nodiscard]] std::string name() const override;
    [[nodiscard]] std::string namePrefix() const override;
    void answerQuery(Query &query, const User &user,
                     const ICore &core) override;
    [[nodiscard]] std::shared_ptr<Column> column(
        std::string colname) const override;

private:
    LogCache *log_cache_;
};

#endif  // TableLog_h
