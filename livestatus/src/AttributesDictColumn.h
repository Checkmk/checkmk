// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef ListAttributesColumn_h
#define ListAttributesColumn_h

#include "config.h"  // IWYU pragma: keep

#include <memory>
#include <string>

#include "CustomVarsDictFilter.h"
#include "DictColumn.h"
#include "Filter.h"
#include "MapUtils.h"
#include "Row.h"
#include "opids.h"

// TODO(sp): Is there a way to have a default value in the template parameters?
// Currently it is hardwired to the empty Attributes.
template <class T>
struct AttributesDictColumn : DictColumn::Callback<T> {
    using DictColumn::Callback<T>::Callback;
    ~AttributesDictColumn() override = default;
    [[nodiscard]] std::unique_ptr<Filter> createFilter(
        Filter::Kind kind, RelationalOperator relOp,
        const std::string &value) const override {
        return std::make_unique<CustomVarsDictFilter>(
            kind, this->name(), [this](Row row) { return this->getValue(row); },
            relOp, value);
    }
};

#endif
