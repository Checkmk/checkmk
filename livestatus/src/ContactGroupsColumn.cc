// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "ContactGroupsColumn.h"
#include "Row.h"

#ifdef CMC
#include "ContactList.h"
#include "Object.h"
#include "cmc.h"
#else
#include "nagios.h"
#endif

std::vector<std::string> ContactGroupsColumn::getValue(
    Row row, const contact * /*auth_user*/,
    std::chrono::seconds /*timezone_offset*/) const {
    std::vector<std::string> names;
#ifdef CMC
    if (auto object = columnData<Object>(row)) {
        for (const auto &name : object->_contact_list->groupNames()) {
            names.push_back(name);
        }
    }
#else
    if (auto p = columnData<contactgroupsmember *>(row)) {
        for (auto cgm = *p; cgm != nullptr; cgm = cgm->next) {
            names.emplace_back(cgm->group_ptr->group_name);
        }
    }
#endif
    return names;
}
