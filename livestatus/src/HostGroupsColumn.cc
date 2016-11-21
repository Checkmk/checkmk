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

using std::make_unique;
using std::string;
using std::unique_ptr;

objectlist *HostgroupsColumn::getData(void *data) {
    if (data != nullptr) {
        data = shiftPointer(data);
        if (data != nullptr) {
            return *reinterpret_cast<objectlist **>(
                reinterpret_cast<char *>(data) + _offset);
        }
    }
    return nullptr;
}

void HostgroupsColumn::output(void *row, RowRenderer &r,
                              contact * /* auth_user */) {
    ListRenderer l(r);
    for (objectlist *list = getData(row); list != nullptr; list = list->next) {
        hostgroup *sg = reinterpret_cast<hostgroup *>(list->object_ptr);
        l.output(string(sg->group_name));
    }
}

unique_ptr<ListColumn::Contains> HostgroupsColumn::makeContains(
    const string &name) {
    class ContainsHostGroup : public Contains {
    public:
        ContainsHostGroup(hostgroup *element, int offset)
            : _element(element), _offset(offset) {}

        bool operator()(void *row) override {
            if (_element == nullptr || row == nullptr) {
                return false;
            }

            // row is already shifted (_indirect_offset is taken into account),
            // but _offset needs still to be accounted for
            for (objectlist *list = *reinterpret_cast<objectlist **>(
                     reinterpret_cast<char *>(row) + _offset);
                 list != nullptr; list = list->next) {
                if (list->object_ptr == _element) {
                    return true;
                }
            }
            return false;
        }

    private:
        hostgroup *const _element;
        const int _offset;
    };

    return make_unique<ContainsHostGroup>(
        find_hostgroup(const_cast<char *>(name.c_str())), _offset);
}

bool HostgroupsColumn::isEmpty(void *data) {
    objectlist *list = *reinterpret_cast<objectlist **>(
        reinterpret_cast<char *>(data) + _offset);
    return list == nullptr;
}
