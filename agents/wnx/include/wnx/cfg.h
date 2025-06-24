// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#pragma once

#include <functional>
#include <optional>
#include <ranges>
#include <string>
#include <utility>

#include "common/cfg_info.h"
#include "common/wtools.h"
#include "logger.h"
#include "on_start.h"
#include "onlyfrom.h"
#include "tools/_misc.h"

namespace cma::cfg {
constexpr std::string_view kBuildHashValue = "DEFADEFADEFA";
enum class LoadCfgStatus {
    kAllFailed,    // root config not found
    kCacheFailed,  // cached not found, only root loaded, user is bad
    kFileLoaded,   // all loaded
    kCacheLoaded,  // user is bad, cache loaded
};

enum class Error {
    kOk = 0,     //
    kEmpty = 1,  // config is empty
    kNotFound    // name not found

};

namespace files {

// names of file
constexpr const wchar_t *kDefaultMainConfigName = L"check_mk";
constexpr const wchar_t *kDefaultMainConfig = L"check_mk.yml";

constexpr const wchar_t *kCapFile = L"plugins.cap";
constexpr const wchar_t *kIniFile = L"check_mk.ini";
constexpr const wchar_t *kInstallYmlFileW = L"check_mk.install.yml";
constexpr const char *kInstallYmlFileA = "check_mk.install.yml";
constexpr const wchar_t *kWatoIniFile = L"check_mk.ini";
constexpr const wchar_t *kAuStateFile = L"cmk-update-agent.state";

constexpr std::wstring_view kDatFile = L"checkmk.dat";
constexpr std::wstring_view kUserYmlFile = L"check_mk.user.yml";
constexpr std::wstring_view kBakeryYmlFile = L"check_mk.bakery.yml";
constexpr std::wstring_view kExecuteUpdateFile = L"execute_update.cmd";
constexpr std::wstring_view kConfigureAndExecPs1 = L"configure_and_exec.ps1";

// extensions
constexpr const wchar_t *kDefaultBakeryExt = L".bakery.yml";
constexpr const wchar_t *kDefaultUserExt = L".user.yml";

// special
constexpr std::string_view kUpgradeProtocol = "upgrade.protocol";
constexpr std::string_view kInstallProtocol = "install.protocol";
constexpr const wchar_t *kAgentUpdaterPython = L"cmk_update_agent.checkmk.py";
constexpr const wchar_t *kAgentCtl = L"cmk-agent-ctl.exe";
constexpr const wchar_t *kAgentToml = L"cmk-agent-ctl.toml";

}  // namespace files

// *******************************************************
// Important internal API
// Example is in OnStart
// *******************************************************

// 1.
// we have to init folders depending from start type
// test, exe or service
// This is done once for whole life-cycle
bool FindAndPrepareWorkingFolders(AppType app_type);

// 2. Prepare List of possible config names
std::vector<std::wstring> DefaultConfigArray();

// 3.
// must be called o program start.
// and check done too
[[nodiscard]] bool InitializeMainConfig(
    const std::vector<std::wstring> &config_filenames, YamlCacheOp cache_op);

// *******************************************************
// Internal API
// *******************************************************

// provides one or more file name to find and load on
// available paths

// how to use, look OnStart
// this function gets parse yaml to get information into known groups
void ProcessKnownConfigGroups();
void SetupEnvironmentFromGroups();

consteval bool ReloadConfigAutomatically() noexcept { return false; }

// returns stored value from Windows OS
// This is Absolute Global per OS
uint64_t GetPerformanceFrequency() noexcept;

// Main Config is HERE
YAML::Node GetLoadedConfig() noexcept;

std::wstring GetPathOfRootConfig() noexcept;
std::wstring GetPathOfBakeryConfig() noexcept;
std::wstring GetPathOfUserConfig() noexcept;

// deprecated
std::wstring GetPathOfLoadedConfig() noexcept;
std::string GetPathOfLoadedConfigAsString() noexcept;

// official
std::wstring GetUserPluginsDir() noexcept;
std::wstring GetSystemPluginsDir() noexcept;
std::wstring GetRootDir() noexcept;
std::wstring GetRootInstallDir() noexcept;  // for cap, ini and dat
std::wstring GetRootUtilsDir() noexcept;
std::wstring GetUserDir() noexcept;
std::wstring GetUserBinDir() noexcept;
std::wstring GetUpgradeProtocolDir();
std::wstring GetBakeryDir() noexcept;
std::wstring GetUserModulesDir() noexcept;
std::filesystem::path GetBakeryFile();
std::wstring GetLocalDir() noexcept;
std::wstring GetStateDir() noexcept;
std::wstring GetLibDir() noexcept;
std::wstring GetAuStateDir() noexcept;
std::wstring GetPluginConfigDir() noexcept;
std::wstring GetUpdateDir() noexcept;       // for incoming MSI
std::wstring GetUserInstallDir() noexcept;  // storage for installed files
std::wstring GetSpoolDir() noexcept;
std::wstring GetTempDir() noexcept;
std::wstring GetLogDir() noexcept;
std::string GetHostName() noexcept;
std::wstring GetWorkingDir() noexcept;
std::wstring GetMsiExecPath() noexcept;

bool IsLoadedConfigOk() noexcept;

bool StoreUserYamlToCache();

std::wstring StoreFileToCache(const std::filesystem::path &file_name);

int RemoveInvalidNodes(YAML::Node node);

enum class FallbackPolicy {
    kNone,      // do not fallback at all
    kStandard,  // load Last Good, if not, generate Default
    kLastGoodOnly,
    kGenerateDefault
};

// YAML API is here
YAML::Node LoadAndCheckYamlFile(const std::wstring &file_name,
                                FallbackPolicy fallback_policy);
YAML::Node LoadAndCheckYamlFile(const std::wstring &file_name);

// ***********************************************************
// API:
// ***********************************************************
// usage auto x = GetVal("global", "name", false)
template <typename T>
T GetVal(std::string_view section_name, std::string_view key, T dflt) noexcept {
    auto yaml = GetLoadedConfig();
    try {
        if (yaml.size() == 0) {
            return dflt;
        }

        auto section = yaml[section_name];
        auto val = section[key];
        if (val.IsScalar()) return val.as<T>();
        return dflt;
    } catch (const std::exception &e) {
        XLOG::l("Cannot read yml file {} with {}.{} code:{}",
                wtools::ToUtf8(GetPathOfLoadedConfig()), section_name, key, e);
    }
    return dflt;
}

inline YAML::Node GetNode(std::string_view section_name,
                          std::string_view key) noexcept {
    auto yaml = GetLoadedConfig();
    try {
        if (yaml.size() == 0) {
            return {};
        }

        auto section = yaml[section_name];
        return section[key];
    } catch (const std::exception &e) {
        XLOG::l("Cannot read yml file {} with {}.{} code:{}",
                wtools::ToUtf8(GetPathOfLoadedConfig()), section_name, key, e);
    }
    return {};
}

inline std::optional<YAML::Node> GetGroup(
    const YAML::Node &yaml, std::string_view section_name) noexcept {
    try {
        if (yaml.size() == 0) {
            return {};
        }

        return yaml[section_name];
    } catch (const std::exception &e) {
        XLOG::d("Absent '{}' in YAML, exception is '{}'", section_name, e);
    }
    return {};
}

inline std::optional<YAML::Node> GetGroupLoaded(
    const std::string &section) noexcept {
    return GetGroup(GetLoadedConfig(), section);
}

// safe method yo extract value from the yaml
template <typename T>
T GetVal(const YAML::Node &yaml, std::string_view name, T dflt) noexcept {
    try {
        if (yaml.size() == 0) {
            return dflt;
        }
        auto val = yaml[name];
        if (!val.IsDefined()) {
            return dflt;
        }
        if (val.IsScalar()) {
            return val.as<T>();
        }
        if (val.IsNull()) {
            return {};
        }
        return dflt;
    } catch (const std::exception &e) {
        XLOG::l("Cannot read yml file {} with {} code:{}",
                wtools::ToUtf8(GetPathOfLoadedConfig()), name, e);
    }
    return dflt;
}

inline YAML::Node GetNode(const YAML::Node &yaml,
                          std::string_view name) noexcept {
    try {
        YAML::Node val = yaml[name];
        if (!val.IsDefined() || val.IsNull()) {
            return {};
        }
        return val;
    } catch (const std::exception &e) {
        XLOG::l("Cannot read yml node in file {} with {} code:{}",
                wtools::ToUtf8(GetPathOfLoadedConfig()), name, e.what());
    }
    return {};
}

template <typename T>
std::vector<T> ConvertNode2Sequence(const YAML::Node &val) noexcept {
    try {
        if (!val.IsDefined() || !val.IsSequence()) {
            return {};
        }

        const auto sz = val.size();
        std::vector<T> arr;
        arr.reserve(sz);
        for (const auto &v : val) {
            if (!v.IsDefined() || v.IsSequence()) {
                XLOG::t(XLOG_FUNC + " Invalid node type");
                continue;
            }
            arr.emplace_back(v.as<T>());
        }
        return arr;
    } catch (const std::exception &e) {
        XLOG::l(XLOG_FUNC + " exception happened '{}'", e.what());
    }
    return {};
}

using StringPairArray = std::vector<std::pair<std::string, std::string>>;

inline StringPairArray ConvertNode2StringPairArray(
    const YAML::Node &val) noexcept {
    try {
        if (!val.IsDefined() || !val.IsSequence()) {
            XLOG::t(XLOG_FUNC + " Invalid node or absent node");
            return {};
        }

        const auto sz = val.size();
        StringPairArray arr;
        arr.reserve(sz);

        for (const auto &v : val) {
            if (!v.IsDefined() || !v.IsMap()) {
                XLOG::t(XLOG_FUNC + " Invalid node type [{}]",
                        static_cast<int>(val.Type()));
                continue;
            }

            auto sub_it = v.begin();  // This iterator points to
                                      // the single key/value pair
            auto name = sub_it->first.as<std::string>();
            auto body = sub_it->second.as<std::string>();
            arr.emplace_back(name, body);
        }
        return arr;

    } catch (const std::exception &e) {
        XLOG::l(XLOG_FUNC + " exception happened '{}'", e.what());
    }

    return {};
}

template <typename T>
std::vector<T> GetArray(std::string_view section_name,
                        std::string_view name) noexcept {
    auto yaml = GetLoadedConfig();
    if (yaml.size() == 0) {
        return {};
    }
    try {
        auto section = yaml[section_name];
        auto val = section[name];
        if (val.IsDefined() && val.IsSequence()) {
            return ConvertNode2Sequence<T>(val);
        }

        // this is OK when nothing inside
        XLOG::d.t("Absent/Empty node {}.{} type is {}", section_name, name,
                  val.Type());
    } catch (const std::exception &e) {
        XLOG::l("Cannot read yml file {} with {}.{} code:{}",
                wtools::ToUtf8(GetPathOfLoadedConfig()), section_name, name,
                e.what());
    }
    return {};
}

// used to convert arrays of maps into string pairs
// special case for more simple version of YAML when we are using
// sequences of maps  '- name: value'
inline StringPairArray GetPairArray(std::string_view section_name,
                                    std::string_view value_name) noexcept {
    auto yaml = GetLoadedConfig();
    if (yaml.size() == 0) {
        return {};
    }
    try {
        auto section = yaml[section_name];
        auto val = section[value_name];
        if (val.IsDefined() && val.IsSequence()) {
            return ConvertNode2StringPairArray(val);
        }

        // this is OK when nothing inside
        XLOG::d.t("Absent/Empty node {}.{} type is {}", section_name,
                  value_name, val.Type());
    } catch (const std::exception &e) {
        XLOG::l("Cannot read yml file {} with {}.{} code:{}",
                wtools::ToUtf8(GetPathOfLoadedConfig()), section_name,
                value_name, e.what());
    }
    return {};
}

// gets string from the yaml and split it in table using space as divider
std::vector<std::string> GetInternalArray(std::string_view section_name,
                                          std::string_view value_name);

void PutInternalArray(YAML::Node yaml_node, std::string_view value_name,
                      const std::vector<std::string> &arr);

void PutInternalArray(std::string_view section_name,
                      std::string_view value_name,
                      const std::vector<std::string> &arr);

// gets string from the yaml and split it in table using space as divider
std::vector<std::string> GetInternalArray(const YAML::Node &yaml_node,
                                          std::string_view name);

template <typename T>
std::vector<T> GetArray(const YAML::Node &yaml, std::string_view node_name) {
    try {
        if (yaml.size() == 0) {
            return {};
        }
        auto val = yaml[node_name];
        if (val.IsSequence()) {
            return ConvertNode2Sequence<T>(val);
        }

        if (!val.IsDefined() || val.IsNull()) {
            XLOG::t("Node '{}' is not defined/empty,return empty array",
                    node_name);
        } else {
            XLOG::d("Node '{}' has bad type [{}]", node_name, val.Type());
        }
    } catch (const std::exception &e) {
        XLOG::l("Cannot read yml file {} with {} code:{}",
                wtools::ToUtf8(GetPathOfLoadedConfig()), node_name, e.what());
    }
    return {};
}

void LogNodeAsBad(const YAML::Node &node, std::string_view comment);

template <typename T>
std::vector<T> GetArray(const YAML::Node &node) {
    try {
        if (node.IsDefined()) {
            if (node.IsSequence()) {
                return ConvertNode2Sequence<T>(node);
            }

            if (node.IsNull()) {
                // this is a valid case, no logging
                return {};
            }
        }
        LogNodeAsBad(node, "Node is not suitable");

    } catch (const std::exception &e) {
        XLOG::l("Cannot read node '{}'", e.what());
    }
    return {};
}

// Merging API. Used to help merge our config files correctly, normally it is
// internal.
// API uses std::string because of YAML has no good support for
// string_view Merges sequence target_group[name] <--- source_group[name] if
// name exists in target no action
bool MergeStringSequence(YAML::Node target_group, YAML::Node source_group,
                         const std::string &name);
// Merges map target_group[name] <--- source_group[name] using key
// if entry with key exists in target no action
bool MergeMapSequence(YAML::Node target_group, YAML::Node source_group,
                      const std::string &name, const std::string &key);
// ***********************************************************

std::string GetMapNodeName(const YAML::Node &node);

namespace details {
void KillDefaultConfig();
void LoadGlobal();
}  // namespace details

class Group {
public:
    Group() noexcept : enabled_in_cfg_(false), exist_in_cfg_(false) {}
    bool existInConfig() const { return exist_in_cfg_; }

