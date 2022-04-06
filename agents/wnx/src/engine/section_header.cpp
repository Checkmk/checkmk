// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// Provides basic section formatting
// header with optional separator
// empty header
// local header
// default names
// in the future we will add something here

#include "stdafx.h"

#include "service_processor.h"

namespace cma::section {

// Build standard header with optional Separator
// <<<section_name>>>\n or
// <<<section_name:sep(9)>>>\n
std::string MakeHeader(std::string_view name, char separator) noexcept {
    if (name.empty()) {
        XLOG::l("supplied empty string to header");
        name = "nothing";
    }

    std::string s{kLeftBracket};
    s += name;

    // separator part
    if (separator) {
        s += kLeftSeparator;
        s += std::to_string(separator);
        s += kRightSeparator;
    }

    s += kRightBracket;
    s += '\n';

    return s;
}

std::string MakeHeader(std::string_view name) noexcept {
    return MakeHeader(name, '\0');
}

// [sub_section_name]
std::string MakeSubSectionHeader(std::string_view name) noexcept {
    if (name.empty()) {
        XLOG::l(" supplied empty string to sub header");
        name = "nothing";
    }
    std::string s{kLeftSubSectionBracket};
    s += name;
    s += kRightSubSectionBracket;
    s += '\n';

    return s;
}

std::string MakeEmptyHeader() {
    static std::string s{std::string{kLeftBracket} + kRightBracket.data() +
                         '\n'};
    return s;
}

std::string MakeLocalHeader() {
    static std::string s{std::string{kLeftBracket} + kLocalHeader.data() +
                         kRightBracket.data() + '\n'};
    return s;
}

}  // namespace cma::section
