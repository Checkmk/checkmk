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
#include "Row.h"

void ContactGroupsColumn::output(Row row, RowRenderer &r,
                                 const contact * /* auth_user */) const {
    ListRenderer l(r);
    for (auto cgm = getData(row); cgm != nullptr; cgm = cgm->next) {
        l.output(std::string(cgm->group_ptr->group_name));
    }
}

std::unique_ptr<ListColumn::Contains> ContactGroupsColumn::makeContains(
    const std::string &name) const {
    class ContainsContactGroup : public Contains {
    public:
        ContainsContactGroup(MonitoringCore::ContactGroup *element,
                             const ContactGroupsColumn *column)
            : _element(element), _column(column) {}

        bool operator()(Row row) override {
            for (auto cgm = _column->getData(row); cgm != nullptr;
                 cgm = cgm->next) {
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
        const ContactGroupsColumn *const _column;
    };

    return std::make_unique<ContainsContactGroup>(_mc->find_contactgroup(name),
                                                  this);
}

bool ContactGroupsColumn::isEmpty(Row row) const {
    return getData(row) == nullptr;
}

contactgroupsmember *ContactGroupsColumn::getData(Row row) const {
    if (auto p = columnData<contactgroupsmember *>(row)) {
        return *p;
    }
    return nullptr;
}