    bool enabledInConfig() const { return enabled_in_cfg_; }

protected:
    void reset() {
        name_.clear();
        enabled_in_cfg_ = false;
        exist_in_cfg_ = false;
    }

    mutable std::mutex lock_;
    // std::atomic<std::string> name_;
    std::atomic<bool> enabled_in_cfg_;
    std::atomic<bool> exist_in_cfg_;
    std::string name_;
};

class Global : public Group {
public:
    Global() noexcept;

    void loadFromMainConfig();

    // #TODO move somewhere!
    // transfer global data into app environment
    void setupLogEnvironment() const;

    // accessors
    bool ipv6() const {
        std::lock_guard lk(lock_);
        return ipv6_;
    }
    bool async() const {
        std::lock_guard lk(lock_);
        return async_;
    }

    int port() const {
        std::lock_guard lk(lock_);
        return port_;
    }

    int flushTcp() const {
        std::lock_guard lk(lock_);
        return static_cast<int>(flush_tcp_);
    }

    int globalEncrypt() const {
        std::lock_guard lk(lock_);
        return static_cast<int>(encrypt_);
    }

    std::wstring fullLogFileName() const {
        std::lock_guard lk(lock_);
        return logfile_as_wide_;
    }

    std::string fullLogFileNameAsString() const {
        std::lock_guard lk(lock_);
        return logfile_as_string_;
    }

