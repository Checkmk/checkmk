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
            details::G_ConfigInfo.initFolders(L"", r.wstring(), d.wstring());
            break;
        }
        case AppType::srv:
            details::G_ConfigInfo.initFolders(cma::srv::kServiceName, L"", L"");
            break;
        case AppType::test:  // only watest
        {
            auto [r, d] = FindAlternateDirs(kRemoteMachine);
            details::G_ConfigInfo.initFolders(L"", r.wstring(), d.wstring());
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

static AppType CalcAppType(AppType Type) {
    if (Type == AppType::automatic) return AppDefaultType();
    if (Type == AppType::test) cma::details::G_Test = true;

    return Type;
}

bool ReloadConfig() {
    //

    return LoadConfig(AppDefaultType(), {});
}

bool LoadConfig(AppType Type, const std::wstring& ConfigFile) {
    cfg::details::KillDefaultConfig();
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
              wtools::ConvertToUTF8(cma::cfg::GetPathOfLoadedConfig()));
    return true;
}

bool OnStartCore(AppType type, const std::wstring& config_file) {
    if (!cfg::FindAndPrepareWorkingFolders(type)) return false;
    wtools::InitWindowsCom();

    return LoadConfig(type, config_file);
}

// must be called on start
bool OnStart(AppType proposed_type, const std::wstring& config_file) {
    auto type = CalcAppType(proposed_type);

    auto already_loaded = S_OnStartCalled.exchange(true);

    if (!already_loaded) return OnStartCore(type, config_file);

    if (AppDefaultType() == AppType::test) {
        XLOG::d.i("Second call of OnStart in test mode");
        return OnStartCore(type, config_file);
    }

    XLOG::l.crit(
        "Second call of OnStart, this may happen ONLY in test environment");

    return true;
}

void OnExit() {
    if (wtools::IsWindowsComInitialized()) wtools::CloseWindowsCom();
}
}  // namespace cma
