// .------------------------------------------------------------------------.
// |                ____ _               _        __  __ _  __              |
// |               / ___| |__   ___  ___| | __   |  \/  | |/ /              |
// |              | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /               |
// |              | |___| | | |  __/ (__|   <    | |  | | . \               |
// |               \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\              |
// |                                        |_____|                         |
// |             _____       _                       _                      |
// |            | ____|_ __ | |_ ___ _ __ _ __  _ __(_)___  ___             |
// |            |  _| | '_ \| __/ _ \ '__| '_ \| '__| / __|/ _ \            |
// |            | |___| | | | ||  __/ |  | |_) | |  | \__ \  __/            |
// |            |_____|_| |_|\__\___|_|  | .__/|_|  |_|___/\___|            |
// |                                     |_|                                |
// |                     _____    _ _ _   _                                 |
// |                    | ____|__| (_) |_(_) ___  _ __                      |
// |                    |  _| / _` | | __| |/ _ \| '_ \                     |
// |                    | |__| (_| | | |_| | (_) | | | |                    |
// |                    |_____\__,_|_|\__|_|\___/|_| |_|                    |
// |                                                                        |
// | mathias-kettner.com                                 mathias-kettner.de |
// '------------------------------------------------------------------------'
//  This file is part of the Check_MK Enterprise Edition (CEE).
//  Copyright by Mathias Kettner and Mathias Kettner GmbH.  All rights reserved.
//
//  Distributed under the Check_MK Enterprise License.
//
//  You should have  received  a copy of the Check_MK Enterprise License
//  along with Check_MK. If not, email to mk@mathias-kettner.de
//  or write to the postal address provided at www.mathias-kettner.de

#ifndef DynamicRRDColumn_h
#define DynamicRRDColumn_h

#include "config.h"  // IWYU pragma: keep
#include <memory>
#include <string>
#include "Column.h"
#include "DynamicColumn.h"
#include "opids.h"
class Filter;
class MonitoringCore;

class DynamicRRDColumn : public DynamicColumn {
public:
    DynamicRRDColumn(const std::string &name, const std::string &description,
                     MonitoringCore *mc, const Column::Offsets &);

    [[nodiscard]] std::unique_ptr<Filter> createFilter(
        RelationalOperator relOp, const std::string &value) const;

    std::unique_ptr<Column> createColumn(
        const std::string &name, const std::string &arguments) override = 0;
    MonitoringCore *core();

protected:
    struct Args {
        std::string rpn;
        long int start_time;
        long int end_time;
        int resolution;
        int max_entries;
    };
    [[nodiscard]] Args parse_args(const std::string &arguments) const;

private:
    MonitoringCore *_mc;
    void invalid(const std::string &message) const;
};

#endif  // DynamicRRDColumn_h
