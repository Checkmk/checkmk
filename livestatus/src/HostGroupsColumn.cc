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

#include "HostGroupsColumn.h"
#include "Renderer.h"
#include "Row.h"

void HostGroupsColumn::output(Row row, RowRenderer &r,
                              const contact * /* auth_user */) const {
    ListRenderer l(r);
    for (objectlist *list = getData(row); list != nullptr; list = list->next) {
        auto sg = static_cast<hostgroup *>(list->object_ptr);
        l.output(std::string(sg->group_name));
    }
}

std::unique_ptr<ListColumn::Contains> HostGroupsColumn::makeContains(
    const std::string &name) const {
    class ContainsHostGroup : public Contains {
    public:
        ContainsHostGroup(hostgroup *element, const HostGroupsColumn *column)
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
        hostgroup *const _element;
        const HostGroupsColumn *const _column;
    };

    return std::make_unique<ContainsHostGroup>(
        find_hostgroup(const_cast<char *>(name.c_str())), this);
}

bool HostGroupsColumn::isEmpty(Row row) const {
    return getData(row) == nullptr;
}

objectlist *HostGroupsColumn::getData(Row row) const {
    if (auto p = columnData<objectlist *>(row)) {
        return *p;
    }
    return nullptr;
}
