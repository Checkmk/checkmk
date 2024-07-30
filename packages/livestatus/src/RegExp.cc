// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/RegExp.h"

#ifdef HAVE_RE2
// -----------------------------------------------------------------------------
// RE2 implementation
// -----------------------------------------------------------------------------
#include <stdexcept>

#include "re2/re2.h"
#include "re2/stringpiece.h"

class RegExp::Impl {
public:
    Impl(const std::string &str, Case c, Syntax s) : regex_(str, opts(c, s)) {
        if (!regex_.ok()) {
            throw std::runtime_error(regex_.error());
        }
    }

    std::string replace(std::string str, const std::string &replacement) {
        RE2::GlobalReplace(&str, regex_, replacement);
        return str;
    }

    bool match(const std::string &str) const {
        return RE2::FullMatch(str, regex_);
    }

    bool search(const std::string &str) const {
        return RE2::PartialMatch(str, regex_);
    }

    static std::string engine() { return "RE2"; }

private:
    RE2 regex_;

    static RE2::Options opts(Case c, Syntax s) {
        RE2::Options options{RE2::Quiet};
        options.set_case_sensitive(c == Case::respect);
        options.set_literal(s == Syntax::literal);
        return options;
    }
};

#else
// -----------------------------------------------------------------------------
// standard <regex> implementation
// -----------------------------------------------------------------------------
#include <map>
#include <regex>
#include <sstream>
#include <vector>
class RegExp::Impl {
public:
    Impl(const std::string &str, Case c, Syntax s)
        : regex_(s == Syntax::literal
                     ? std::regex_replace(
                           str, std::regex(R"([.^$|()\[\]{}*+?\\])"), R"(\\&)",
                           std::regex_constants::format_sed)
                     : str,
                 c == Case::respect
                     ? std::regex::extended
                     : std::regex::extended | std::regex::icase) {}

    std::string replace(const std::string &str,
                        const std::string &replacement) {
        return std::regex_replace(str, regex_, replacement,
                                  std::regex_constants::format_sed);
    }

    [[nodiscard]] bool match(const std::string &str) const {
        return regex_match(str, regex_);
    }

    [[nodiscard]] bool search(const std::string &str) const {
        return regex_search(str, regex_);
    }

    static std::string engine() { return "C++11"; }

private:
    std::regex regex_;
};
#endif

// -----------------------------------------------------------------------------
// boilerplate pimpl code
// -----------------------------------------------------------------------------

RegExp::RegExp(const std::string &str, Case c, Syntax s)
    : _impl(std::make_unique<Impl>(str, c, s)) {}

RegExp::~RegExp() = default;

RegExp::RegExp(RegExp &&rhs) noexcept = default;

RegExp &RegExp::operator=(RegExp &&rhs) noexcept = default;

std::string RegExp::replace(const std::string &str,
                            const std::string &replacement) const {
    return _impl->replace(str, replacement);
}

bool RegExp::match(const std::string &str) const { return _impl->match(str); }

bool RegExp::search(const std::string &str) const { return _impl->search(str); }

// static
std::string RegExp::engine() { return Impl::engine(); }
