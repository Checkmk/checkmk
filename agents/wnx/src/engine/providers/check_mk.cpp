
// provides basic api to start and stop service
#include "stdafx.h"

#include <chrono>
#include <string>

#include "tools/_raii.h"
#include "tools/_xlog.h"

#include "providers/check_mk.h"

#include "cfg.h"

namespace cma {

namespace provider {

std::string CheckMk::makeBody() const {
    using namespace std::chrono;
    using namespace std;
    using namespace cma;
    using namespace wtools;
    using namespace cma::cfg;

    XLOG::t(XLOG_FUNC + " entering");

    pair<string, string> infos[] = {
        // start -----------------------------------------------
        {"Version", CHECK_MK_VERSION},
        {"BuildDate", __DATE__},
        {"AgentOS", "windows"},
        {"Hostname", cfg::GetHostName()},

        {"Architecture", tgt::Is64bit() ? "64bit" : "32bit"},
        {"WorkingDirectory", ConvertToUTF8(cfg::GetWorkingDir())},
        {"ConfigFile", ConvertToUTF8(cfg::GetPathOfRootConfig())},
        {"LocalConfigFile", ConvertToUTF8(cfg::GetPathOfUserConfig())},
        {"AgentDirectory", ConvertToUTF8(cfg::GetRootDir())},
        {"PluginsDirectory", ConvertToUTF8(cfg::GetUserPluginsDir())},
        {"StateDirectory", ConvertToUTF8(cfg::GetStateDir())},
        {"ConfigDirectory", ConvertToUTF8(cfg::GetPluginConfigDir())},
        {"TempDirectory", ConvertToUTF8(cfg::GetTempDir())},
        {"LogDirectory", ConvertToUTF8(cfg::GetLogDir())},
        {"SpoolDirectory", ConvertToUTF8(cfg::GetSpoolDir())},
        {"LocalDirectory", ConvertToUTF8(cfg::GetLocalDir())}
        // end -------------------------------------------------
    };

    std::string out;
    for (const auto& info : infos) {
        out += fmt::format("{}: {}\n", info.first, info.second);
    }
    out += "OnlyFrom:";
    auto only_from = GetArray<string>(groups::kGlobal, vars::kOnlyFrom);
    if (only_from.size() == 0) {
        out += " 0.0.0.0/0\n";
    } else {
        for (auto& entry : only_from) {
            out += " " + entry;
        }
        out += '\n';
    }
    return out;
}  // namespace provider

}  // namespace provider
};  // namespace cma
