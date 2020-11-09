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

// TODO(sp): Is there a way to have a default value in the template parameters?
// Currently it is hardwired to the empty string.
template <class T>
class StringLambdaColumn : public StringColumn {
public:
    struct Constant;
    struct Reference;
    StringLambdaColumn(std::string name, std::string description,
                       ColumnOffsets offsets,
                       std::function<std::string(const T&)> gv)
        : StringColumn(std::move(name), std::move(description),
                       std::move(offsets))
        , get_value_(std::move(gv)) {}

    ~StringLambdaColumn() override = default;

    [[nodiscard]] std::string getValue(Row row) const override {
        using namespace std::string_literals;
        const T* data = columnData<T>(row);
        return data == nullptr ? ""s : get_value_(*data);
    }

private:
    std::function<std::string(const T&)> get_value_;
};

template <class T>
struct StringLambdaColumn<T>::Constant : StringLambdaColumn {
    Constant(std::string name, std::string description, const std::string& x)
        : StringLambdaColumn(std::move(name), std::move(description), {},
                             [x](const T& /*t*/) { return x; }){};
};

template <class T>
struct StringLambdaColumn<T>::Reference : StringLambdaColumn {
    Reference(std::string name, std::string description, const std::string& x)
        : StringLambdaColumn(std::move(name), std::move(description), {},
                             [&x](const T& /*t*/) { return x; }){};
};

#endif
