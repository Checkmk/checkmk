// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#pragma once
#ifndef MEM_H
#define MEM_H

#include <string>

#include "providers/internal.h"
#include "wnx/section_header.h"

namespace cma::provider {

class Mem final : public Synchronous {
public:
    Mem() : Synchronous(cma::section::kMemName) {}
    Mem(const std::string &name, char separator)
        : Synchronous(name, separator) {}

private:
    std::string makeBody() override;
};

}  // namespace cma::provider

#endif  // MEM_H
