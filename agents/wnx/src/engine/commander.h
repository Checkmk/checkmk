
// tools to control starting operations

#pragma once
#include <string>
#include <string_view>

namespace cma {

namespace commander {
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
}  // namespace commander
}  // namespace cma
