// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef ListLambdaColumn_h
#define ListLambdaColumn_h

#include <functional>
#include <string>
#include <vector>
#include "ListColumn.h"
#include "contact_fwd.h"
class Row;

class ListLambdaColumn : public ListColumn {
public:
    ListLambdaColumn(std::string name, std::string description,
                     std::function<std::vector<std::string>(Row)> f)
        : ListColumn(std::move(name), std::move(description), {})
        , get_value_{f} {}
    virtual ~ListLambdaColumn() = default;

    std::vector<std::string> getValue(
        Row row, const contact* /*auth_user*/,
        std::chrono::seconds /*timezone_offset*/) const override {
        return get_value_(row);
    }

private:
    std::function<std::vector<std::string>(Row)> get_value_;
};

#endif
