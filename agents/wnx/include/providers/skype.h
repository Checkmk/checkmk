// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#pragma once
#ifndef skype_h__
#define skype_h__

#include <string>
#include <string_view>

#include "common/cfg_info.h"
#include "providers/internal.h"
#include "wnx/section_header.h"

namespace cma::provider {

// mrpe:
class SkypeProvider : public Asynchronous {
public:
    SkypeProvider() : Asynchronous(section::kSkype, ',') {
        delay_on_fail_ = cfg::G_DefaultDelayOnFail;
    }

    SkypeProvider(const std::string_view &name, char separator)
        : Asynchronous(name, separator) {}

protected:
    std::string makeBody() override;

private:
    static std::string makeFirstLine();
    static std::wstring makeSubSection(std::wstring_view name);
};

// Special API used for testing
namespace internal {
std::vector<std::wstring> *GetSkypeCountersVector();
std::wstring_view GetSkypeAspSomeCounter();
}  // namespace internal

}  // namespace cma::provider

#endif  // skype_h__
