// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef AttributeListAsIntColumn_h
#define AttributeListAsIntColumn_h

#include "config.h"  // IWYU pragma: keep

#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "Filter.h"
#include "IntColumn.h"
#include "contact_fwd.h"
#include "opids.h"
class Row;

class AttributeListAsIntColumn : public IntColumn {
public:
    using IntColumn::IntColumn;

    [[nodiscard]] std::unique_ptr<Filter> createFilter(
        Filter::Kind kind, RelationalOperator relOp,
        const std::string &value) const override;

    int32_t getValue(Row row, const contact *auth_user) const override;

    [[nodiscard]] std::vector<std::string> getAttributes(Row row) const;

    static std::vector<std::string> decode(unsigned long mask);
};

#endif  // AttributeListAsIntColumn_h
