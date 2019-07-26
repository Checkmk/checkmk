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

std::pair<std::filesystem::path, std::filesystem::path> FindAlternateDirs(
    std::wstring_view environment_variable) {
    auto base = cma::tools::win::GetEnv(environment_variable);
    if (base.empty()) return {};

    namespace fs = std::filesystem;
    fs::path root_dir = base;
    fs::path data_dir = base;
    data_dir /= L"ProgramData";

    std::error_code ec;
    if (!std::filesystem::exists(data_dir, ec) &&
        !fs::create_directories(data_dir, ec)) {
        XLOG::l.crit("Cannot create test folder {} error:{}",
                     data_dir.u8string(), ec.value());
        return {};
    }

    return {root_dir, data_dir};
}

namespace cfg {

void LogFolders() {
    auto root_dir = details::G_ConfigInfo.getRootDir();
    auto data_dir = details::G_ConfigInfo.getDataDir();
    XLOG::l.t("Using root = '{}' and data = '{}' folders ", root_dir.u8string(),
              data_dir.u8string());
}

bool FindAndPrepareWorkingFolders(AppType Type) {
    using namespace cma::cfg;
    namespace fs = std::filesystem;
    switch (Type) {
        case AppType::exe:  // main exe
        {
            auto [r, d] = FindAlternateDirs(kTemporaryRoot);
            details::G_ConfigInfo.initAll(L"", r.wstring(), d.wstring());
            break;
        }
        case AppType::srv:
            details::G_ConfigInfo.initAll(cma::srv::kServiceName, L"", L"");
            break;
        case AppType::test:  // only watest
        {
            auto [r, d] = FindAlternateDirs(kRemoteMachine);
            details::G_ConfigInfo.initAll(L"", r.wstring(), d.wstring());
            break;
        }
        case AppType::automatic:
            XLOG::l.crit("Invalid value of the AppType automatic");
            return false;
        case AppType::failed:
            XLOG::l.crit("Invalid value of the AppType automatic");
            return false;
    };
    LogFolders();
    return true;
}

}  // namespace cfg

// must be called on start
bool OnStart(AppType Type, const std::wstring& ConfigFile) {
    if (Type == AppType::automatic) Type = AppDefaultType();
    if (Type == AppType::test) cma::details::G_Test = true;

    using namespace std;
    using namespace cma::cfg;

    auto already_loaded = S_OnStartCalled.exchange(true);

    bool load_config = !already_loaded || cma::cfg::ReloadConfigAutomatically();

    if (load_config) {
        cfg::details::KillDefaultConfig();
        if (!cfg::FindAndPrepareWorkingFolders(Type)) return false;
    }

    if (!already_loaded) wtools::InitWindowsCom();

    if (!load_config) return true;

    // load config is here
    auto cfg_files = cfg::DefaultConfigArray(Type);
    if (!ConfigFile.empty()) {
        cfg_files.clear();
        cfg_files.push_back(ConfigFile);
    }

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
