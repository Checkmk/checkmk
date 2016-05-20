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
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#ifndef TableEventConsole_h
#define TableEventConsole_h

#include "config.h"  // IWYU pragma: keep
#include <stdlib.h>
#include <sys/types.h>
#include <cstdint>
#include <functional>
#include <map>
#include <string>
#include <vector>
#include "DoubleColumn.h"
#include "IntColumn.h"
#include "ListColumn.h"
#include "OffsetTimeColumn.h"
#include "Query.h"
#include "StringColumn.h"
#include "Table.h"

class TableEventConsole : public Table {
public:
    void answerQuery(Query *) override;

protected:
    typedef std::map<std::string, std::string> _row_t;

    // TODO(sp) Move this to some helper.
    static std::vector<std::string> split(std::string str, char delimiter);

    template <typename T>
    class EventConsoleColumn {
        std::string _name;
        T _default_value;
        std::function<T(std::string)> _f;

    public:
        EventConsoleColumn(std::string name, T default_value,
                           std::function<T(std::string)> f)
            : _name(name), _default_value(default_value), _f(f) {}

        T getValue(void *data) const {
            auto row = static_cast<_row_t *>(data);
            return row == nullptr ? _default_value : _f(row->at(_name));
        }
    };

    class StringEventConsoleColumn : public StringColumn {
        EventConsoleColumn<std::string> _ecc;

    public:
        StringEventConsoleColumn(std::string name, std::string description)
            : StringColumn(name, description, -1, -1)
            , _ecc(name, std::string(), [](std::string x) { return x; }) {}

        std::string getValue(void *data) const override {
            return _ecc.getValue(data);
        }
    };

    class IntEventConsoleColumn : public IntColumn {
        EventConsoleColumn<int32_t> _ecc;

    public:
        IntEventConsoleColumn(std::string name, std::string description)
            : IntColumn(name, description, -1, -1)
            , _ecc(name, 0, [](std::string x) {
                return static_cast<int32_t>(atol(x.c_str()));
            }) {}

        int32_t getValue(void *data, Query *) override {
            return _ecc.getValue(data);
        }
    };

    class DoubleEventConsoleColumn : public DoubleColumn {
        EventConsoleColumn<double> _ecc;

    public:
        DoubleEventConsoleColumn(std::string name, std::string description)
            : DoubleColumn(name, description, -1, -1)
            , _ecc(name, 0, [](std::string x) { return atof(x.c_str()); }) {}

        double getValue(void *data) override { return _ecc.getValue(data); }
    };

    class TimeEventConsoleColumn : public OffsetTimeColumn {
        EventConsoleColumn<int32_t> _ecc;

    public:
        TimeEventConsoleColumn(std::string name, std::string description)
            : OffsetTimeColumn(name, description, -1, -1)
            , _ecc(name, 0, [](std::string x) {
                return static_cast<int32_t>(atof(x.c_str()));
            }) {}

        int32_t getValue(void *data, Query *) override {
            return _ecc.getValue(data);
        }
    };

    class ListEventConsoleColumn : public ListColumn {
        typedef std::vector<std::string> _column_t;
        EventConsoleColumn<_column_t> _ecc;

    public:
        ListEventConsoleColumn(std::string name, std::string description)
            : ListColumn(name, description, -1, -1)
            , _ecc(name, _column_t(), [](std::string x) {
                return x.empty() || x == "\002" ? _column_t()
                                                : split(x.substr(1), '\001');
            }) {}

        void output(void *data, Query *query) override {
            query->outputBeginList();
            bool first = true;
            for (const auto &elem : _ecc.getValue(data)) {
                printf("-------------------- [%s]\n", elem.c_str());
                if (first) {
                    first = false;
                } else {
                    query->outputListSeparator();
                }
                query->outputString(elem.c_str());
            }
            query->outputEndList();
        }

        bool isEmpty(void *data) override {
            return _ecc.getValue(data).empty();
        }

        // TODO(sp) We should probably rename the methods below and actually
        // implement them here for real.
        void *getNagiosObject(char *) override { return nullptr; }
        bool isNagiosMember(void *, void *) override { return false; }
    };
};

#endif  // TableEventConsole_h
