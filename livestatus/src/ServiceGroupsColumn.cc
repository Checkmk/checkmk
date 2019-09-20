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
#include "Row.h"

#ifdef CMC
#include "Object.h"
#include "ObjectGroup.h"
#include "cmc.h"
#else
#include "auth.h"
#include "nagios.h"
#endif

std::vector<std::string> ServiceGroupsColumn::getValue(
    Row row, const contact *auth_user,
    std::chrono::seconds /*timezone_offset*/) const {
    std::vector<std::string> group_names;
#ifdef CMC
    if (auto object = columnData<Object>(row)) {
        for (const auto &og : object->_groups) {
            if (og->isContactAuthorized(auth_user)) {
                group_names.push_back(og->name());
            }
        }
    }
#else
    if (auto p = columnData<objectlist *>(row)) {
        for (objectlist *list = *p; list != nullptr; list = list->next) {
            auto sg = static_cast<servicegroup *>(list->object_ptr);
            if (is_authorized_for_service_group(_mc, sg, auth_user)) {
                group_names.emplace_back(sg->group_name);
            }
        }
    }
#endif
    return group_names;
}
