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

#ifndef RRDColumn_h
#define RRDColumn_h

#include "config.h"  // IWYU pragma: keep
#include <chrono>
#include <ctime>
#include <string>
#include <vector>
#include "Column.h"
#include "ListColumn.h"
#include "contact_fwd.h"
class MonitoringCore;
class Row;
class RowRenderer;

class RRDColumn : public ListColumn {
public:
    RRDColumn(const std::string &name, const std::string &description,
              const Column::Offsets &, MonitoringCore *mc, std::string rpn,
              time_t start_time, time_t end_time, int resolution,
              int max_entries);

    void output(Row row, RowRenderer &r, const contact *auth_user,
                std::chrono::seconds timezone_offset) const override;

    std::vector<std::string> getValue(
        Row row, const contact *auth_user,
        std::chrono::seconds timezone_offset) const override;

    enum class Table { objects, services, hosts };

private:
    [[nodiscard]] virtual const void *getObject(Row row) const = 0;
    [[nodiscard]] virtual Table table() const = 0;

    MonitoringCore *_mc;
    std::string _rpn;
    time_t _start_time;
    time_t _end_time;
    int _resolution;
    int _max_entries;

    struct Data {
        std::chrono::system_clock::time_point start;
        std::chrono::system_clock::time_point end;
        unsigned long step{};
        std::vector<double> values;
    };

    [[nodiscard]] Data getData(Row row) const;
};

#endif  // RRDColumn_h
