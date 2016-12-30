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
#include <cstdlib>
#include <ctime>
#include <utility>
#include "DowntimeOrComment.h"
#include "DowntimesOrComments.h"
#include "Renderer.h"

using std::make_unique;
using std::string;
using std::unique_ptr;

void DownCommColumn::output(void *row, RowRenderer &r,
                            contact * /* auth_user */) {
    ListRenderer l(r);
    if (auto data = rowData<void>(row)) {
        for (const auto &entry : _holder) {
            unsigned long id = entry.first;
            DowntimeOrComment *dt = entry.second.get();
            if (match(dt, data)) {
                if (_with_info) {
                    SublistRenderer s(l);
                    s.output(id);
                    s.output(dt->_author_name);
                    s.output(dt->_comment);
                    if (_with_extra_info && !_is_downtime) {
                        s.output(static_cast<Comment *>(dt)->_entry_type);
                        s.output(dt->_entry_time);
                    }
                } else {
                    l.output(id);
                }
            }
        }
    }
}

bool DownCommColumn::match(DowntimeOrComment *dt, void *data) {
    // TableDownComm always enumerates dowtimes/comments for both hosts and
    // services, regardless of what we are interested in. So we have to skip the
    // ones which have the wrong kind.
    if (_is_service != (dt->_is_service != 0)) {
        return false;
    }

    if (_is_service) {
        service *s = static_cast<service *>(data);
        return dt->_service != nullptr &&  // just to be sure...
               dt->_service->host_name == s->host_name &&
               dt->_service->description == s->description;
    }
    host *h = static_cast<host *>(data);
    return dt->_host->name == h->name;
}

unique_ptr<ListColumn::Contains> DownCommColumn::makeContains(
    const string &name) {
    class ContainsDownCommID : public Contains {
    public:
        ContainsDownCommID(unsigned long element,
                           const DowntimesOrComments &holder)
            : _element(element), _holder(holder) {}

        bool operator()(void *row) override {
            DowntimeOrComment *dt = _holder.findEntry(_element);
            return dt != nullptr &&
                   (dt->_service == static_cast<service *>(row) ||
                    (dt->_service == nullptr &&
                     dt->_host == static_cast<host *>(row)));
        }

    private:
        const unsigned long _element;
        const DowntimesOrComments &_holder;
    };

    return make_unique<ContainsDownCommID>(strtoul(name.c_str(), nullptr, 10),
                                           _holder);
}

bool DownCommColumn::isEmpty(void *data) {
    if (data == nullptr) {
        return true;
    }

    for (const auto &entry : _holder) {
        DowntimeOrComment *dt = entry.second.get();
        if (dt->_service == data ||
            (dt->_service == nullptr && dt->_host == data)) {
            return false;
        }
    }
    return true;  // empty
}