    std::vector<std::string> enabledSections() const noexcept {
        std::lock_guard lk(lock_);
        return enabled_sections_;
    }
    std::vector<std::string> disabledSections() const noexcept {
        std::lock_guard lk(lock_);
        return disabled_sections_;
    }
    std::vector<std::string> realtimeSections() const noexcept {
        std::lock_guard lk(lock_);
        return realtime_sections_;
    }

    bool realtimeEncrypt() const noexcept {
        std::lock_guard lk(lock_);
        return realtime_encrypt_;
    }

    bool realtimeEnabled() const noexcept {
        std::lock_guard lk(lock_);
        return realtime_enabled_;
    }

    int realtimePort() const noexcept {
        std::lock_guard lk(lock_);
        return realtime_port_;
    }

    int realtimeTimeout() const noexcept {
        std::lock_guard lk(lock_);
        return realtime_timeout_;
    }

    int getWmiTimeout() const noexcept {
        std::lock_guard lk(lock_);
        return wmi_timeout_;
    }
    std::string password() const {
        std::lock_guard lk(lock_);
        return password_;
    }

    std::string realtimePassword() const {
        std::lock_guard lk(lock_);
        return realtime_encrypt_ ? password_ : "";
    }

    std::filesystem::path logPath() const {
        std::lock_guard lk(lock_);
        return yaml_log_path_;
    }
    int debugLogLevel() const {
        std::lock_guard lk(lock_);
        return debug_level_;
    }
    bool windbgLog() const {
        std::lock_guard lk(lock_);
        return windbg_;
    }
    bool eventLog() const {
        std::lock_guard lk(lock_);
        return event_log_;
    }

