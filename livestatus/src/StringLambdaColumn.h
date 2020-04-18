// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef StringLambdaColumn_h
#define StringLambdaColumn_h

#include "config.h"  // IWYU pragma: keep
#include <functional>
#include <string>
#include "StringColumn.h"
class Row;

class StringLambdaColumn : public StringColumn {
public:
    struct Constant;
    struct Reference;
    StringLambdaColumn(std::string name, std::string description,
                       std::function<std::string(Row)> gv)
        : StringColumn(std::move(name), std::move(description), {})
        , get_value_(gv) {}
    virtual ~StringLambdaColumn() = default;
    std::string getValue(Row row) const override { return get_value_(row); }

private:
    std::function<std::string(Row)> get_value_;
};

struct StringLambdaColumn::Constant : StringLambdaColumn {
    Constant(std::string name, std::string description, const std::string& x)
        : StringLambdaColumn(std::move(name), std::move(description),
                             [x](Row /*row*/) { return x; }){};
};

struct StringLambdaColumn::Reference : StringLambdaColumn {
    Reference(std::string name, std::string description, const std::string& x)
        : StringLambdaColumn(std::move(name), std::move(description),
                             [&x](Row /*row*/) { return x; }){};
};

#endif
