// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#pragma once
#ifndef ps_h__
#define ps_h__

#include <ctime>
#include <string>
#include <string_view>

#include "providers/internal.h"
#include "section_header.h"

namespace cma::provider {

namespace ps {
constexpr std::wstring_view kSepString = L",";
}

time_t ConvertWmiTimeToHumanTime(const std::string &creation_date);

class Ps : public Asynchronous {
public:
    Ps() : Asynchronous(cma::section::kPsName, '\t') {}

    Ps(const std::string &name, char separator)
        : Asynchronous(name, separator) {}

    void loadConfig() override;

private:
    std::string makeBody() override;
    bool use_wmi_;
    bool full_path_;
};
std::string ProducePsWmi(bool use_full_path);
std::wstring GetProcessListFromWmi(std::wstring_view separator);

};  // namespace cma::provider

#endif  // ps_h__
