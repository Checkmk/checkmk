// Configuration Parameters for whole Agent
#include "stdafx.h"

#include "on_start.h"

#include <atomic>
#include <string>
#include <string_view>

#include "cfg.h"
#include "common/cfg_info.h"
#include "windows_service_api.h"

namespace cma::details {
extern bool G_Test;
}

namespace cma {

// internal global variables:
static bool S_ConfigLoaded = false;
static std::atomic<bool> S_OnStartCalled = false;

bool ConfigLoaded() { return S_ConfigLoaded; }
namespace cfg {

bool UseAlternateDirs(std::wstring_view base) {
    namespace fs = std::filesystem;
    fs::path root_dir = base;
    fs::path data_dir = base;
    data_dir /= L"ProgramData";

    std::error_code ec;
    if (std::filesystem::exists(data_dir, ec)) {
        XLOG::d("Already {} exists, no action required", data_dir.u8string());
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

    return true;
}

static void LogFolders() {
    auto root_dir = details::G_ConfigInfo.getRootDir();
    auto data_dir = details::G_ConfigInfo.getDataDir();
    XLOG::l.t("Using root = '{}' and data = '{}' folders ", root_dir.u8string(),
              data_dir.u8string());
}

bool DetermineWorkingFolders(AppType Type) {
    using namespace cma::cfg;
    namespace fs = std::filesystem;
    switch (Type) {
        case AppType::exe:  // main exe
        {
            // we are using special env variable for testing
            // THIS VARIABLE MUST BE TEMPORARY
            auto cma_test_dir = cma::tools::win::GetEnv(kTemporaryRoot);
            if (cma_test_dir.empty())
                details::G_ConfigInfo.initAll(L"", L"", L"");
            else {
                if (!UseAlternateDirs(cma_test_dir)) return false;
            }
            LogFolders();
        } break;

        case AppType::srv:
            details::G_ConfigInfo.initAll(cma::srv::kServiceName, L"", L"");
            break;

        case AppType::test:  // only watest
        {
            auto remote_machine_string =
                cma::tools::win::GetEnv(L"REMOTE_MACHINE");

            if (!UseAlternateDirs(remote_machine_string)) return false;
            LogFolders();

        } break;
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
    if (Type == AppType::test) cma::details::G_Test = true;

    using namespace std;
    using namespace cma::cfg;

    auto already_loaded = S_OnStartCalled.exchange(true);
    if (already_loaded && !cma::cfg::ReloadConfigAutomatically()) return true;

    if (already_loaded) {
        cfg::details::KillDefaultConfig();
    }
    wtools::InitWindowsCom();

    // false is possible only for watest
    if (!cfg::DetermineWorkingFolders(Type)) return false;
    groups::global.updateLogNamesByDefault();

    // load default configuration files
    auto cfg_files = cfg::DefaultConfigArray(Type);
    if (!ConfigFile.empty()) {
        cfg_files.clear();
        cfg_files.push_back(ConfigFile);
    }

    XLOG::setup::ChangeDebugLogLevel(LogLevel::kLogDebug);
    S_ConfigLoaded = cfg::InitializeMainConfig(cfg_files, YamlCacheOp::update);

    if (S_ConfigLoaded) {
        cfg::ProcessKnownConfigGroups();
        cfg::SetupEnvironmentFromGroups();
    }

    XLOG::l.i("Loaded start config {}",
              wtools::ConvertToUTF8(GetPathOfLoadedConfig()));
    return true;
}

void OnExit() {
    if (wtools::IsWindowsComInitialized()) wtools::CloseWindowsCom();
}
}  // namespace cma
