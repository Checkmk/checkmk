// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#pragma once
#ifndef system_time_h__
#define system_time_h__

#include <string>

#include "providers/internal.h"
#include "section_header.h"

namespace cma::provider {

class SystemTime : public Synchronous {
public:
    SystemTime() : Synchronous(cma::section::kSystemTime) {}
    SystemTime(const std::string &name, char separator)
        : Synchronous(name, separator) {}

private:
    std::string makeBody() override;
};

}  // namespace cma::provider

#endif  // system_time_h__