    auto logFileName() const {
        std::lock_guard lk(lock_);
        return log_file_name_;
    }

    auto allowedSection(std::string_view name) const {
        std::lock_guard lk(lock_);

        // most important is disabled
        if (std::ranges::find(disabled_sections_, std::string(name)) !=
            disabled_sections_.end()) {
            return false;
        }

        if (!enabled_sections_.empty()) {
            return std::ranges::find(enabled_sections_, std::string(name)) !=
                   enabled_sections_.end();
        }

        // default: both entries are empty,  section is enabled
        return true;
    }

    auto isSectionDisabled(const std::string &name) const {
        std::lock_guard lk(lock_);

        // most important is disabled
        return std::ranges::find(disabled_sections_, name) !=
               disabled_sections_.end();
    }

    bool isIpAddressAllowed(std::string_view ip) const {
        if (!of::IsAddress(ip)) {
            XLOG::d(XLOG_FUNC + " Bad param in {}", ip);
            return false;
        }
        std::lock_guard lk(lock_);

        // empty only from vector allows any connection
        if (only_from_.empty()) {
            return true;
        }

        for (const auto &o : only_from_) {
            if (of::IsValid(o, ip)) {
                return true;
            }
        }
        return std::ranges::any_of(only_from_,
                                   [ip](auto o) { return of::IsValid(o, ip); });
    }

