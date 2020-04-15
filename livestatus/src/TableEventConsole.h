// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TableEventConsole_h
#define TableEventConsole_h

#include "config.h"  // IWYU pragma: keep
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <ctime>
#include <map>
#include <string>
#include <utility>
#include <vector>
#include "Column.h"
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
class Query;

class TableEventConsole : public Table {
public:
    explicit TableEventConsole(MonitoringCore *mc);

    void answerQuery(Query *query) override;

    struct ECRow {
        std::map<std::string, std::string> _map;
        MonitoringCore::Host *_host;
    };

protected:
    static std::string getRaw(Row row, const Column &column,
                              const std::string &default_value) {
        if (auto r = column.columnData<ECRow>(row)) {
            auto it = r->_map.find(column.name());
            if (it != r->_map.end()) {
                return it->second;
            }
        }
        return default_value;
    }

    struct StringEventConsoleColumn : public StringColumn {
        StringEventConsoleColumn(const std::string &name,
                                 const std::string &description,
                                 const Column::Offsets &offsets)
            : StringColumn(name, description, offsets) {}

        [[nodiscard]] std::string getValue(Row row) const override {
            return getRaw(row, *this, "");
        }
    };

    struct IntEventConsoleColumn : public IntColumn {
        IntEventConsoleColumn(const std::string &name,
                              const std::string &description,
                              const Column::Offsets &offsets)
            : IntColumn(name, description, offsets) {}

        int32_t getValue(Row row,
                         const contact * /* auth_user */) const override {
            return static_cast<int32_t>(atol(getRaw(row, *this, "0").c_str()));
        }
    };

    struct DoubleEventConsoleColumn : public DoubleColumn {
        DoubleEventConsoleColumn(const std::string &name,
                                 const std::string &description,
                                 const Column::Offsets &offsets)
            : DoubleColumn(name, description, offsets) {}

        [[nodiscard]] double getValue(Row row) const override {
            return atof(getRaw(row, *this, "0").c_str());
        }
    };

    struct TimeEventConsoleColumn : public TimeColumn {
        TimeEventConsoleColumn(const std::string &name,
                               const std::string &description,
                               const Column::Offsets &offsets)
            : TimeColumn(name, description, offsets) {}

    private:
        [[nodiscard]] std::chrono::system_clock::time_point getRawValue(
            Row row) const override {
            return std::chrono::system_clock::from_time_t(
                static_cast<std::time_t>(
                    atof(getRaw(row, *this, "0").c_str())));
        }
    };

    struct ListEventConsoleColumn : public ListColumn {
        ListEventConsoleColumn(const std::string &name,
                               const std::string &description,
                               const Column::Offsets &offsets)
            : ListColumn(name, description, offsets) {}

        std::vector<std::string> getValue(
            Row row, const contact * /*auth_user*/,
            std::chrono::seconds /*timezone_offset*/) const override {
            auto result = getRaw(row, *this, "");
            return result.empty() || result == "\002"
                       ? std::vector<std::string>()
                       : mk::split(result.substr(1), '\001');
        }

        [[nodiscard]] bool isNone(Row row) const {
            return getRaw(row, *this, "") == "\002";
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
