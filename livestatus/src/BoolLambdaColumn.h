// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef BoolLambdaColumn_h
#define BoolLambdaColumn_h

#include <functional>
#include <string>
#include "IntColumn.h"
#include "contact_fwd.h"
class Row;

class BoolLambdaColumn : public IntColumn {
public:
    BoolLambdaColumn(std::string name, std::string description,
                     std::function<bool(Row)> f)
        : IntColumn(std::move(name), std::move(description), {})
        , get_value_{f} {}
    virtual ~BoolLambdaColumn() = default;

    std::int32_t getValue(Row row,
                          const contact* /*auth_user*/) const override {
        return get_value_(row) ? 1 : 0;
    }

private:
    std::function<bool(Row)> get_value_;
};

#endif  // BoolLambdaColumn.h
