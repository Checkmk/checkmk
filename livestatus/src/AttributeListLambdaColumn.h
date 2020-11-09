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
template <class T, int32_t Default = 0>
class AttributeBitmaskLambdaColumn : public AttributeListAsIntColumn {
public:
    AttributeBitmaskLambdaColumn(std::string name, std::string description,
                                 ColumnOffsets offsets,
                                 std::function<int(const T&)> f)
        : AttributeListAsIntColumn(std::move(name), std::move(description),
                                   std::move(offsets))
        , get_value_{std::move(f)} {}
    ~AttributeBitmaskLambdaColumn() override = default;

    std::int32_t getValue(Row row,
                          const contact* /*auth_user*/) const override {
        return getValue(row);
    }

    [[nodiscard]] std::int32_t getValue(Row row) const {
        const T* data = columnData<T>(row);
        return data == nullptr ? Default : get_value_(*data);
    }

private:
    std::function<int(const T&)> get_value_;
};

template <class T>
class AttributeListColumn2 : public ListColumn {
public:
    AttributeListColumn2(std::string name, std::string description,
                         ColumnOffsets offsets,
                         const AttributeBitmaskLambdaColumn<T>& bitmask_col)
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
    AttributeBitmaskLambdaColumn<T> bitmask_col_;
};

#endif
