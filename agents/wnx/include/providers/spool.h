// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#pragma once
#ifndef SPOOL_H
#define SPOOL_H

#include <filesystem>
#include <string>
#include <string_view>

#include "wnx/cma_core.h"
#include "providers/internal.h"
#include "wnx/section_header.h"

namespace cma::provider {

class SpoolProvider final : public Asynchronous {
public:
    SpoolProvider() : Asynchronous(section::kSpool) {}

    SpoolProvider(std::string_view name, char separator)
        : Asynchronous(name, separator) {}

    std::string makeHeader(
        const std::string_view /*section_name*/) const noexcept override {
        return {};
    }

protected:
    std::string makeBody() override;
};
bool IsSpoolFileValid(const std::filesystem::path &path);
bool IsDirectoryValid(const std::filesystem::path &dir);
}  // namespace cma::provider

#endif  // SPOOL_H
