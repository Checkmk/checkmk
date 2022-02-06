// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#pragma once
#ifndef agent_controller_h__
#define agent_controller_h__
#include <filesystem>

namespace YAML {
class Node;
}

namespace cma::ac {
bool StartAgentController(const std::filesystem::path &service);
bool KillAgentController();
bool IsRunController(const YAML::Node &node);
bool IsUseLegacyMode(const YAML::Node &node);
}  // namespace cma::ac

#endif  // agent_controller_h__
