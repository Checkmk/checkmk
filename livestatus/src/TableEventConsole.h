// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TableEventConsole_h
#define TableEventConsole_h

#include "config.h"  // IWYU pragma: keep

#include <cstdint>
#include <functional>
#include <map>
#include <memory>
#include <string>
#include <vector>

#include "IntColumn.h"
#include "ListColumn.h"
#include "MonitoringCore.h"
#include "Table.h"
#include "contact_fwd.h"

class ColumnOffsets;
template <class T>
class DoubleColumn;
class Query;
class Row;
template <class T>
class StringColumn;
template <class T>
class TimeColumn;

class ECRow {
public:
    ECRow(MonitoringCore *mc, const std::vector<std::string> &headers,
          const std::vector<std::string> &columns);

    static std::unique_ptr<StringColumn<ECRow>> makeStringColumn(
        const std::string &name, const std::string &description,
        const ColumnOffsets &offsets);
    static std::unique_ptr<IntColumn<ECRow>> makeIntColumn(
        const std::string &name, const std::string &description,
        const ColumnOffsets &offsets);
    static std::unique_ptr<DoubleColumn<ECRow>> makeDoubleColumn(
        const std::string &name, const std::string &description,
        const ColumnOffsets &offsets);
    static std::unique_ptr<TimeColumn<ECRow>> makeTimeColumn(
        const std::string &name, const std::string &description,
        const ColumnOffsets &offsets);
    static std::unique_ptr<ListColumn<ECRow>> makeListColumn(
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
    TableEventConsole(MonitoringCore *mc,
                      std::function<bool(Row, const contact *)> is_authorized);

    void answerQuery(Query *query) override;

protected:
    bool isAuthorizedForEvent(Row row, const contact *ctc) const;

private:
    std::function<bool(Row, const contact *)> is_authorized_;

    bool isAuthorizedForEventViaContactGroups(
        const MonitoringCore::Contact *ctc, Row row, bool &result) const;
    bool isAuthorizedForEventViaHost(const MonitoringCore::Contact *ctc,
                                     Row row, bool &result) const;
};

#endif  // TableEventConsole_h
