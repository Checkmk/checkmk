// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TableEventConsole_h
#define TableEventConsole_h

#include "config.h"  // IWYU pragma: keep

#include <chrono>
#include <cstdint>
#include <ctime>
#include <map>
#include <string>
#include <vector>

#include "DoubleColumn.h"
#include "IntColumn.h"
#include "ListColumn.h"
#include "MonitoringCore.h"
#include "Row.h"
#include "StringColumn.h"
#include "StringUtils.h"
#include "Table.h"
#include "TimeColumn.h"
#include "nagios.h"
class ColumnOffsets;
class Query;

class ECRow {
public:
    ECRow(MonitoringCore *mc, const std::vector<std::string> &headers,
          const std::vector<std::string> &columns);
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
    struct StringEventConsoleColumn : public StringColumn {
        StringEventConsoleColumn(const std::string &name,
                                 const std::string &description,
                                 const ColumnOffsets &offsets)
            : StringColumn(name, description, offsets) {}

        [[nodiscard]] std::string getValue(Row row) const override {
            if (const auto *r = columnData<ECRow>(row)) {
                return r->getString(name());
            }
            return "";
        }
    };

    struct IntEventConsoleColumn : public IntColumn {
        IntEventConsoleColumn(const std::string &name,
                              const std::string &description,
                              const ColumnOffsets &offsets)
            : IntColumn(name, description, offsets) {}

        int32_t getValue(Row row,
                         const contact * /* auth_user */) const override {
            if (const auto *r = columnData<ECRow>(row)) {
                return r->getInt(name());
            }
            return 0;
        }
    };

    struct DoubleEventConsoleColumn : public DoubleColumn {
        DoubleEventConsoleColumn(const std::string &name,
                                 const std::string &description,
                                 const ColumnOffsets &offsets)
            : DoubleColumn(name, description, offsets) {}

        [[nodiscard]] double getValue(Row row) const override {
            if (const auto *r = columnData<ECRow>(row)) {
                return r->getDouble(name());
            }
            return 0.0;
        }
    };

    struct TimeEventConsoleColumn : public TimeColumn {
        TimeEventConsoleColumn(const std::string &name,
                               const std::string &description,
                               const ColumnOffsets &offsets)
            : TimeColumn(name, description, offsets) {}

    private:
        [[nodiscard]] std::chrono::system_clock::time_point getRawValue(
            Row row) const override {
            if (const auto *r = columnData<ECRow>(row)) {
                return std::chrono::system_clock::from_time_t(
                    static_cast<std::time_t>(r->getDouble(name())));
            }
            return {};
        }
    };

    struct ListEventConsoleColumn : public ListColumn {
        ListEventConsoleColumn(const std::string &name,
                               const std::string &description,
                               const ColumnOffsets &offsets)
            : ListColumn(name, description, offsets) {}

        std::vector<std::string> getValue(
            Row row, const contact * /*auth_user*/,
            std::chrono::seconds /*timezone_offset*/) const override {
            if (const auto *r = columnData<ECRow>(row)) {
                auto result = r->getString(name());
                return result.empty() || result == "\002"
                           ? std::vector<std::string>()
                           : mk::split(result.substr(1), '\001');
            }
            return {};
        }

        [[nodiscard]] bool isNone(Row row) const {
            if (const auto *r = columnData<ECRow>(row)) {
                return r->getString(name()) == "\002";
            }
            return false;
        }
    };

    bool isAuthorizedForEvent(Row row, const contact *ctc) const;

private:
    bool isAuthorizedForEventViaContactGroups(
        const MonitoringCore::Contact *ctc, Row row, bool &result) const;
    bool isAuthorizedForEventViaHost(const MonitoringCore::Contact *ctc,
                                     Row row, bool &result) const;
};

#endif  // TableEventConsole_h
