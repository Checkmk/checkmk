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
