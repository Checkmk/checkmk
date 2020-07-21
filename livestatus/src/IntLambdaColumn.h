// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef IntLambdaColumn_h
#define IntLambdaColumn_h

#include <functional>
#include <string>
#include <utility>

#include "IntColumn.h"
#include "contact_fwd.h"
class Row;

template <class T>
class IntLambdaColumn : public IntColumn {
public:
    struct Constant;
    struct Reference;
    IntLambdaColumn(std::string name, std::string description, Offsets offsets,
                    std::function<int(const T*)> gv)
        : IntColumn(std::move(name), std::move(description), std::move(offsets))
        , get_value_{std::move(gv)} {}
    ~IntLambdaColumn() override = default;

    std::int32_t getValue(Row row,
                          const contact* /*auth_user*/) const override {
        return get_value_(columnData<T>(row));
    }

private:
    std::function<int(const T*)> get_value_;
};

template <class T>
struct IntLambdaColumn<T>::Constant : IntLambdaColumn {
    Constant(std::string name, std::string description, int x)
        : IntLambdaColumn(std::move(name), std::move(description), {},
                          [x](const T* /*t*/) { return x; }){};
};

template <class T>
struct IntLambdaColumn<T>::Reference : IntLambdaColumn {
    Reference(std::string name, std::string description, int& x)
        : IntLambdaColumn(std::move(name), std::move(description), {},
                          [&x](const T* /*t*/) { return x; }){};
};

#endif
