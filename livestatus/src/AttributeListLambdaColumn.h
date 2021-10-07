// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef AttributeListLambdaColumn_h
#define AttributeListLambdaColumn_h

#include "config.h"  // IWYU pragma: keep

#include <functional>
#include <memory>
#include <string>
#include <utility>

#include "AttributeListAsIntColumn.h"
#include "AttributeListColumnUtils.h"
#include "IntColumn.h"
#include "IntFilter.h"
#include "IntLambdaColumn.h"
#include "ListColumn.h"

template <class T, int32_t Default = 0>
struct AttributeBitmaskLambdaColumn : IntColumn::Callback<T, Default> {
    using IntColumn::Callback<T, Default>::Callback;
    ~AttributeBitmaskLambdaColumn() override = default;

    [[nodiscard]] std::unique_ptr<Filter> createFilter(
        Filter::Kind kind, RelationalOperator relOp,
        const std::string& value) const override {
        return std::make_unique<IntFilter>(
            kind, this->name(),
            [this](Row row, const contact* auth_user) {
                return this->getValue(row, auth_user);
            },
            relOp, column::attribute_list::refValueFor(value, this->logger()));
    }
};

// TODO(ml): This could likely be simplified with a dict column.
//
//           See also
//             - `TableContacts::GetCustomAttribute` and
//             - `TableContacts::GetCustomAttributeElem`
//           for an example of a dict column without pointer arithmetic.
template <class T>
class AttributeListColumn2 : public deprecated::ListColumn {
public:
    AttributeListColumn2(const std::string& name,
                         const std::string& description,
                         const ColumnOffsets& offsets,
                         const AttributeBitmaskLambdaColumn<T>& bitmask_col)
        : deprecated::ListColumn(name, description, offsets)
        , bitmask_col_{bitmask_col} {}

    [[nodiscard]] std::unique_ptr<Filter> createFilter(
        Filter::Kind kind, RelationalOperator relOp,
        const std::string& value) const override {
        return bitmask_col_.createFilter(kind, relOp, value);
    }
    [[nodiscard]] std::vector<std::string> getValue(
        Row row, const contact* /*auth_user*/,
        std::chrono::seconds /*timezone_offset*/) const override {
        return column::attribute_list::decode(
            bitmask_col_.getValue(row, nullptr));
    }

private:
    AttributeBitmaskLambdaColumn<T> bitmask_col_;
};

#endif
