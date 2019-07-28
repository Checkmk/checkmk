
// tools to control starting operations

#pragma once
#include <string>
#include <string_view>

namespace cma {

namespace commander {
constexpr std::string_view kMainPeer = "main_peer";
constexpr std::string_view kReload = "reload";

bool RunCommand(std::string_view peer, std::string_view cmd);
}  // namespace commander
}  // namespace cma
