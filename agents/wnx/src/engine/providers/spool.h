// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#pragma once
#ifndef spool_h__
#define spool_h__

#include <filesystem>
#include <string>
#include <string_view>

#include "cma_core.h"
#include "providers/internal.h"
#include "section_header.h"

namespace cma::provider {

class SpoolProvider : public Asynchronous {
public:
    SpoolProvider() : Asynchronous(cma::section::kSpool) {}

    SpoolProvider(std::string_view name, char separator)
        : Asynchronous(name, separator) {}

    void loadConfig() override;

    void updateSectionStatus() override;

    // empty header
    std::string makeHeader(
        const std::string_view /*section_name*/) const override {
        return {};
    }

protected:
    std::string makeBody() override;
};
bool IsSpoolFileValid(const std::filesystem::path &path);
bool IsDirectoryValid(const std::filesystem::path &dir);
}  // namespace cma::provider

#endif  // spool_h__
