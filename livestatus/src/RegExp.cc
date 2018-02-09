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
#include <regex>

class RegExp::Impl {
public:
    Impl(const std::string &str, Case c)
        : _regex(str, c == Case::ignore
                          ? std::regex::extended | std::regex::icase
                          : std::regex::extended) {}

    std::string replace(const std::string &str,
                        const std::string &replacement) {
        return std::regex_replace(str, _regex, replacement,
                                  std::regex_constants::format_sed);
    }

    bool search(const std::string &str) const {
        return regex_search(str, _regex);
    }

private:
    std::regex _regex;
};

RegExp::RegExp(const std::string &str, Case c)
    : _impl(std::make_unique<Impl>(str, c)) {}

RegExp::~RegExp() = default;

RegExp::RegExp(const RegExp &rhs) noexcept
    : _impl(std::make_unique<Impl>(*rhs._impl)) {}

RegExp &RegExp::operator=(const RegExp &rhs) noexcept {
    *_impl = *rhs._impl;
    return *this;
}

RegExp::RegExp(RegExp &&rhs) noexcept = default;

RegExp &RegExp::operator=(RegExp &&rhs) noexcept = default;

std::string RegExp::replace(const std::string &str,
                            const std::string &replacement) const {
    return _impl->replace(str, replacement);
}

bool RegExp::search(const std::string &str) const { return _impl->search(str); }
