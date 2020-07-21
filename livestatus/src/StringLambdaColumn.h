// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef StringLambdaColumn_h
#define StringLambdaColumn_h

#include "config.h"  // IWYU pragma: keep

#include <functional>
#include <string>
#include <utility>

#include "StringColumn.h"
class Row;

template <class T>
class StringLambdaColumn : public StringColumn {
public:
    struct Constant;
    struct Reference;
    StringLambdaColumn(std::string name, std::string description,
                       Offsets offsets, std::function<std::string(const T*)> gv)
        : StringColumn(std::move(name), std::move(description),
                       std::move(offsets))
        , get_value_(std::move(gv)) {}

    ~StringLambdaColumn() override = default;

    [[nodiscard]] std::string getValue(Row row) const override {
        return get_value_(columnData<T>(row));
    }

private:
    std::function<std::string(const T*)> get_value_;
};

template <class T>
struct StringLambdaColumn<T>::Constant : StringLambdaColumn {
    Constant(std::string name, std::string description, const std::string& x)
        : StringLambdaColumn(std::move(name), std::move(description), {},
                             [x](const T* /*t*/) { return x; }){};
};

template <class T>
struct StringLambdaColumn<T>::Reference : StringLambdaColumn {
    Reference(std::string name, std::string description, const std::string& x)
        : StringLambdaColumn(std::move(name), std::move(description), {},
                             [&x](const T* /*t*/) { return x; }){};
};

#endif
