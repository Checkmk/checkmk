// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "ContactGroupsMemberColumn.h"
#include "Row.h"

#ifdef CMC
#include "ContactGroup.h"
#else
#include "nagios.h"
#endif

std::vector<std::string> ContactGroupsMemberColumn::getValue(
    Row row, const contact* /*auth_user*/,
    std::chrono::seconds /*timezone_offset*/) const {
#ifdef CMC
    if (auto cg = columnData<ContactGroup>(row)) {
        return cg->contactNames();
    }
    return {};
#else
    std::vector<std::string> names;
    if (auto cg = columnData<contactgroup>(row)) {
        for (auto cm = cg->members; cm != nullptr; cm = cm->next) {
            names.emplace_back(cm->contact_ptr->name);
        }
    }
    return names;
#endif
}
