// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TimeLambdaColumn_h
#define TimeLambdaColumn_h

#include <chrono>
#include <functional>
#include <string>
#include <utility>

#include "TimeColumn.h"
#include "contact_fwd.h"
class Row;

// TODO(sp): Is there a way to have a default value in the template parameters?
// Currently it is hardwired to the start of the epoch.
template <class T>
class TimeLambdaColumn : public TimeColumn {
public:
    struct Constant;
    struct Reference;
    TimeLambdaColumn(
        std::string name, std::string description, ColumnOffsets offsets,
        std::function<std::chrono::system_clock::time_point(const T&)> gv)
        : TimeColumn(std::move(name), std::move(description),
                     std::move(offsets))
        , get_value_{std::move(gv)} {}
    ~TimeLambdaColumn() override = default;

private:
    [[nodiscard]] std::chrono::system_clock::time_point getRawValue(
        Row row) const override {
        const T* data = columnData<T>(row);
        return data == nullptr ? std::chrono::system_clock::time_point{}
                               : get_value_(*data);
    }

    std::function<std::chrono::system_clock::time_point(const T&)> get_value_;
};

template <class T>
struct TimeLambdaColumn<T>::Constant : TimeLambdaColumn {
    Constant(std::string name, std::string description,
             std::chrono::system_clock::time_point x)
        : TimeLambdaColumn(std::move(name), std::move(description), {},
                           [x](const T& /*t*/) { return x; }){};
};

template <class T>
struct TimeLambdaColumn<T>::Reference : TimeLambdaColumn {
    Reference(std::string name, std::string description,
              std::chrono::system_clock::time_point& x)
        : TimeLambdaColumn(std::move(name), std::move(description), {},
                           [&x](const T& /*t*/) { return x; }){};
};

#endif
