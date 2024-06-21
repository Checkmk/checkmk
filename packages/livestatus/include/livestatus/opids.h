// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef opids_h
#define opids_h

#include <iosfwd>
#include <memory>
#include <string>
#include <string_view>

class RegExp;

enum class RelationalOperator {
    equal,
    not_equal,
    matches,
    doesnt_match,
    equal_icase,
    not_equal_icase,
    matches_icase,
    doesnt_match_icase,
    less,
    greater_or_equal,
    greater,
    less_or_equal
};

std::ostream &operator<<(std::ostream &os, const RelationalOperator &relOp);

RelationalOperator relationalOperatorForName(std::string_view name);

RelationalOperator negateRelationalOperator(RelationalOperator relOp);

std::unique_ptr<RegExp> makeRegExpFor(RelationalOperator relOp,
                                      const std::string &value);
#endif  // opids_h
