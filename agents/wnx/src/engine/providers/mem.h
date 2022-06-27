// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// provides basic api to start and stop service

#pragma once
#ifndef mem_h__
#define mem_h__

#include <string>

#include "providers/internal.h"
#include "section_header.h"

namespace cma::provider {

class Mem : public Synchronous {
public:
    Mem() : Synchronous(cma::section::kMemName) {}
    Mem(const std::string &name, char separator)
        : Synchronous(name, separator) {}

private:
    std::string makeBody() override;
};

};  // namespace cma::provider

#endif  // mem_h__
