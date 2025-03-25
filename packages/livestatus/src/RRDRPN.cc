// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/RRDRPN.h"

#include <stdexcept>
#include <system_error>

#include "livestatus/StringUtils.h"

using namespace std::string_literals;

double detail::RPN::solve(const std::vector<std::string> &x) {
    for (auto &&val : x) {
        eval(val);
    }
    if (_stack.size() != 1) {
        throw std::runtime_error{"invalid rpn"};
    }
    return pop();
}

void detail::RPN::op(const std::string &x) {
    // we only support binary operations
    if (x == "+"s) {
        const auto rhs = pop();
        const auto lhs = pop();
        _stack.emplace_back(lhs + rhs);
    } else if (x == "-"s) {
        const auto rhs = pop();
        const auto lhs = pop();
        _stack.emplace_back(lhs - rhs);
    } else if (x == "*"s) {
        const auto rhs = pop();
        const auto lhs = pop();
        _stack.emplace_back(lhs * rhs);
    } else if (x == "/"s) {
        const auto rhs = pop();
        const auto lhs = pop();
        _stack.emplace_back(lhs / rhs);
    } else {
        throw std::runtime_error{"unsupported operation " + x};
    }
}

void detail::RPN::eval(const std::string &x) {
    if (x == _value.first) {
        _stack.emplace_back(_value.second);
        return;
    }
    double number = 0.0;
    // NOLINTNEXTLINE(cppcoreguidelines-pro-bounds-pointer-arithmetic)
    auto [ptr, ec] = mk::from_chars(x.data(), x.data() + x.size(), number);
    if (ec == std::errc{}) {
        _stack.emplace_back(number);
    } else {
        op(x);
    }
}

double detail::RPN::pop() {
    if (_stack.empty()) {
        throw std::runtime_error{"invalid rpn"};
    }
    auto last = _stack.back();
    _stack.pop_back();
    return last;
}
