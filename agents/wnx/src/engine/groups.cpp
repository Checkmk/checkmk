// Configuration Parameters for whole Agent
#include "stdafx.h"

#include <shellapi.h>

#include <filesystem>
#include <ranges>
#include <string>

#include "common/cfg_info.h"
#include "common/wtools.h"
#include "common/yaml.h"
#include "tools/_tgt.h"  // we need IsDebug
#include "wnx/cfg.h"
#include "wnx/cfg_details.h"

using namespace std::string_literals;
namespace fs = std::filesystem;

namespace cma::cfg {

Global::Global() noexcept { setDefaults(); }

namespace {

[[nodiscard]] bool IsSectionExist(std::string_view name) noexcept {
    try {
        auto _ = GetLoadedConfig()[name];
        return true;
    } catch (std::exception &) {
        return false;
    }
}

template <typename T>
[[nodiscard]] T GetGlobalVal(std::string_view name, T dflt) noexcept {
    return GetVal(groups::kGlobal, name, dflt);
}
template <typename T>
[[nodiscard]] T GetLoggingVal(std::string_view name, T dflt) noexcept {
    auto logging = GetNode(groups::kGlobal, vars::kLogging);
    return GetVal(logging, name, dflt);
}

std::unordered_map<std::string_view, LogLevel> text_to_log_level = {
    {"", LogLevel::kLogBase},     {"no", LogLevel::kLogBase},
    {"yes", LogLevel::kLogDebug}, {"true", LogLevel::kLogDebug},
    {"all", LogLevel::kLogAll},
};

[[nodiscard]] int GetLoggingDebugLevel() noexcept {
    constexpr std::string_view default_debug = tgt::IsDebug() ? "yes" : "no";
    auto level = GetLoggingVal(vars::kLogDebug, std::string{default_debug});
    try {
        return static_cast<int>(text_to_log_level.at(level));
    } catch (const std::out_of_range & /* e*/) {
        return static_cast<int>(tgt::IsDebug() ? LogLevel::kLogDebug
                                               : LogLevel::kLogBase);
    }
}
}  // namespace

// loader of yaml is going here
void Global::loadFromMainConfig() {
    std::scoped_lock lk(lock_);
    reset();
    exist_in_cfg_ = IsSectionExist(groups::kGlobal);
    if (!exist_in_cfg_) {
        return;
    }
    loadGlobal();
    loadRealTime();
    loadLogging();
}

void Global::loadGlobal() {
    port_ = GetGlobalVal(vars::kPort, kMainPort);
    enabled_in_cfg_ = GetGlobalVal(vars::kEnabled, exist_in_cfg_.load());
    name_ = GetGlobalVal(vars::kName, ""s);
    ipv6_ = GetGlobalVal(vars::kIpv6, false);
    async_ = GetGlobalVal(vars::kAsync, true);
    flush_tcp_ = GetGlobalVal(vars::kSectionFlush, false);
    password_ = GetGlobalVal(vars::kGlobalPassword, ""s);
    encrypt_ = GetGlobalVal(vars::kGlobalEncrypt, false);
    execute_ = GetInternalArray(groups::kGlobal, vars::kExecute);

    fillOnlyFrom(GetInternalArray(groups::kGlobal, vars::kOnlyFrom));

    enabled_sections_ =
        GetInternalArray(groups::kGlobal, vars::kSectionsEnabled);
    disabled_sections_ =
        GetInternalArray(groups::kGlobal, vars::kSectionsDisabled);
    wmi_timeout_ = GetGlobalVal(vars::kGlobalWmiTimeout, kDefaultWmiTimeout);
    cpuload_method_ =
        GetGlobalVal(vars::kCpuLoadMethod, std::string{defaults::kCpuLoad});
}

void Global::loadRealTime() {
    auto realtime = GetNode(groups::kGlobal, vars::kRealTime);

    realtime_encrypt_ = GetVal(realtime, vars::kRtEncrypt, false);
    realtime_enabled_ = GetVal(realtime, vars::kRtEnabled, true);
    realtime_timeout_ =
        GetVal(realtime, vars::kRtTimeout, kDefaultRealtimeTimeout);

    realtime_port_ = GetVal(realtime, vars::kRtPort, kDefaultRealtimePort);
    realtime_sections_ = GetInternalArray(realtime, vars::kRtRun);
}

void Global::loadLogging() {
    auto yml_log_location = GetLoggingVal(vars::kLogLocation, ""s);
    yaml_log_path_ = details::ConvertLocationToLogPath(yml_log_location);
    debug_level_ = GetLoggingDebugLevel();
    windbg_ = GetLoggingVal(vars::kLogWinDbg, true);
    event_log_ = GetLoggingVal(vars::kLogEvent, true);
    log_file_name_ = GetLoggingVal(vars::kLogFile, ""s);
    updateLogNames();
}

// Software defaults
// Predefined and as logic as possible
// as safe as possible
void Global::setDefaults() noexcept {
    port_ = kMainPort;
    enabled_in_cfg_ = false;
    name_ = "";
    ipv6_ = false;
    async_ = true;
    flush_tcp_ = false;
    encrypt_ = false;
    only_from_ = {};
    enabled_sections_ = {};
    disabled_sections_ = {};
    // realtime
    realtime_encrypt_ = false;
    realtime_timeout_ = kDefaultRealtimeTimeout;
    wmi_timeout_ = kDefaultWmiTimeout;
    password_ = "";
    realtime_sections_ = {};

    // log
    debug_level_ = static_cast<int>(tgt::IsDebug() ? LogLevel::kLogDebug
                                                   : LogLevel::kLogBase);
    windbg_ = true;
    event_log_ = true;
    log_file_name_ = kDefaultLogFileName;
}

static fs::path CheckAndCreateLogPath(const fs::path &forced_path) {
    try {
        std::error_code ec;
        if (fs::exists(forced_path, ec)) {
            return forced_path;
        }

        fs::create_directories(forced_path, ec);
        if (fs::exists(forced_path, ec)) {
            return forced_path;
        }

        XLOG::l.bp("Failed to create [{}' folder as log", forced_path);

    } catch (const std::exception &e) {
        XLOG::l.bp("Failed to use [{}' folder as log, exception is '{}'",
                   forced_path, e.what());
    }
    return details::GetDefaultLogPath();
}

// should be called to keep invariant
void Global::updateLogNames() {
    auto yaml_path = wtools::ToUtf8(yaml_log_path_.wstring());
    auto log_path = details::ConvertLocationToLogPath(yaml_path);
    if (log_file_name_.empty()) {
        log_file_name_ = kDefaultLogFileName;
    }
    logfile_dir_ = log_path;

    logfile_ = logfile_dir_ / log_file_name_;
    logfile_as_string_ = wtools::ToUtf8(logfile_.wstring());
    logfile_as_wide_ = logfile_.wstring();
}

// empty string does nothing
// used to set values during start
void Global::setLogFolder(const fs::path &forced_path) {
    std::scoped_lock lk(lock_);
    if (GetModus() == Modus::service) {
        XLOG::details::LogWindowsEventAlways(
            XLOG::EventLevel::information, 35,
            "checkmk service uses log path '{}'", forced_path);
    }
    if (forced_path.empty()) {
        return;
    }

    yaml_log_path_ = CheckAndCreateLogPath(forced_path);
    updateLogNames();
}

// transfer global data into app environment
void Global::setupLogEnvironment() const {
    XLOG::setup::Configure(logfile_as_string_, debug_level_, windbg_,
                           event_log_);
    GetCfg().setConfiguredLogFileDir(logfile_dir_.wstring());
}

namespace {
template <typename T>
[[nodiscard]] T GetWinPerfVal(std::string_view name, T dflt) noexcept {
    return GetVal(groups::kWinPerf, name, dflt);
}
}  // namespace

void WinPerf::loadFromMainConfig() {
    auto config = cfg::GetLoadedConfig();

    std::lock_guard lk(lock_);
    reset();
    counters_.resize(0);
    exist_in_cfg_ = IsSectionExist(groups::kWinPerf);
    if (!exist_in_cfg_) {
        XLOG::l("Section {} absent or invalid", groups::kWinPerf);
        return;
    }
    exe_name_ = GetWinPerfVal(vars::kWinPerfExe, "agent"s);
    prefix_ = GetWinPerfVal(vars::kWinPerfPrefixName, "winperf"s);
    timeout_ =
        GetWinPerfVal(vars::kWinPerfTimeout, cfg::kDefaultWinPerfTimeout);
    fork_ = GetWinPerfVal(vars::kWinPerfFork, cfg::kDefaultWinPerfFork);
    trace_ = GetWinPerfVal(vars::kWinPerfTrace, cfg::kDefaultWinPerfTrace);
    enabled_in_cfg_ = GetWinPerfVal(vars::kEnabled, exist_in_cfg_.load());
    auto counters = GetPairArray(groups::kWinPerf, vars::kWinPerfCounters);
    for (const auto &[id, name] : counters) {
        counters_.emplace_back(id, name);
    }
}

std::vector<Plugins::ExeUnit> LoadExeUnitsFromYaml(
    const std::vector<YAML::Node> &yaml_node) noexcept {
    std::vector<Plugins::ExeUnit> exe_unit;
    for (const auto &entry : yaml_node) {
        try {
            auto pattern = entry[vars::kPluginPattern].as<std::string>();
            pattern = ReplacePredefinedMarkers(pattern);
            auto async = entry[vars::kPluginAsync].as<bool>(false);
            auto run = entry[vars::kPluginRun].as<bool>(true);
            auto retry = entry[vars::kPluginRetry].as<int>(0);
            auto repair_invalid_utf =
                entry[vars::kPluginRepairInvalidUtf].as<bool>(false);
            auto timeout =
                entry[vars::kPluginTimeout].as<int>(kDefaultPluginTimeout);
            auto cache_age = entry[vars::kPluginCacheAge].as<int>(0);
            if (cache_age < 0) {
                cache_age = 0;
            }

            auto group = entry[vars::kPluginGroup].as<std::string>("");
            auto user = entry[vars::kPluginUser].as<std::string>("");

            std::optional<int> age;
            if (cache_age != 0 || async) {
                age = cache_age;
            }

            if (!async && age.has_value()) {
                XLOG::d.t(
                    "Sync Plugin Entry '{}' forced to be async, due to cache_age [{}]",
                    pattern, cache_age);
            }

            exe_unit.emplace_back(pattern, timeout, repair_invalid_utf, age,
                                  retry, run);
            exe_unit.back().assign(entry);

            exe_unit.back().assignGroup(group);
            exe_unit.back().assignUser(user);
        } catch (const std::exception &e) {
            XLOG::l("bad entry at {} {} exc {}", groups::kPlugins,
                    vars::kPluginsExecution, e);
        }
    }
    return exe_unit;
}

void Plugins::ExeUnit::assign(const YAML::Node &entry) {
    try {
        source_ = YAML::Clone(entry);
        ApplyValueIfScalar(source_, run_, vars::kPluginRun);
    } catch (const std::exception &e) {
        pattern_ = "";
        source_.reset();
        XLOG::l("bad entry at {} {} exc {}", groups::kPlugins,
                vars::kPluginsExecution, e);
    }
}

void Plugins::ExeUnit::assignGroup(std::string_view group) { group_ = group; }

void Plugins::ExeUnit::assignUser(std::string_view user) {
    if (group_.empty())
        user_ = user;
    else
        user_.clear();
}

void Plugins::ExeUnit::apply(std::string_view filename,
                             const YAML::Node &entry) {
    try {
        if (!entry.IsMap()) {
            return;
        }

        ApplyValueIfScalar(entry, async_, vars::kPluginAsync);
        ApplyValueIfScalar(entry, run_, vars::kPluginRun);
        ApplyValueIfScalar(entry, retry_, vars::kPluginRetry);
        ApplyValueIfScalar(entry, cache_age_, vars::kPluginCacheAge);
        ApplyValueIfScalar(entry, timeout_, vars::kPluginTimeout);
        ApplyValueIfScalar(entry, repair_invalid_utf_,
                           vars::kPluginRepairInvalidUtf);
        ApplyValueIfScalar(entry, group_, vars::kPluginGroup);
        ApplyValueIfScalar(entry, user_, vars::kPluginUser);
        if (cache_age_ != 0 && !async_) {
            XLOG::d.t(
                "Sync Plugin Entry '{}' forced to be async, due to cache_age [{}]",
                filename, cache_age_);
            async_ = true;
        }

    } catch (const std::exception &e) {
        pattern_ = "";
        source_.reset();
        XLOG::l("bad entry at {} {} exc {}", groups::kPlugins,
                vars::kPluginsExecution, e.what());
    }
}

void Plugins::loadFromMainConfig(std::string_view group_name) {
    std::lock_guard lk(lock_);
    reset();
    units_.resize(0);
    local_ = group_name == groups::kLocal;
    try {
        auto yaml = GetLoadedConfig();
        auto me = yaml[group_name];
        if (!me.IsMap()) {
            XLOG::l("Section {} absent or invalid", group_name);
            return;
        }
        exist_in_cfg_ = true;
        enabled_in_cfg_ =
            GetVal(group_name, vars::kEnabled, exist_in_cfg_.load());
        exe_name_ = GetVal(group_name, vars::kPluginExe,
                           std::string{"plugin_player.exe"});
        const auto units =
            GetArray<YAML::Node>(group_name, vars::kPluginsExecution);
        units_ = LoadExeUnitsFromYaml(units);
        folders_.clear();
        if (local_) {
            folders_.push_back(GetLocalDir());
        } else {
            const auto folders =
                GetArray<std::string>(group_name, vars::kPluginsFolders);
            for (const auto &folder : folders) {
                auto f = ReplacePredefinedMarkers(folder);
                folders_.push_back(wtools::ConvertToUtf16(f));
            }
        }
    } catch (const std::exception &e) {
        XLOG::l("Section {} exception {}", group_name, e.what());
    }
}

namespace {
void RemoveDuplicates(std::vector<std::wstring> &files) {
    std::ranges::sort(files);
    auto [a, b] = std::ranges::unique(files);
    files.erase(a, b);
}

void UpdateCommandLine(std::wstring &cmd_line,
                       const std::vector<std::wstring> &files) {
    for (const auto &file_name : files) {
        cmd_line += L"\"" + file_name + L"\" ";
    }
    if (cmd_line.empty()) {
        XLOG::l("Unexpected, no plugins to execute");
        return;
    }

    if (!cmd_line.empty() && cmd_line.back() == L' ') {
        cmd_line.pop_back();
    }

    XLOG::t.i("Expected to execute [{}] plugins '{}'", files.size(),
              wtools::ToUtf8(cmd_line));
}
}  // namespace

// To be used in plugin player
// constructs command line from folders and patterns
Plugins::CmdLineInfo Plugins::buildCmdLine() const {
    // pickup protected data from the structure
    std::unique_lock lk(lock_);
    auto units = units_;
    auto folders = folders_;
    lk.unlock();

    // case when there is NO folder in array
    const auto default_folder_mark =
        wtools::ConvertToUtf16(vars::kPluginsDefaultFolderMark);
    auto default_plugins_folder = GetCfg().getSystemPluginsDir();
    if (folders.empty()) {
        folders.emplace_back(default_folder_mark);
    }

    Plugins::CmdLineInfo cli;

    int count_of_folders = 0;
    int count_of_files = 0;
    std::vector<std::wstring> files;
    for (auto &folder : folders) {
        if (folder == default_folder_mark) {
            folder = default_plugins_folder;
        }
        std::error_code ec;
        if (!fs::exists(folder, ec)) {
            continue;
        }
        count_of_folders++;

        for (const auto &unit : units) {
            // must be complicated full folder scanning by mask
            fs::path file = folder;
            file /= unit.pattern();
            if (fs::exists(file, ec)) {
                count_of_files++;
                files.emplace_back(file.lexically_normal().wstring());
                cli.timeouts_.emplace_back(unit.timeout());
            }
        }
    }

    XLOG::d() << "we have processed:" << count_of_folders << " folders and "
              << count_of_files << " files";

    RemoveDuplicates(files);
    UpdateCommandLine(cli.cmd_line_, files);

    return cli;
}

}  // namespace cma::cfg