    std::vector<std::string> getOnlyFrom() const {
        std::lock_guard lk(lock_);
        return only_from_;
    }

    std::optional<std::string> getPasword() {
        std::lock_guard lk(lock_);
        if (encrypt_) {
            return password_;
        }
        return {};
    }
    void setLogFolder(const std::filesystem::path &forced_path);

private:
    void loadGlobal();
    void loadRealTime();
    void loadLogging();
    void updateLogNames();
    void setDefaults() noexcept;

    // check contents of only_from from the yml and fills array correct
    // * for ipv6-mode added mapped addresses of ipv4-entries and normal
    // ipv6-entries
    // * for non ipv6-mode added only ipv4-entries
    int fillOnlyFrom(const std::vector<std::string> &only) {
        only_from_.clear();

        for (const auto &entry : only) {
            if (!of::IsAddress(entry) && !of::IsNetwork(entry)) {
                XLOG::d("Bad param in ini {}", entry);
                continue;
            }

            const bool only_v4 = !ipv6_;
            const bool entry_ipv6 = of::IsIpV6(entry);

            // skipping ipv6 entries in ipv4 mode
            if (only_v4 && entry_ipv6) {
                continue;
            }

            only_from_.push_back(entry);

            // skipping because of
            // * in ipv4-mode no mapping
            // * for ipv6-entry no mapping too
            if (only_v4 || entry_ipv6) {
                continue;
            }

            // ipv6-mode:
            if (of::IsAddressV4(entry)) {
                // V4 address we are mapping to ipv6
                auto mapped = of::MapToV6Address(entry);
                if (mapped.empty()) {
                    continue;
                }

                only_from_.push_back(mapped);
            } else if (of::IsNetworkV4(entry)) {
                // V4 network we are mapping to ipv6
                auto mapped = of::MapToV6Network(entry);
                if (mapped.empty()) {
                    continue;
                }

                only_from_.push_back(mapped);
            }
        }
        return static_cast<int>(only_from_.size());
    }

