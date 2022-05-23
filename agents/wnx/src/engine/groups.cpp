// Configuration Parameters for whole Agent
#include "stdafx.h"

#include <shellapi.h>
#include <shlobj.h>  // known path

#include <filesystem>
#include <string>

#include "cfg.h"
#include "common/cfg_info.h"
#include "common/wtools.h"
#include "common/yaml.h"
#include "tools/_raii.h"  // on out
#include "tools/_tgt.h"   // we need IsDebug

namespace fs = std::filesystem;

namespace cma::cfg {

Global::Global() {
    // may crash on init XLOG::l.t("Global init");
    setDefaults();
    setupLogEnvironment();
}

// loader of yaml is going here
void Global::loadFromMainConfig() {
    auto config = cma::cfg::GetLoadedConfig();

    {
        reset();
        std::lock_guard lk(lock_);
        me_.reset();
        try {
            me_ = config[groups::kGlobal];
            exist_in_cfg_ = true;
        } catch (std::exception &) {
            me_.reset();
        }

        port_ = GetVal(groups::kGlobal, vars::kPort, cma::cfg::kMainPort);
        enabled_in_cfg_ =
            GetVal(groups::kGlobal, vars::kEnabled, exist_in_cfg_);
        name_ = GetVal(groups::kGlobal, vars::kName, std::string(""));
        ipv6_ = GetVal(groups::kGlobal, vars::kIpv6, false);
        async_ = GetVal(groups::kGlobal, vars::kAsync, true);
        flush_tcp_ = GetVal(groups::kGlobal, vars::kSectionFlush, false);

        password_ =
            GetVal(groups::kGlobal, vars::kGlobalPassword, std::string(""));

        encrypt_ = GetVal(groups::kGlobal, vars::kGlobalEncrypt, false);

        execute_ = GetInternalArray(groups::kGlobal, vars::kExecute);

        auto only_from = GetInternalArray(groups::kGlobal, vars::kOnlyFrom);
        fillOnlyFrom(only_from);

        enabled_sections_ =
            GetInternalArray(groups::kGlobal, vars::kSectionsEnabled);
        disabled_sections_ =
            GetInternalArray(groups::kGlobal, vars::kSectionsDisabled);
        auto realtime = GetNode(groups::kGlobal, vars::kRealTime);

        realtime_encrypt_ = GetVal(realtime, vars::kRtEncrypt, false);

        realtime_enabled_ = GetVal(realtime, vars::kRtEnabled, true);

        realtime_timeout_ =
            GetVal(realtime, vars::kRtTimeout, kDefaultRealtimeTimeout);

        realtime_port_ = GetVal(realtime, vars::kRtPort, kDefaultRealtimePort);

        wmi_timeout_ = GetVal(groups::kGlobal, vars::kGlobalWmiTimeout,
                              kDefaultWmiTimeout);
        cpuload_method_ = GetVal(groups::kGlobal, vars::kCpuLoadMethod,
                                 std::string{defaults::kCpuLoad});

        realtime_sections_ = GetInternalArray(realtime, vars::kRtRun);
        auto logging = GetNode(groups::kGlobal, vars::kLogging);

        // we must reuse already set location
        auto yml_log_location =
            GetVal(logging, vars::kLogLocation, yaml_log_path_.u8string());
        yaml_log_path_ =
            cma::cfg::details::ConvertLocationToLogPath(yml_log_location);

        std::string default_debug = tgt::IsDebug() ? "yes" : "no";
        auto debug_level = GetVal(logging, vars::kLogDebug, default_debug);
        if (debug_level.empty() || debug_level == "no")
            debug_level_ = LogLevel::kLogBase;
        else if (debug_level == "yes" || debug_level == "true")
            debug_level_ = LogLevel::kLogDebug;
        else if (debug_level == "all")
            debug_level_ = LogLevel::kLogAll;
        else
            debug_level_ =
                tgt::IsDebug() ? LogLevel::kLogDebug : LogLevel::kLogBase;

        windbg_ = GetVal(logging, vars::kLogWinDbg, true);

        event_log_ = GetVal(logging, vars::kLogEvent, true);

        log_file_name_ = GetVal(logging, vars::kLogFile, std::string());
        updateLogNames();
    }
    // UNLOCK HERE
}

// Software defaults
// Predefined and as logic as possible
// as safe as possible
void Global::setDefaults() {
    std::lock_guard lk(lock_);
    me_.reset();
    port_ = cma::cfg::kMainPort;
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
    debug_level_ = tgt::IsDebug() ? LogLevel::kLogDebug : LogLevel::kLogBase;
    windbg_ = true;
    event_log_ = true;
    log_file_name_ = kDefaultLogFileName;
}

static std::filesystem::path CheckAndCreateLogPath(
    const std::filesystem::path &forced_path) {
    namespace fs = std::filesystem;
    try {
        std::error_code ec;
        if (fs::exists(forced_path, ec)) return forced_path;

        fs::create_directories(forced_path, ec);
        if (fs::exists(forced_path, ec)) return forced_path;

        XLOG::l.bp("Failed to create [{}' folder as log",
                   forced_path.u8string());

    } catch (const std::exception &e) {
        XLOG::l.bp("Failed to use [{}' folder as log, exception is '{}'",
                   forced_path.u8string(), e.what());
    }
    return details::GetDefaultLogPath();
}

// should be called to keep invariant
void Global::updateLogNames() {
    auto yaml_path = yaml_log_path_.u8string();

    auto log_path = details::ConvertLocationToLogPath(yaml_path);

    auto yaml_file = log_file_name_;
    if (yaml_file.empty()) log_file_name_ = kDefaultLogFileName;

    logfile_dir_ = log_path;

    logfile_ = logfile_dir_ / log_file_name_;
    logfile_as_string_ = logfile_.u8string();
    logfile_as_wide_ = logfile_.wstring();
}

// empty string does nothing
// used to set values during start
void Global::setLogFolder(const fs::path &forced_path) {
    std::unique_lock lk(lock_);
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
void Global::setupLogEnvironment() {
    XLOG::setup::Configure(logfile_as_string_, debug_level_, windbg_,
                           event_log_);
    GetCfg().setConfiguredLogFileDir(logfile_dir_.wstring());
}

// loader
// gtest[+] partially
void WinPerf::loadFromMainConfig() {
    auto config = cma::cfg::GetLoadedConfig();

    std::lock_guard lk(lock_);
    // reset all
    reset();
    counters_.resize(0);

    // attempt to load all
    try {
        // if section not present
        auto yaml = GetLoadedConfig();
        auto me = yaml[groups::kWinPerf];
        if (!me.IsMap()) {
            XLOG::l("Section {} absent or invalid", groups::kWinPerf);
            return;
        }
        exist_in_cfg_ = true;

        exe_name_ =
            GetVal(groups::kWinPerf, vars::kWinPerfExe, std::string("agent"));

        prefix_ = GetVal(groups::kWinPerf, vars::kWinPerfPrefixName,
                         std::string("winperf"));

        timeout_ = GetVal(groups::kWinPerf, vars::kWinPerfTimeout,
                          cma::cfg::kDefaultWinPerfTimeout);

        fork_ = GetVal(groups::kWinPerf, vars::kWinPerfFork,
                       cma::cfg::kDefaultWinPerfFork);

        trace_ = GetVal(groups::kWinPerf, vars::kWinPerfTrace,
                        cma::cfg::kDefaultWinPerfTrace);

        enabled_in_cfg_ =
            GetVal(groups::kWinPerf, vars::kEnabled, exist_in_cfg_);
        auto counters = GetPairArray(groups::kWinPerf, vars::kWinPerfCounters);
        for (const auto &entry : counters) {
            counters_.emplace_back(entry.first, entry.second);
        }
    } catch (std::exception &e) {
        XLOG::l("Section {} ", groups::kWinPerf, e.what());
    }
}

void LoadExeUnitsFromYaml(std::vector<Plugins::ExeUnit> &exe_unit,
                          const std::vector<YAML::Node> &yaml_node) noexcept {
    for (const auto &entry : yaml_node) {
        try {
            auto pattern = entry[vars::kPluginPattern].as<std::string>();
            pattern = ReplacePredefinedMarkers(pattern);
            auto async = entry[vars::kPluginAsync].as<bool>(false);
            auto run = entry[vars::kPluginRun].as<bool>(true);
            auto retry = entry[vars::kPluginRetry].as<int>(0);
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

            exe_unit.emplace_back(pattern, timeout, age, retry, run);
            exe_unit.back().assign(entry);

            exe_unit.back().assignGroup(group);
            exe_unit.back().assignUser(user);
        } catch (const std::exception &e) {
            XLOG::l("bad entry at {} {} exc {}", groups::kPlugins,
                    vars::kPluginsExecution, e.what());
        }
    }
}

void Plugins::ExeUnit::assign(const YAML::Node &entry) {
    try {
        source_ = YAML::Clone(entry);
        ApplyValueIfScalar(source_, run_, vars::kPluginRun);
    } catch (const std::exception &e) {
        pattern_ = "";
        source_.reset();
        XLOG::l("bad entry at {} {} exc {}", groups::kPlugins,
                vars::kPluginsExecution, e.what());
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
        if (!entry.IsMap()) return;

        ApplyValueIfScalar(entry, async_, vars::kPluginAsync);
        ApplyValueIfScalar(entry, run_, vars::kPluginRun);
        ApplyValueIfScalar(entry, retry_, vars::kPluginRetry);
        ApplyValueIfScalar(entry, cache_age_, vars::kPluginCacheAge);
        ApplyValueIfScalar(entry, timeout_, vars::kPluginTimeout);
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
    auto config = GetLoadedConfig();

    std::lock_guard lk(lock_);
    // reset all
    reset();
    units_.resize(0);

    local_ = group_name == groups::kLocal;

    // attempt to load all
    try {
        // if section not present
        auto yaml = GetLoadedConfig();
        auto me = yaml[group_name];
        if (!me.IsMap()) {
            XLOG::l("Section {} absent or invalid", group_name);
            return;
        }
        exist_in_cfg_ = true;

        enabled_in_cfg_ = GetVal(group_name, vars::kEnabled, exist_in_cfg_);

        exe_name_ = GetVal(group_name, vars::kPluginExe,
                           std::string{"plugin_player.exe"});

        auto units = GetArray<YAML::Node>(group_name, vars::kPluginsExecution);
        LoadExeUnitsFromYaml(units_, units);

        folders_.clear();
        if (local_) {
            folders_.push_back(cma::cfg::GetLocalDir());
        } else {
            auto folders =
                GetArray<std::string>(group_name, vars::kPluginsFolders);
            for (const auto &folder : folders) {
                auto f = ReplacePredefinedMarkers(folder);
                folders_.push_back(wtools::ConvertToUTF16(f));
            }
        }
    } catch (std::exception &e) {
        XLOG::l("Section {} exception {}", group_name, e.what());
    }
}

// To be used in plugin player
// constructs command line from folders and patterns
Plugins::CmdLineInfo Plugins::buildCmdLine() const {
    namespace fs = std::filesystem;

    // pickup protected data from the structure
    std::unique_lock lk(lock_);
    auto units = units_;
    auto folders = folders_;
    lk.unlock();

    // case when there is NO folder in array
    const auto default_folder_mark =
        wtools::ConvertToUTF16(vars::kPluginsDefaultFolderMark);
    auto default_plugins_folder = cma::cfg::GetCfg().getSystemPluginsDir();
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
            // THIS IS NOT VALID CODE
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

    // remove duplicates
    std::sort(files.begin(), files.end());
    auto undefined = std::unique(files.begin(), files.end());
    files.erase(undefined, files.end());

    // build command line
    for (const auto &file_name : files) {
        cli.cmd_line_ += L"\"" + file_name + L"\" ";
    }
    if (cli.cmd_line_.empty()) {
        XLOG::l("Unexpected, no plugins to execute");
        return cli;
    }

    if (!cli.cmd_line_.empty() && cli.cmd_line_.back() == L' ')
        cli.cmd_line_.pop_back();

    XLOG::t.i("Expected to execute [{}] plugins '{}'", files.size(),
              wtools::ToUtf8(cli.cmd_line_));

    return cli;
}

}  // namespace cma::cfg
