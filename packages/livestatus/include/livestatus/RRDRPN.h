// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef RRDRPN_h
#define RRDRPN_h

#include <string>
#include <utility>
#include <vector>

namespace detail {
class RPN {
    // Limited to binary operations, a single RPN line, and a single named
    // variable.
public:
    explicit RPN(const std::pair<std::string, double> &value) : _value{value} {}
    double solve(const std::vector<std::string> &x);

private:
    void op(const std::string &x);
    void eval(const std::string &x);
    double pop();

    std::vector<double> _stack;
    std::pair<std::string, double> _value;
};
}  // namespace detail

inline double rrd_rpn_solve(const std::vector<std::string> &x,
                            const std::pair<std::string, double> &value) {
    return detail::RPN{value}.solve(x);
}

#endif  // RRDRPN_h
