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

#ifndef TableTimeperiods_h
#define TableTimeperiods_h

#include "config.h"  // IWYU pragma: keep
#include <string>
#include "Table.h"
#ifdef CMC
class Timeperiod;
#else
#include "nagios.h"
extern timeperiod *timeperiod_list;
#endif

class MonitoringCore;
class Query;

class TableTimeperiods : public Table {
public:
    class IRow {
    public:
        virtual ~IRow() = default;
#ifdef CMC
        virtual const Timeperiod *getTimePeriod() const = 0;
#else
        virtual const timeperiod *getTimePeriod() const = 0;
#endif
    };
    explicit TableTimeperiods(MonitoringCore *mc);

    [[nodiscard]] std::string name() const override;
    [[nodiscard]] std::string namePrefix() const override;
    void answerQuery(Query *query) override;
};

#endif  // TableTimeperiods_h
