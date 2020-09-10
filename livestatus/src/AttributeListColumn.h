// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef AttributeListColumn_h
#define AttributeListColumn_h

#include "config.h"  // IWYU pragma: keep

#include <chrono>
#include <memory>
#include <string>
#include <vector>

#include "AttributeListAsIntColumn.h"
#include "Filter.h"
#include "ListColumn.h"
#include "contact_fwd.h"
#include "opids.h"
class ColumnOffsets;
class Row;

class AttributeListColumn : public ListColumn {
public:
    AttributeListColumn(const std::string &name, const std::string &description,
                        const ColumnOffsets &offsets)
        : ListColumn(name, description, offsets)
        , _int_view_column(name, description, offsets) {}

    [[nodiscard]] std::unique_ptr<Filter> createFilter(
        Filter::Kind kind, RelationalOperator relOp,
        const std::string &value) const override;

    std::vector<std::string> getValue(
        Row row, const contact *auth_user,
        std::chrono::seconds timezone_offset) const override;

private:
    AttributeListAsIntColumn _int_view_column;
};

#endif  // AttributeListColumn_h
