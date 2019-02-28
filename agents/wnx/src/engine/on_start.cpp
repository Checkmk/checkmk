// Configuration Parameters for whole Agent
#include "stdafx.h"

#include <atomic>
#include <string>

#include "common/cfg_info.h"

#include "cfg.h"
#include "on_start.h"

#include "windows_service_api.h"

namespace cma {

// internal global variables:
static bool S_ConfigLoaded = 0;
static std::atomic<bool> S_OnStartCalled = false;

bool ConfigLoaded() { return S_ConfigLoaded; }
namespace cfg {

bool DetermineWorkingFolders(StartTypes Type) {
    using namespace cma::cfg;
    namespace fs = std::filesystem;
    switch (Type) {
        case kExe:
            details::G_ConfigInfo.initAll(L"", L"", L"");
            break;

        case kService:
            details::G_ConfigInfo.initAll(cma::srv::kServiceName, L"", L"");
            break;

        case kTest:  // only watest
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
        default:
            break;
    };
    return true;
}  // namespace cma

}  // namespace cfg

// must be called on start
bool OnStart(StartTypes Type, bool UpdateCacheOnSuccess,
             std::wstring ConfigFile) {
    if (Type == kDefault) Type = AppDefaultType();

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
        cfg_files, UpdateCacheOnSuccess, Type != kTest);

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
