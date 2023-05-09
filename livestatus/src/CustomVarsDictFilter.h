// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef CustomVarsDictFilter_h
#define CustomVarsDictFilter_h

#include "config.h"  // IWYU pragma: keep

#include <chrono>
#include <memory>
#include <string>

#include "ColumnFilter.h"
#include "Filter.h"
#include "opids.h"
class CustomVarsDictColumn;
class RegExp;
class Row;

#ifdef CMC
#include "contact_fwd.h"
#else
// TODO(sp) Why on earth is "contact_fwd.h" not enough???
#include "nagios.h"
#endif

class CustomVarsDictFilter : public ColumnFilter {
public:
    CustomVarsDictFilter(Kind kind, const CustomVarsDictColumn &column,
                         RelationalOperator relOp, const std::string &value);
    bool accepts(Row row, const contact *auth_user,
                 std::chrono::seconds timezone_offset) const override;
    [[nodiscard]] std::unique_ptr<Filter> copy() const override;
    [[nodiscard]] std::unique_ptr<Filter> negate() const override;

private:
    const CustomVarsDictColumn &_column;
    std::shared_ptr<RegExp> _regExp;
    std::string _ref_string;
    std::string _ref_varname;
};

#endif  // CustomVarsDictFilter_h
