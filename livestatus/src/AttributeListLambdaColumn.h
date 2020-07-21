// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef AttributeListLambdaColumn_h
#define AttributeListLambdaColumn_h

#include "config.h"  // IWYU pragma: keep

#include <functional>
#include <string>
#include <utility>

#include "AttributeListAsIntColumn.h"
#include "ListColumn.h"

// TODO(ml): This could likely be simplified with a dict column.
//
//           See also
//             - `TableContacts::GetCustomAttribute` and
//             - `TableContacts::GetCustomAttributeElem`
//           for an example of a dict column without pointer arithmetic.

class AttributeBitmaskLambdaColumn : public AttributeListAsIntColumn {
public:
    AttributeBitmaskLambdaColumn(std::string name, std::string description,
                                 Offsets offsets, std::function<int(Row)> f)
        : AttributeListAsIntColumn(std::move(name), std::move(description),
                                   std::move(offsets))
        , get_value_{std::move(f)} {}
    ~AttributeBitmaskLambdaColumn() override = default;
    std::int32_t getValue(Row row,
                          const contact* /*auth_user*/) const override {
        return getValue(row);
    }
    [[nodiscard]] std::int32_t getValue(Row row) const {
        return get_value_(row);
    }

private:
    std::function<int(Row)> get_value_;
};

class AttributeListColumn2 : public ListColumn {
public:
    AttributeListColumn2(std::string name, std::string description,
                         Offsets offsets,
                         const AttributeBitmaskLambdaColumn& bitmask_col)
        : ListColumn(std::move(name), std::move(description),
                     std::move(offsets))
        , bitmask_col_{bitmask_col} {}

    [[nodiscard]] std::unique_ptr<Filter> createFilter(
        Filter::Kind kind, RelationalOperator relOp,
        const std::string& value) const override {
        return bitmask_col_.createFilter(kind, relOp, value);
    }
    std::vector<std::string> getValue(
        Row row, const contact* /*auth_user*/,
        std::chrono::seconds /*timezone_offset*/) const override {
        return getValue(row);
    }
    [[nodiscard]] std::vector<std::string> getValue(Row row) const {
        return AttributeListAsIntColumn::decode(bitmask_col_.getValue(row));
    }

private:
    AttributeBitmaskLambdaColumn bitmask_col_;
};

#endif
