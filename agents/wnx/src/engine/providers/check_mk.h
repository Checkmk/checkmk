// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

//

#pragma once
#ifndef check_mk_h__
#define check_mk_h__

#include <string>

#include "providers/internal.h"
#include "section_header.h"

namespace cma {

namespace provider {

// Converts address entry from config file into
// expected by check_mk check(only_from) representation.
// Carefully tested to be maximally compatible with legacy
// integrations tests
// on error returns empty string
std::string AddressToCheckMkString(std::string_view entry);

class CheckMk : public Synchronous {
public:
    CheckMk() : Synchronous(cma::section::kCheckMk) {}
    CheckMk(const std::string& Name, char Separator)
        : Synchronous(Name, Separator) {}

private:
    virtual std::string makeBody() override;
    static std::string makeOnlyFrom();

#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class SectionProviders;
    FRIEND_TEST(SectionProviders, BasicCheckMkOnlyFrom);
#endif
};

}  // namespace provider

};  // namespace cma

#endif  // check_mk_h__
