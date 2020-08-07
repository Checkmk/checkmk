// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "HostContactsColumn.h"

#include "Row.h"

#ifdef CMC
#include "ContactList.h"
#include "Object.h"
#include "cmc.h"
#else
#include <functional>
#include <unordered_set>

#include "nagios.h"
#endif

std::vector<std::string> HostContactsColumn::getValue(
    Row row, const contact* /*auth_user*/,
    std::chrono::seconds /*timezone_offset*/) const {
#ifdef CMC
    if (const auto* object = columnData<Object>(row)) {
        return object->_contact_list->contactNames();
    }
    return {};
#else
    std::unordered_set<std::string> names;
    if (const auto *hst = columnData<host>(row)) {
        for (auto *cm = hst->contacts; cm != nullptr; cm = cm->next) {
            names.insert(cm->contact_ptr->name);
        }
        for (auto *cgm = hst->contact_groups; cgm != nullptr; cgm = cgm->next) {
            for (auto *cm = cgm->group_ptr->members; cm != nullptr;
                 cm = cm->next) {
                names.insert(cm->contact_ptr->name);
            }
        }
    }
    return std::vector<std::string>(names.begin(), names.end());
#endif
}
