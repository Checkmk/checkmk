// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef IntLambdaColumn_h
#define IntLambdaColumn_h

#include <functional>
#include <string>
#include "IntColumn.h"
#include "contact_fwd.h"
class Row;

class IntLambdaColumn : public IntColumn {
public:
    struct Constant;
    struct Reference;
    IntLambdaColumn(std::string name, std::string description,
                    std::function<int(Row)> gv)
        : IntColumn(std::move(name), std::move(description), {})
        , get_value_{gv} {}
    virtual ~IntLambdaColumn() = default;

    std::int32_t getValue(Row row,
                          const contact* /*auth_user*/) const override {
        return get_value_(row);
    }

private:
    std::function<int(Row)> get_value_;
};

struct IntLambdaColumn::Constant : IntLambdaColumn {
    Constant(std::string name, std::string description, int x)
        : IntLambdaColumn(std::move(name), std::move(description),
                          [x](Row /*row*/) { return x; }){};
};

struct IntLambdaColumn::Reference : IntLambdaColumn {
    Reference(std::string name, std::string description, int& x)
        : IntLambdaColumn(std::move(name), std::move(description),
                          [&x](Row /*row*/) { return x; }){};
};

#endif
