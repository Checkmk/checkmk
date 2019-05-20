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

#include "RegExp.h"

#ifdef HAVE_RE2
// -----------------------------------------------------------------------------
// RE2 implementation
// -----------------------------------------------------------------------------
#include <re2/re2.h>
#include <re2/stringpiece.h>
#include <stdexcept>

class RegExp::Impl {
public:
    Impl(const std::string &str, Case c, Syntax s) : _regex(str, opts(c, s)) {
        if (!_regex.ok()) {
            throw std::runtime_error(_regex.error());
        }
    }

    std::string replace(std::string str, const std::string &replacement) {
        RE2::GlobalReplace(&str, _regex, replacement);
        return str;
    }

    bool match(const std::string &str) const {
        return RE2::FullMatch(str, _regex);
    }

    bool search(const std::string &str) const {
        return RE2::PartialMatch(str, _regex);
    }

    static std::string engine() { return "RE2"; }

private:
    RE2 _regex;

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
        : _regex(s == Syntax::literal
                     ? std::regex_replace(
                           str, std::regex(R"([.^$|()\[\]{}*+?\\])"), R"(\\&)",
                           std::regex_constants::format_sed)
                     : str,
                 c == Case::respect
                     ? std::regex::extended
                     : std::regex::extended | std::regex::icase) {}

    std::string replace(const std::string &str,
                        const std::string &replacement) {
        return std::regex_replace(str, _regex, replacement,
                                  std::regex_constants::format_sed);
    }

    [[nodiscard]] bool match(const std::string &str) const {
        return regex_match(str, _regex);
    }

    [[nodiscard]] bool search(const std::string &str) const {
        return regex_search(str, _regex);
    }

    static std::string engine() { return "C++11"; }

private:
    std::regex _regex;
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
