// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// Tools to control behavior of the service from MSI/command line

#pragma once
#include <string_view>

namespace cma::commander {

constexpr std::string_view kMainPeer = "main_peer";
constexpr std::string_view kReload = "reload";
constexpr std::string_view kPassTrue = "pass_true";  // test command
constexpr std::string_view kUninstallAlert = "uninstall_alert";

using RunCommandProcessor = bool (*)(std::string_view peer,
                                     std::string_view cmd);
RunCommandProcessor ObtainRunCommandProcessor();

bool RunCommand(std::string_view peer, std::string_view cmd);

// normally only for testing
void ChangeRunCommandProcessor(RunCommandProcessor rcp);
}  // namespace cma::commander
