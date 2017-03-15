// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#ifndef TableEventConsole_h
#define TableEventConsole_h

#include "config.h"  // IWYU pragma: keep
#include <sys/types.h>
#include <algorithm>
#include <cstdint>
#include <cstdlib>
#include <functional>
#include <map>
#include <memory>
#include <string>
#include <vector>
#include "DoubleColumn.h"
#include "IntColumn.h"
#include "ListColumn.h"
#include "MonitoringCore.h"
#include "Renderer.h"
#include "StringColumn.h"
#include "StringUtils.h"
#include "Table.h"
#include "TimeColumn.h"
class Query;

#ifdef CMC
#include "cmc.h"  // for contact
#else
#include "nagios.h"  // for contact
#endif

class TableEventConsole : public Table {
public:
    explicit TableEventConsole(MonitoringCore *mc);

    void answerQuery(Query *) override;

    struct Row {
        std::map<std::string, std::string> _map;
        MonitoringCore::Host *_host;
    };

protected:
    template <typename T>
    class EventConsoleColumn {
        std::string _name;
        T _default_value;
        std::function<T(std::string)> _f;

    public:
        EventConsoleColumn(std::string name, T default_value,
                           std::function<T(std::string)> f)
            : _name(name), _default_value(default_value), _f(f) {}

        std::string getRaw(void *row) const {
            auto r = static_cast<Row *>(row);
            return r == nullptr ? "" : r->_map.at(_name);
        }

        T getValue(void *row) const {
            auto r = static_cast<Row *>(row);
            return r == nullptr ? _default_value : _f(r->_map.at(_name));
        }
    };

    class StringEventConsoleColumn : public StringColumn {
        EventConsoleColumn<std::string> _ecc;

    public:
        StringEventConsoleColumn(const std::string &name,
                                 const std::string &description)
            : StringColumn(name, description, -1, -1, -1)
            , _ecc(name, std::string(), [](std::string x) { return x; }) {}

        std::string getValue(void *row) const override {
            return _ecc.getValue(row);
        }
    };

    class IntEventConsoleColumn : public IntColumn {
        EventConsoleColumn<int32_t> _ecc;

    public:
        IntEventConsoleColumn(const std::string &name,
                              const std::string &description)
            : IntColumn(name, description, -1, -1, -1)
            , _ecc(name, 0, [](std::string x) {
                return static_cast<int32_t>(atol(x.c_str()));
            }) {}

        int32_t getValue(void *row, contact * /* auth_user */) override {
            return _ecc.getValue(row);
        }
    };

    class DoubleEventConsoleColumn : public DoubleColumn {
        EventConsoleColumn<double> _ecc;

    public:
        DoubleEventConsoleColumn(const std::string &name,
                                 const std::string &description)
            : DoubleColumn(name, description, -1, -1, -1)
            , _ecc(name, 0, [](std::string x) { return atof(x.c_str()); }) {}

        double getValue(void *row) override { return _ecc.getValue(row); }
    };

    class TimeEventConsoleColumn : public TimeColumn {
        EventConsoleColumn<int32_t> _ecc;

    public:
        TimeEventConsoleColumn(const std::string &name,
                               const std::string &description)
            : TimeColumn(name, description, -1, -1, -1)
            , _ecc(name, 0, [](std::string x) {
                return static_cast<int32_t>(atof(x.c_str()));
            }) {}

        int32_t getValue(void *row, contact * /* auth_user */) override {
            return _ecc.getValue(row);
        }
    };

    class ListEventConsoleColumn : public ListColumn {
        typedef std::vector<std::string> _column_t;
        EventConsoleColumn<_column_t> _ecc;

    public:
        ListEventConsoleColumn(const std::string &name,
                               const std::string &description)
            : ListColumn(name, description, -1, -1, -1)
            , _ecc(name, _column_t(), [](std::string x) {
                return x.empty() || x == "\002"
                           ? _column_t()
                           : mk::split(x.substr(1), '\001');
            }) {}

        bool isNone(void *row) { return _ecc.getRaw(row) == "\002"; }

        _column_t getValue(void *row) { return _ecc.getValue(row); }

        void output(void *row, RowRenderer &r,
                    contact * /* auth_user */) override {
            ListRenderer l(r);
            for (const auto &elem : _ecc.getValue(row)) {
                l.output(elem);
            }
        }

        bool isEmpty(void *row) override { return _ecc.getValue(row).empty(); }

        std::unique_ptr<Contains> makeContains(
            const std::string &name) override {
            class ContainsElem : public Contains {
            public:
                ContainsElem(const std::string &name,
                             const EventConsoleColumn<_column_t> &ecc)
                    : _name(name), _ecc(ecc) {}
                bool operator()(void *row) override {
                    const _column_t &values = _ecc.getValue(row);
                    return std::find(values.begin(), values.end(), _name) !=
                           values.end();
                }

            private:
                std::string _name;
                const EventConsoleColumn<_column_t> &_ecc;
            };
            return std::make_unique<ContainsElem>(name, _ecc);
        }
    };

    bool isAuthorizedForEvent(contact *ctc, void *data);

private:
    bool isAuthorizedForEventViaContactGroups(MonitoringCore::Contact *ctc,
                                              Row *row, bool &result);
    bool isAuthorizedForEventViaHost(MonitoringCore::Contact *ctc, Row *row,
                                     bool &result);
};

#endif  // TableEventConsole_h
