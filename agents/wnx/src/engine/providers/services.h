// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#pragma once
#ifndef services_h__
#define services_h__

#include <string>

#include "providers/internal.h"
#include "section_header.h"

namespace cma::provider {

class Services : public Asynchronous {
public:
    Services() : Asynchronous(cma::section::kServices) {}
    Services(const std::string &name, char separator)
        : Asynchronous(name, separator) {}

private:
    std::string makeBody() override;
};

};  // namespace cma::provider

#endif  // services_h__
