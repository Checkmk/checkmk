// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

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