    // root
    int port_{kMainPort};
    bool ipv6_{false};
    bool async_{true};
    bool flush_tcp_{false};
    std::vector<std::string> execute_;
    std::vector<std::string> only_from_;
    std::string password_;
    bool encrypt_{false};
    std::string cpuload_method_;

    // sections
    std::vector<std::string> enabled_sections_;
    std::vector<std::string> disabled_sections_;

    // real time
    bool realtime_enabled_{true};
    bool realtime_encrypt_{false};
    int realtime_timeout_{kDefaultRealtimeTimeout};
    int realtime_port_{kDefaultRealtimePort};
    std::vector<std::string> realtime_sections_;

    // wmi global
    int wmi_timeout_{kDefaultWmiTimeout};

    // log
    std::filesystem::path yaml_log_path_;
    int debug_level_{static_cast<int>(
        tgt::IsDebug() ? LogLevel::kLogDebug : LogLevel::kLogBase)};  // 0, 1, 2

    bool windbg_{true};
    bool event_log_{true};
    std::string log_file_name_;

    // derivative
    std::filesystem::path logfile_;
    std::filesystem::path logfile_dir_;
    std::string logfile_as_string_;
    std::wstring logfile_as_wide_;
};

class WinPerf : public Group {
public:
    struct Counter {
        Counter() = default;
        Counter(std::string id, std::string name) noexcept
            : id_(std::move(id)), name_(std::move(name)) {}
        [[nodiscard]] auto name() const noexcept { return name_; }
        [[nodiscard]] auto id() const noexcept { return id_; }

    private:
        const std::string id_;    // example: 234
        const std::string name_;  // example: if
    };

    // API:
    void loadFromMainConfig();

    auto exe() const {
        std::lock_guard lk(lock_);
        return exe_name_;
    }
    auto exeWide() const {
        std::lock_guard lk(lock_);
        return wtools::ConvertToUtf16(exe_name_);
    }

    auto prefix() const {
        std::lock_guard lk(lock_);
        return prefix_;
    }

    auto prefixWide() const {
        std::lock_guard lk(lock_);
        return wtools::ConvertToUtf16(prefix_);
    }

    auto counters() const {
        std::lock_guard lk(lock_);
        return counters_;
    }
    auto countersCount() const {
        std::lock_guard lk(lock_);
        return counters_.size();
    }

    auto timeout() const {
        std::lock_guard lk(lock_);
        return timeout_;
    }

    auto isFork() const {
        std::lock_guard lk(lock_);
        return fork_;
    }

    auto isTrace() const {
        std::lock_guard lk(lock_);
        return trace_;
    }

