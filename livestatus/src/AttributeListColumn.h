// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef AttributeListColumn_h
#define AttributeListColumn_h

#include "config.h"  // IWYU pragma: keep

#include <chrono>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "AttributeBitmaskColumn.h"
#include "Filter.h"
#include "IntColumn.h"
#include "ListColumn.h"
#include "Row.h"
#include "contact_fwd.h"
#include "opids.h"
class Logger;
class ColumnOffsets;
class IntFilter;

// TODO(ml): This could likely be simplified with a dict column.
//
//           See also
//             - `TableContacts::GetCustomAttribute` and
//             - `TableContacts::GetCustomAttributeElem`
//           for an example of a dict column without pointer arithmetic.
template <class T>
class AttributeListColumn : public deprecated::ListColumn {
public:
    AttributeListColumn(
        const std::string& name, const std::string& description,
        const ColumnOffsets& offsets,
        const typename AttributeBitmaskColumn<T>::function_type& f)
        : deprecated::ListColumn(name, description, offsets)
        , bitmask_col_{name, description, offsets, f} {}

    [[nodiscard]] std::unique_ptr<Filter> createFilter(
        Filter::Kind kind, RelationalOperator relOp,
        const std::string& value) const override {
        return bitmask_col_.createFilter(kind, relOp, value);
    }
    [[nodiscard]] std::vector<std::string> getValue(
        Row row, const contact* /*auth_user*/,
        std::chrono::seconds /*timezone_offset*/) const override {
        return column::attribute_list::detail::decode(
            bitmask_col_.getValue(row, nullptr));
    }

private:
    AttributeBitmaskColumn<T> bitmask_col_;
};

#endif
