// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#pragma once

#include <yaml-cpp/yaml.h>

#include <vector>

#include "cma_core.h"

namespace cma::cfg::extensions {
enum class Mode { yes, no, automatic };
struct Extension {
    std::string name;
    std::string binary;
    std::string command_line;
    Mode mode;
};

std::vector<Extension> GetAll(YAML::Node node);
std::vector<std::filesystem::path> StartAll(
    const std::vector<Extension> &extensions);
void KillAll(const std::vector<std::filesystem::path> &paths);

}  // namespace cma::cfg::extensions