    // gtest [+]
    std::wstring buildCmdLine() const;

private:
    // Data
    mutable std::mutex lock_;
    // node from the config file
    std::vector<Counter> counters_;
    std::string exe_name_;
    std::string prefix_;
    int timeout_{cfg::kDefaultWinPerfTimeout};
    bool fork_{true};
    bool trace_{false};
};

// $BUILTIN_PLUGINS_PATH$ -> c:\Program Files (x86)\checkmk\service\plugins
// $CUSTOM_PLUGINS_PATH$ -> c:\ProgramData\checkmk\agent\plugins
// $CUSTOM_AGENT_PATH$ ->c:\ProgramData\checkmk\agent
std::string ReplacePredefinedMarkers(std::string_view work_path);

// replaces one value with other
bool ReplaceInString(std::string &in_out, std::string_view marker,
                     std::string_view value);

bool PatchRelativePath(YAML::Node yaml_config, std::string_view group_name,
                       std::string_view key_name, std::string_view subkey_name,
                       std::string_view marker);
class PluginInfo {
public:
    PluginInfo() = default;

    PluginInfo(int the_timeout, std::optional<int> age, int retry,
               bool repair_invalid_utf)
        : defined_(true)
        , async_(age.has_value())
        , timeout_(the_timeout)
        , cache_age_(age.value_or(0))
        , retry_(retry)
        , repair_invalid_utf_(repair_invalid_utf) {
        // validation
    }

    [[nodiscard]] bool async() const noexcept { return async_; }
    [[nodiscard]] int timeout() const noexcept { return timeout_; }
    [[nodiscard]] int cacheAge() const noexcept { return cache_age_; }
    [[nodiscard]] int retry() const noexcept { return retry_; }
    [[nodiscard]] bool defined() const noexcept { return defined_; }
    [[nodiscard]] bool repairInvalidUtf() const noexcept {
        return repair_invalid_utf_;
    }

    void extend(std::string_view group, std::string_view user) noexcept {
        group_ = group;
        user_ = user;
    }

    [[nodiscard]] std::string user() const noexcept { return user_; }
    [[nodiscard]] std::string group() const noexcept { return group_; }

protected:
    bool defined_ = false;
    bool async_ = false;                   // from the config
    int timeout_ = kDefaultPluginTimeout;  // from the config, #TODO chrono
    int cache_age_ = 0;                    // from the config, #TODO chrono
    int retry_ = 0;                        // from the config
    bool repair_invalid_utf_{false};

    std::string user_;   // from the config
    std::string group_;  // from the config
};

template <typename T>
void ApplyValueIfScalar(const YAML::Node &entry, T &var,
                        std::string_view name) noexcept {
    if (!name.data()) {
        XLOG::l(XLOG_FUNC + "name is null");
        return;
    }
    try {
        auto v = entry[name.data()];
        if (v.IsDefined() && v.IsScalar()) {
            var = v.as<T>(var);
        }
    } catch (const std::exception &e) {
        XLOG::l(XLOG_FUNC + "Exception '{}'", e.what());
    }
}

class Plugins : public Group {
public:
    // describes how should certain modules executed
    class ExeUnit : public PluginInfo {
    public:
        ExeUnit() = default;

        ExeUnit(std::string_view pattern, int the_timeout,
                bool repair_invalid_utf, std::optional<int> age, int retry,
                bool run_mode)
            : PluginInfo(the_timeout, age, retry, repair_invalid_utf)  //
            , pattern_{pattern}
            , run_{run_mode} {
            validateAndFix();
        }

        // normally only for testing/simulation
        ExeUnit(std::string_view pattern, const std::string &entry)
            : pattern_{pattern}, source_text_{entry} {
            assign(YAML::Load(entry));
        }

        auto pattern() const noexcept { return pattern_; }
        auto run() const noexcept { return run_; }
        void assign(const YAML::Node &entry);
        void assignGroup(std::string_view group);
        void assignUser(std::string_view user);
        void apply(std::string_view filename, const YAML::Node &entry);
        YAML::Node source() const noexcept { return source_; }
        std::string sourceText() const noexcept { return source_text_; }

