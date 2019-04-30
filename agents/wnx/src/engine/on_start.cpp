// Configuration Parameters for whole Agent
#include "stdafx.h"

#include "on_start.h"

#include <atomic>
#include <string>

#include "cfg.h"
#include "common/cfg_info.h"
#include "windows_service_api.h"

namespace cma {

// internal global variables:
static bool S_ConfigLoaded = 0;
static std::atomic<bool> S_OnStartCalled = false;

bool ConfigLoaded() { return S_ConfigLoaded; }
namespace cfg {

bool DetermineWorkingFolders(AppType Type) {
    using namespace cma::cfg;
    namespace fs = std::filesystem;
    switch (Type) {
        case AppType::exe:
            details::G_ConfigInfo.initAll(L"", L"", L"");
            break;

        case AppType::srv:
            details::G_ConfigInfo.initAll(cma::srv::kServiceName, L"", L"");
            break;

        case AppType::test:  // only watest
        {
            auto remote_machine_string =
                cma::tools::win::GetEnv(L"REMOTE_MACHINE");

            fs::path root_dir = remote_machine_string;
            fs::path data_dir = remote_machine_string;
            data_dir /= L"ProgramData";

            std::error_code ec;
            if (std::filesystem::exists(data_dir, ec)) {
                XLOG::d("Already {} exists, no action required",
                        data_dir.u8string());
            } else {
                if (!fs::create_directories(data_dir, ec)) {
                    XLOG::l("Cannot create test folder {} error:{}",
                            data_dir.u8string(), ec.value());
                    return false;
                }
            }
            details::G_ConfigInfo.initAll(L"",       // no service
                                          root_dir,  // default
                                          data_dir   // this is data folder
            );
            break;
        }
        case AppType::automatic:
            XLOG::l.crit("Invalid value of the AppType");
            break;
    };
    return true;
}  // namespace cma

}  // namespace cfg

// must be called on start
bool OnStart(AppType Type, YamlCacheOp UpdateCacheOnSuccess,
             const std::wstring& ConfigFile) {
    if (Type == AppType::automatic) Type = AppDefaultType();

    wtools::InitWindowsCom();

    using namespace std;
    using namespace cma::cfg;

    auto old_value = S_OnStartCalled.exchange(true);
    if (old_value) {
        details::KillDefaultConfig();
    }

    // false is possible only for watest
    if (!cfg::DetermineWorkingFolders(Type)) return false;

    // load default configuration files
    auto cfg_files = cfg::DefaultConfigArray(Type);
    if (!ConfigFile.empty()) {
        cfg_files.clear();
        cfg_files.push_back(ConfigFile);
    }

    S_ConfigLoaded = cma::cfg::InitializeMainConfig(
        cfg_files, UpdateCacheOnSuccess == YamlCacheOp::update,
        Type != AppType::test);

    if (S_ConfigLoaded) {
        cma::cfg::ProcessKnownConfigGroups();
        cma::cfg::SetupEnvironmentFromGroups();
    }

    XLOG::l.i("Loaded start config {}",
              wtools::ConvertToUTF8(GetPathOfLoadedConfig()));
    return true;
}

void OnExit() {
    if (wtools::IsWindowsComInitialized()) wtools::CloseWindowsCom();
}
}  // namespace cma
