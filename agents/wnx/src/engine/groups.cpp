// Configuration Parameters for whole Agent
#include "stdafx.h"

#include <shellapi.h>
#include <shlobj.h>  // known path

#include <filesystem>
#include <string>

#include "cfg.h"
#include "common/cfg_info.h"
#include "common/wtools.h"
#include "tools/_raii.h"  // on out
#include "tools/_tgt.h"   // we need IsDebug
#include "yaml-cpp/yaml.h"

namespace cma::cfg {

Global::Global() {
    XLOG::l.t("Global init");
    setDefaults();
    calcDerivatives();
    setupEnvironment();
}

// loader of yaml is going here
void Global::loadFromMainConfig() {
    using namespace std;
    auto config = cma::cfg::GetLoadedConfig();

    {
        reset();
        std::lock_guard lk(lock_);
        me_.reset();
        try {
            me_ = config[groups::kGlobal];
            exist_in_cfg_ = true;
        } catch (std::exception&) {
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

        realtime_sections_ = GetInternalArray(realtime, vars::kRtRun);
        auto logging = GetNode(groups::kGlobal, vars::kLogging);

        auto yml_log_location =
            GetVal(logging, vars::kLogLocation, std::string());
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

        calcDerivatives();
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

void Global::updateLogNames(std::filesystem::path log_path) {
    if (log_path.empty()) XLOG::d.i("log_path is empty");

    logfile_dir_ = log_path;

    logfile_dir_ =
        cma::cfg::details::ConvertLocationToLogPath(logfile_dir_.u8string());

    if (log_file_name_.empty()) log_file_name_ = kDefaultLogFileName;

    logfile_ = logfile_dir_ / log_file_name_;
    logfile_as_string_ = logfile_.u8string();
    logfile_as_wide_ = logfile_.wstring();
}

// may be called only during start
void Global::updateLogNamesByDefault() {
    //
    updateLogNames({});
}
// optimization
void Global::calcDerivatives() {
#if 0
    auto rfid = public_log_ ? cma::cfg::kPublicFolderId : kWindowsFolderId;
    const auto dir = cma::tools::win::GetSomeSystemFolder(rfid);
    logfile_dir_ = dir;
    if (!public_log_) logfile_dir_ = logfile_dir_ / "Logs";
#endif
    updateLogNames(yaml_log_path_);
}

// transfer global data into app environment
void Global::setupEnvironment() {
    using namespace XLOG;

    setup::Configure(logfile_as_string_, debug_level_, windbg_, event_log_);
    details::G_ConfigInfo.setLogFileDir(logfile_dir_.wstring());
}

// loader
// gtest[+] partially
void WinPerf::loadFromMainConfig() {
    using namespace std;
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

        enabled_in_cfg_ =
            GetVal(groups::kWinPerf, vars::kEnabled, exist_in_cfg_);
        auto counters = GetPairArray(groups::kWinPerf, vars::kWinPerfCounters);
        for (const auto& entry : counters) {
            counters_.emplace_back(entry.first, entry.second);
        }
    } catch (std::exception& e) {
        XLOG::l("Section {} ", groups::kWinPerf, e.what());
    }
}

void LoadExeUnitsFromYaml(std::vector<Plugins::ExeUnit>& ExeUnit,
                          const std::vector<YAML::Node>& Yaml) noexcept {
    for (const auto& entry : Yaml) {
        try {
            // --exception control start --
            auto pattern = entry[vars::kPluginPattern].as<std::string>();
            pattern = ReplacePredefinedMarkers(pattern);
            auto async = entry[vars::kPluginAsync].as<bool>(false);
            auto run = entry[vars::kPluginRun].as<bool>(true);
            auto retry = entry[vars::kPluginRetry].as<int>(0);
            auto timeout =
                entry[vars::kPluginTimeout].as<int>(kDefaultPluginTimeout);
            auto cache_age = entry[vars::kPluginCacheAge].as<int>(0);
            if (cache_age && !async) {
                XLOG::d.t(
                    "Sync Plugin Entry '{}' forced to be async, due to cache_age [{}]",
                    pattern, cache_age);
                async = true;
            }

            if (async)
                ExeUnit.emplace_back(pattern, timeout, cache_age, retry, run);
            else
                ExeUnit.emplace_back(pattern, timeout, retry, run);
            // --exception control end  --
        } catch (const std::exception& e) {
            XLOG::l("bad entry at {} {} exc {}", groups::kPlugins,
                    vars::kPluginsExecution, e.what());
        }
    }
}

void Plugins::loadFromMainConfig(const std::string& GroupName) {
    using namespace std;
    using namespace cma::cfg;
    auto config = GetLoadedConfig();

    std::lock_guard lk(lock_);
    // reset all
    reset();
    units_.resize(0);

    local_ = GroupName == groups::kLocal;

    // attempt to load all
    try {
        // if section not present
        auto yaml = GetLoadedConfig();
        auto me = yaml[GroupName];
        if (!me.IsMap()) {
            XLOG::l("Section {} absent or invalid", GroupName);
            return;
        }
        exist_in_cfg_ = true;

        enabled_in_cfg_ = GetVal(GroupName, vars::kEnabled, exist_in_cfg_);

        exe_name_ =
            GetVal(GroupName, vars::kPluginExe, string("plugin_player.exe"));

        auto units = GetArray<YAML::Node>(GroupName, vars::kPluginsExecution);
        LoadExeUnitsFromYaml(units_, units);

        auto folders = GetArray<std::string>(GroupName, vars::kPluginsFolders);
        folders_.clear();
        if (local_) {
            folders_.push_back(cma::cfg::GetLocalDir());
        } else {
            for (const auto& folder : folders) {
                auto f = ReplacePredefinedMarkers(folder);
                folders_.push_back(wtools::ConvertToUTF16(f));
            }
        }
    } catch (std::exception& e) {
        XLOG::l("Section {} exception {}", GroupName, e.what());
    }
}

// To be used in plugin player
// constructs command line from folders and patterns
Plugins::CmdLineInfo Plugins::buildCmdLine() const {
    using namespace std;
    namespace fs = std::filesystem;

    // pickup protected data from the structure
    unique_lock lk(lock_);
    auto units = units_;
    auto folders = folders_;
    lk.unlock();

    // case when there is NO folder in array
    const auto default_folder_mark =
        wtools::ConvertToUTF16(vars::kPluginsDefaultFolderMark);
    auto default_plugins_folder =
        cma::cfg::details::G_ConfigInfo.getSystemPluginsDir();
    if (folders.size() == 0) folders.emplace_back(default_folder_mark);

    Plugins::CmdLineInfo cli;

    int count_of_folders = 0;
    int count_of_files = 0;
    vector<wstring> files;
    for (auto& folder : folders) {
        if (folder == default_folder_mark) {
            folder = default_plugins_folder;
        }
        std::error_code ec;
        if (!fs::exists(folder, ec)) continue;
        count_of_folders++;

        for (const auto& unit : units) {
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
    sort(files.begin(), files.end());
    auto undefined = unique(files.begin(), files.end());
    files.erase(undefined, files.end());

    // build command line
    for (const auto& file_name : files) {
        cli.cmd_line_ += L"\"" + file_name + L"\" ";
    }
    if (cli.cmd_line_.empty()) {
        XLOG::l("Unexpected, no plugins to execute");
        return cli;
    }

    if (!cli.cmd_line_.empty() && cli.cmd_line_.back() == L' ')
        cli.cmd_line_.pop_back();

    XLOG::t.i("Expected to execute [{}] plugins '{}'", files.size(),
              wtools::ConvertToUTF8(cli.cmd_line_));

    return cli;
}  // namespace cma::cfg

}  // namespace cma::cfg
