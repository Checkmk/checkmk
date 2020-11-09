// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef ListLambdaColumn_h
#define ListLambdaColumn_h

#include <functional>
#include <string>
#include <utility>
#include <vector>

#include "ListColumn.h"
#include "contact_fwd.h"
class Row;

// TODO(sp): Is there a way to have a default value in the template parameters?
// Currently it is hardwired to the empty vector.
template <class T>
class ListLambdaColumn : public ListColumn {
public:
    ListLambdaColumn(std::string name, std::string description,
                     ColumnOffsets offsets,
                     std::function<std::vector<std::string>(const T&)> f)
        : ListColumn(std::move(name), std::move(description),
                     std::move(offsets))
        , get_value_{std::move(f)} {}
    ~ListLambdaColumn() override = default;

    std::vector<std::string> getValue(
        Row row, const contact* /*auth_user*/,
        std::chrono::seconds /*timezone_offset*/) const override {
        const T* data = columnData<T>(row);
        return data == nullptr ? std::vector<std::string>{} : get_value_(*data);
    }

private:
    std::function<std::vector<std::string>(const T&)> get_value_;
};

#endif
