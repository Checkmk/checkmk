// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "ColumnFilter.h"

#include <functional>

#include "AndingFilter.h"

std::unique_ptr<Filter> ColumnFilter::partialFilter(
    columnNamePredicate predicate) const {
    return predicate(columnName()) ? copy() : AndingFilter::make(kind(), {});
}

bool ColumnFilter::is_tautology() const { return false; }

bool ColumnFilter::is_contradiction() const { return false; }

Filters ColumnFilter::disjuncts() const {
    Filters filters;
    filters.push_back(copy());
    return filters;
}

Filters ColumnFilter::conjuncts() const {
    Filters filters;
    filters.push_back(copy());
    return filters;
}

std::ostream &ColumnFilter::print(std::ostream &os) const {
    return os << "Filter: " << columnName() << " " << oper() << " " << value();
}
