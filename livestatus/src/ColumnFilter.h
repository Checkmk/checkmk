// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef ColumnFilter_h
#define ColumnFilter_h

#include "config.h"  // IWYU pragma: keep

#include <functional>
#include <memory>
#include <ostream>
#include <string>
#include <utility>

#include "Column.h"
#include "Filter.h"
#include "opids.h"

class ColumnFilter : public Filter {
public:
    ColumnFilter(Kind kind, const Column &column, RelationalOperator relOp,
                 std::string value)
        : Filter(kind)
        , _column(column)
        , _relOp(relOp)
        , _value(std::move(value)) {}
    [[nodiscard]] std::string columnName() const { return _column.name(); }
    [[nodiscard]] RelationalOperator oper() const { return _relOp; }
    [[nodiscard]] std::string value() const { return _value; }
    std::unique_ptr<Filter> partialFilter(
        std::function<bool(const Column &)> predicate) const override;
    [[nodiscard]] bool is_tautology() const override;
    [[nodiscard]] bool is_contradiction() const override;
    [[nodiscard]] Filters disjuncts() const override;
    [[nodiscard]] Filters conjuncts() const override;

private:
    const Column &_column;
    const RelationalOperator _relOp;
    const std::string _value;

    std::ostream &print(std::ostream &os) const override;
};

#endif  // ColumnFilter_h
