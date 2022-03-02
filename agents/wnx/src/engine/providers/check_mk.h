// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#pragma once
#ifndef check_mk_h__
#define check_mk_h__

#include <string>
#include <string_view>

#include "providers/internal.h"
#include "section_header.h"

namespace cma::provider {

/// \brief Converts address entry from config file into
///
/// Expected by check_mk check(only_from) representation.
/// Carefully tested to be maximally compatible with legacy
/// integrations tests.
/// On error returns empty string
std::string AddressToCheckMkString(std::string_view entry);

class CheckMk : public Synchronous {
public:
    explicit CheckMk() : Synchronous(section::kCheckMk) {}
    CheckMk(const std::string &name, char separator)
        : Synchronous(name, separator) {}

private:
    virtual std::string makeBody() override;
    static std::string makeOnlyFrom();
};

};  // namespace cma::provider

#endif  // check_mk_h__
