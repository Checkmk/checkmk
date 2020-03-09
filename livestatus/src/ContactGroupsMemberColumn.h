// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef ContactGroupsMemberColumn_h
#define ContactGroupsMemberColumn_h

#include "config.h"  // IWYU pragma: keep
#include <chrono>
#include <string>
#include <vector>
#include "ListColumn.h"
#include "contact_fwd.h"
class Row;

class ContactGroupsMemberColumn : public ListColumn {
public:
    using ListColumn::ListColumn;
    std::vector<std::string> getValue(
        Row row, const contact* auth_user,
        std::chrono::seconds timezone_offset) const override;
};

#endif  // ContactGroupsMemberColumn_h
