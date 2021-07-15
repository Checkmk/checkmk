// Configuration Parameters for whole Agent
#include "stdafx.h"

#include "on_start.h"

#include <atomic>
#include <string>
#include <string_view>

#include "cfg.h"
#include "cma_core.h"
#include "common/cfg_info.h"
#include "windows_service_api.h"

namespace fs = std::filesystem;

namespace cma::details {
extern bool g_is_test;
}

namespace cma {

// internal global variables:
static bool S_ConfigLoaded = false;
static std::atomic<bool> S_OnStartCalled = false;

bool ConfigLoaded() { return S_ConfigLoaded; }

std::pair<std::filesystem::path, std::filesystem::path> FindAlternateDirs(
    AppType app_type) {
    constexpr std::wstring_view environment_variable{};
    switch (app_type) {
        case AppType::exe:
            return {};
        case AppType::test:
            break;
        default:
            XLOG::l("Bad Mode [{}]", static_cast<int>(app_type));
            return {};
    }

    auto base = cma::tools::win::GetEnv(env::test_root);
    std::error_code ec;
    if (base.empty()) {
        auto exe = wtools::GetCurrentExePath();
        XLOG::l.i(
            "Environment variable {} not found, fallback to exe path '{}'",
            wtools::ToUtf8(env::test_root), exe);
        auto root = exe.parent_path() / "test" / "root";
        auto data = exe.parent_path() / "test" / "data";
        if (fs::exists(root, ec) && fs::exists(data, ec)) {
            return {root, data};
        }

        return {};
    }

    namespace fs = std::filesystem;
    auto root_dir = fs::path{base} / "test" / "root";
    auto data_dir = fs::path{base} / "test" / "data";

    if (!std::filesystem::exists(data_dir, ec) &&
        !fs::create_directories(data_dir, ec)) {
        XLOG::l.crit("Cannot create test folder {} error:{}", data_dir,
                     ec.value());
        return {};
    }

    return {root_dir, data_dir};
}

namespace cfg {

void LogFolders() {
    auto root_dir = GetCfg().getRootDir();
    auto data_dir = GetCfg().getDataDir();
    XLOG::l.t("Using root = '{}' and data = '{}' folders ", root_dir, data_dir);
}

bool FindAndPrepareWorkingFolders(AppType app_type) {
    switch (app_type) {
        case AppType::exe:
            [[fallthrough]];
        case AppType::test: {  // watest32
            auto [r, d] = FindAlternateDirs(app_type);
            GetCfg().initFolders(L"", r.wstring(), d.wstring());
            break;
        }
        case AppType::srv:
            GetCfg().initFolders(cma::srv::kServiceName, L"", L"");
            break;
        case AppType::automatic:
            [[fallthrough]];
        case AppType::failed:
            XLOG::l.crit("Invalid value of the AppType automatic [{}]",
                         static_cast<int>(app_type));
            return false;
    };
    LogFolders();
    return true;
}

}  // namespace cfg

static AppType CalcAppType(AppType app_type) {
    if (app_type == AppType::automatic) return AppDefaultType();
    if (app_type == AppType::test) cma::details::g_is_test = true;

    return app_type;
}

bool ReloadConfig() {
    //
    return LoadConfig(AppDefaultType(), {});
}

UninstallAlert g_uninstall_alert;

// usually for testing
void UninstallAlert::clear() noexcept {
    //
    set_ = false;
}

void UninstallAlert::set() noexcept {
    //
    if (!IsService()) {
        XLOG::l.i("Requested clean on exit is IGNORED, not service");
        return;
    }

    XLOG::l.i("Requested clean on exit");
    XLOG::details::LogWindowsEventAlways(XLOG::EventLevel::information, 9,
                                         "Requested Clean On Exit");
    set_ = true;
}

bool LoadConfig(AppType Type, const std::wstring& ConfigFile) {
    cfg::details::KillDefaultConfig();
    // load config is here
    auto cfg_files = cfg::DefaultConfigArray();
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
              wtools::ToUtf8(cma::cfg::GetPathOfLoadedConfig()));
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
    if (type == AppType::srv) {
        XLOG::details::LogWindowsEventAlways(XLOG::EventLevel::information, 35,
                                             "check_mk_service is loading");
    }

    if (!already_loaded) {
        XLOG::setup::SetContext(cma::IsService() ? "srv" : "app");
        return OnStartCore(type, config_file);
    }

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
