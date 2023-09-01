// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#pragma once
#ifndef SERVICES_H
#define SERVICES_H

#include <string>

#include "providers/internal.h"
#include "wnx/section_header.h"

namespace cma::provider {

class Services final : public Asynchronous {
public:
    Services() : Asynchronous(cma::section::kServices) {}
    Services(const std::string &name, char separator)
        : Asynchronous(name, separator) {}

private:
    std::string makeBody() override;
};

}  // namespace cma::provider

#endif  // SERVICES_H
