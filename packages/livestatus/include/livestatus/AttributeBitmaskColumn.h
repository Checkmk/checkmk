// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef AttributeBitmaskColumn_h
#define AttributeBitmaskColumn_h

#include <bitset>
#include <cstdint>
#include <map>
#include <memory>
#include <string>

#include "livestatus/AttributeListColumn.h"
#include "livestatus/Filter.h"
#include "livestatus/IntColumn.h"
#include "livestatus/Row.h"
#include "livestatus/opids.h"
class Logger;
class IntFilter;

template <typename T, int32_t Default = 0>
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
