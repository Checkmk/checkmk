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

#include "DownCommColumn.h"
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include "MonitoringCore.h"
#include "Renderer.h"

using std::make_unique;
using std::string;
using std::unique_ptr;
using std::vector;

void DownCommColumn::output(void *row, RowRenderer &r,
                            contact * /* auth_user */) {
    if (_is_downtime) {
        ListRenderer l(r);
        if (auto data = rowData<void>(row)) {
            for (const auto &downtime : downtimes_for_object(data)) {
                if (_with_info) {
                    SublistRenderer s(l);
                    s.output(downtime._id);
                    s.output(downtime._author);
                    s.output(downtime._comment);
                } else {
                    l.output(downtime._id);
                }
            }
        }
    } else {
        ListRenderer l(r);
        if (auto data = rowData<void>(row)) {
            for (const auto &comment : comments_for_object(data)) {
                if (_with_info) {
                    SublistRenderer s(l);
                    s.output(comment._id);
                    s.output(comment._author);
                    s.output(comment._comment);
                    if (_with_extra_info) {
                        s.output(comment._entry_type);
                        s.output(comment._entry_time);
                    }
                } else {
                    l.output(comment._id);
                }
            }
        }
    }
}

unique_ptr<ListColumn::Contains> DownCommColumn::makeContains(
    const string &name) {
    class ContainsDowntimeID : public Contains {
    public:
        ContainsDowntimeID(unsigned long element, DownCommColumn *column)
            : _element(element), _column(column) {}

        bool operator()(void *data) override {
            for (const auto &downtime : _column->downtimes_for_object(data)) {
                if (downtime._id == _element) {
                    return true;
                }
            }
            return false;
        }

    private:
        const unsigned long _element;
        DownCommColumn *_column;
    };

    class ContainsCommentID : public Contains {
    public:
        ContainsCommentID(unsigned long element, DownCommColumn *column)
            : _element(element), _column(column) {}

        bool operator()(void *data) override {
            for (const auto &comment : _column->comments_for_object(data)) {
                if (comment._id == _element) {
                    return true;
                }
            }
            return false;
        }

    private:
        const unsigned long _element;
        DownCommColumn *_column;
    };

    unsigned long id = strtoul(name.c_str(), nullptr, 10);
    if (_is_downtime) {
        return make_unique<ContainsDowntimeID>(id, this);
    }
    return make_unique<ContainsCommentID>(id, this);
}

bool DownCommColumn::isEmpty(void *data) {
    return _is_downtime ? downtimes_for_object(data).empty()
                        : comments_for_object(data).empty();
}

vector<DowntimeData> DownCommColumn::downtimes_for_object(void *data) const {
    return _is_service
               ? _mc->downtimes_for_service(
                     reinterpret_cast<MonitoringCore::Service *>(data))
               : _mc->downtimes_for_host(
                     reinterpret_cast<MonitoringCore::Host *>(data));
}

vector<CommentData> DownCommColumn::comments_for_object(void *data) const {
    return _is_service
               ? _mc->comments_for_service(
                     reinterpret_cast<MonitoringCore::Service *>(data))
               : _mc->comments_for_host(
                     reinterpret_cast<MonitoringCore::Host *>(data));
}
