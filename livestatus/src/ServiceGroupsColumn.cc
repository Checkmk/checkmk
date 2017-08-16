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

#include "ServiceGroupsColumn.h"
#include "Column.h"
#include "Renderer.h"
#include "Row.h"

using std::make_unique;
using std::string;
using std::unique_ptr;

void ServiceGroupsColumn::output(Row row, RowRenderer &r,
                                 contact * /* auth_user */) {
    ListRenderer l(r);
    for (objectlist *list = getData(row); list != nullptr; list = list->next) {
        auto sg = static_cast<servicegroup *>(list->object_ptr);
        l.output(string(sg->group_name));
    }
}

unique_ptr<ListColumn::Contains> ServiceGroupsColumn::makeContains(
    const string &name) const {
    class ContainsServiceGroup : public Contains {
    public:
        ContainsServiceGroup(servicegroup *element,
                             const ServiceGroupsColumn *column)
            : _element(element), _column(column) {}

        bool operator()(Row row) override {
            for (auto list = _column->getData(row); list != nullptr;
                 list = list->next) {
                if (list->object_ptr == _element) {
                    return true;
                }
            }
            return false;
        }

    private:
        servicegroup *const _element;
        const ServiceGroupsColumn *const _column;
    };

    return make_unique<ContainsServiceGroup>(
        find_servicegroup(const_cast<char *>(name.c_str())), this);
}

bool ServiceGroupsColumn::isEmpty(Row row) const {
    return getData(row) == nullptr;
}

objectlist *ServiceGroupsColumn::getData(Row row) const {
    if (auto p = columnData<void>(row)) {
        return *offset_cast<objectlist *>(p, _offset);
    }
    return nullptr;
}
