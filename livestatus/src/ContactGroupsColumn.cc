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

#include "ContactGroupsColumn.h"
#include "MonitoringCore.h"
#include "Renderer.h"

using std::make_unique;
using std::string;
using std::unique_ptr;

void ContactGroupsColumn::output(void *row, RowRenderer &r,
                                 contact * /* auth_user */) {
    ListRenderer l(r);
    if (auto data = static_cast<char *>(shiftPointer(row))) {
        for (contactgroupsmember *cgm =
                 *reinterpret_cast<contactgroupsmember **>(data + _offset);
             cgm != nullptr; cgm = cgm->next) {
            l.output(string(cgm->group_ptr->group_name));
        }
    }
}

unique_ptr<ListColumn::Contains> ContactGroupsColumn::makeContains(
    const string &name) {
    class ContainsContactGroup : public Contains {
    public:
        ContainsContactGroup(MonitoringCore::ContactGroup *element, int offset)
            : _element(element), _offset(offset) {}

        bool operator()(void *row) override {
            if (_element == nullptr || row == nullptr) {
                return false;
            }

            // row is already shifted (_indirect_offset is taken into account),
            // but _offset needs still to be accounted for
            for (contactgroupsmember *cgm =
                     *reinterpret_cast<contactgroupsmember **>(
                         reinterpret_cast<char *>(row) + _offset);
                 cgm != nullptr; cgm = cgm->next) {
                // TODO(sp) Remove evil cast below.
                if (cgm->group_ptr ==
                    reinterpret_cast<contactgroup *>(_element)) {
                    return true;
                }
            }
            return false;
        }

    private:
        MonitoringCore::ContactGroup *const _element;
        int _offset;
    };

    return make_unique<ContainsContactGroup>(_core->find_contactgroup(name),
                                             _offset);
}

bool ContactGroupsColumn::isEmpty(void *data) {
    contactgroupsmember *cgm = *reinterpret_cast<contactgroupsmember **>(
        reinterpret_cast<char *>(data) + _offset);
    return cgm == nullptr;
}
