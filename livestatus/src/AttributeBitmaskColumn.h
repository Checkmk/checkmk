// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef AttributeBitmaskColumn_h
#define AttributeBitmaskColumn_h

#include "config.h"  // IWYU pragma: keep

#include <bitset>
#include <cstdint>
#include <map>
#include <memory>
#include <string>

#include "AttributeListColumn.h"
#include "Filter.h"
#include "IntColumn.h"
#include "Row.h"
#include "contact_fwd.h"
#include "opids.h"
class Logger;
class IntFilter;

template <class T, int32_t Default = 0>
struct AttributeBitmaskColumn : IntColumn<T, Default> {
    using IntColumn<T, Default>::IntColumn;

    [[nodiscard]] std::unique_ptr<Filter> createFilter(
        Filter::Kind kind, RelationalOperator relOp,
        const std::string &value) const override {
        return std::make_unique<IntFilter>(
            kind, this->name(),
            [this](Row row, const User &user) {
                return this->getValue(row, user);
            },
            relOp, column::attribute_list::refValueFor(value, this->logger()));
    }
};

#endif