        void resetConfig() noexcept {
            async_ = false;
            timeout_ = kDefaultPluginTimeout;
            cache_age_ = 0;
            retry_ = 0;
            run_ = true;
            group_.clear();
            user_.clear();
        }

    private:
        void validateAndFix() {
            if (cacheAge() >= kMinimumCacheAge || cacheAge() == 0) {
                return;
            }

            XLOG::t(
                "Plugin Entry '{}' has too low cache_age: [{}]. Setting at [{}]",
                pattern_, cacheAge(), kMinimumCacheAge);
            cache_age_ = kMinimumCacheAge;
        }

        std::string pattern_;
        std::string source_text_;
        bool run_ = true;
        YAML::Node source_;
#if defined(ENABLE_WHITE_BOX_TESTING)
        friend class AgentConfig;
        FRIEND_TEST(AgentConfig, ExeUnitTest);
#endif
    };

    struct CmdLineInfo {
        std::wstring cmd_line_;
        std::vector<int> timeouts_;
    };

    Plugins() = default;

    // API:
    void loadFromMainConfig(std::string_view group_name);

    // relative high level API to build intermediate data structures
    // from raw data inside the class
    CmdLineInfo buildCmdLine() const;

    auto units() const {
        std::lock_guard lk(lock_);
        return units_;
    }
    auto unitsCount() const {
        std::lock_guard lk(lock_);
        return units_.size();
    }

    auto folders() const {
        std::lock_guard lk(lock_);
        return folders_;
    }

    auto foldersCount() const {
        std::lock_guard lk(lock_);
        return folders_.size();
    }

    auto exe() const {
        std::lock_guard lk(lock_);
        return exe_name_;
    }
    auto exeWide() const {
        std::lock_guard lk(lock_);
        return wtools::ConvertToUtf16(exe_name_);
    }

    auto asyncStart() const {
        std::lock_guard lk(lock_);
        return async_start_;
    }
    auto maxWait() const {
        std::lock_guard lk(lock_);
        return max_wait_;
    }

    bool isLocal() const noexcept { return local_; }

private:
    bool local_{false};
    // Data
    mutable std::mutex lock_;
    // node from the config file
    std::vector<ExeUnit> units_;
    std::vector<std::wstring> folders_;
    std::string exe_name_;
    bool async_start_{true};
    int max_wait_{kDefaultPluginTimeout};
};

std::vector<Plugins::ExeUnit> LoadExeUnitsFromYaml(
    const std::vector<YAML::Node> &yaml_node) noexcept;

// used to setup on start and forever. These environment variables are
// stable
void SetupPluginEnvironment();

void ProcessPluginEnvironment(
    const std::function<void(std::string_view name, std::string_view value)>
        &func);

// called on every connect from monitoring site.
void SetupRemoteHostEnvironment(const std::string &ip_address);

namespace groups {
extern Global g_global;
extern WinPerf g_winperf;
extern Plugins g_plugins;
extern Plugins g_local_group;
}  // namespace groups

inline bool LogPluginOutput() noexcept { return false; }
inline bool LogMrpeOutput() noexcept { return false; }

}  // namespace cma::cfg

namespace cma::cfg {
constexpr std::string_view kIniFromInstallMarker =
    "# Created by Check_MK Agent Installer";

enum class InstallationType { packaged, wato, unknown };

/// returns the type of installation
///
/// possible values wato or packaged, where packaged returned only if the
/// check_mk.install.yml exists and ["global"]["install"] == "no"
InstallationType DetermineInstallationType();

std::filesystem::path ConstructInstallFileName(
    const std::filesystem::path &dir);
std::string ConstructTimeString();

namespace products {
constexpr std::string_view kLegacyAgent = "Check_mk Agent";
}  // namespace products

std::string CreateWmicCommand(std::string_view product_name);
bool UninstallProduct(std::string_view name);
std::filesystem::path CreateWmicUninstallFile(
    const std::filesystem::path &temp_dir, std::string_view product_name);
}  // namespace cma::cfg
