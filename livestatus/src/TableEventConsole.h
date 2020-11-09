// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TableEventConsole_h
#define TableEventConsole_h

#include "config.h"  // IWYU pragma: keep

#include <cstdint>
#include <map>
#include <memory>
#include <string>
#include <vector>

#include "DoubleLambdaColumn.h"  // IWYU pragma: keep
#include "IntLambdaColumn.h"     // IWYU pragma: keep
#include "ListLambdaColumn.h"    // IWYU pragma: keep
#include "MonitoringCore.h"
#include "StringLambdaColumn.h"  // IWYU pragma: keep
#include "Table.h"
#include "TimeLambdaColumn.h"  // IWYU pragma: keep
#include "nagios.h"
class ColumnOffsets;
class Query;
class Row;

// NOTE: We have a few "keep" pragmas above to avoid the insane handling of
// template foward declarations, when the templates have parameters with
// defaults. Yet another example "simple things gone wrong"... :-/

class ECRow {
public:
    ECRow(MonitoringCore *mc, const std::vector<std::string> &headers,
          const std::vector<std::string> &columns);

    static std::unique_ptr<StringLambdaColumn<ECRow>> makeStringColumn(
        const std::string &name, const std::string &description,
        const ColumnOffsets &offsets);
    static std::unique_ptr<IntLambdaColumn<ECRow>> makeIntColumn(
        const std::string &name, const std::string &description,
        const ColumnOffsets &offsets);
    static std::unique_ptr<DoubleLambdaColumn<ECRow>> makeDoubleColumn(
        const std::string &name, const std::string &description,
        const ColumnOffsets &offsets);
    static std::unique_ptr<TimeLambdaColumn<ECRow>> makeTimeColumn(
        const std::string &name, const std::string &description,
        const ColumnOffsets &offsets);
    static std::unique_ptr<ListLambdaColumn<ECRow>> makeListColumn(
        const std::string &name, const std::string &description,
        const ColumnOffsets &offsets);

    [[nodiscard]] std::string getString(const std::string &column_name) const;
    [[nodiscard]] int32_t getInt(const std::string &column_name) const;
    [[nodiscard]] double getDouble(const std::string &column_name) const;

    [[nodiscard]] const MonitoringCore::Host *host() const;

private:
    std::map<std::string, std::string> map_;
    MonitoringCore::Host *host_;

    [[nodiscard]] std::string get(const std::string &column_name,
                                  const std::string &default_value) const;
};

class TableEventConsole : public Table {
public:
    explicit TableEventConsole(MonitoringCore *mc);

    void answerQuery(Query *query) override;

protected:
    bool isAuthorizedForEvent(Row row, const contact *ctc) const;

private:
    bool isAuthorizedForEventViaContactGroups(
        const MonitoringCore::Contact *ctc, Row row, bool &result) const;
    bool isAuthorizedForEventViaHost(const MonitoringCore::Contact *ctc,
                                     Row row, bool &result) const;
};

#endif  // TableEventConsole_h
