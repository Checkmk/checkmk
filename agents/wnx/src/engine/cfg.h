
#pragma once

#include <functional>
#include <string>
#include <string_view>

#include "common/cfg_info.h"
#include "common/wtools.h"
#include "logger.h"
#include "on_start.h"
#include "onlyfrom.h"
#include "yaml-cpp/yaml.h"

namespace cma {
// set only when executable works as a service
bool IsService();
bool IsTest();
}  // namespace cma

namespace cma::cfg {
constexpr std::string_view kBuidlHashValue = "DEFADEFADEFA";
// bit mask
enum LoadCfgStatus {
    kAllFailed = -2,    // root config not found
    kCacheFailed = -1,  // cached not found, only root loaded, user is bad
    kFileLoaded = 0,    // all loaded
    kCacheLoaded = 1,   // user is bad, cache loaded
};

enum Error {
    kOk = 0,     //
    kEmpty = 1,  // config is empty
    kNotFound    // name not found

};

namespace files {

// names of file
constexpr const wchar_t* kDefaultMainConfigName = L"check_mk";
constexpr const wchar_t* kDefaultMainConfig = L"check_mk.yml";

constexpr const wchar_t* kCapFile = L"plugins.cap";
constexpr const wchar_t* kIniFile = L"check_mk.ini";

constexpr std::wstring_view kDatFile = L"checkmk.dat";
constexpr std::wstring_view kUserYmlFile = L"check_mk.user.yml";

// extensions
constexpr const wchar_t* kDefaultBakeryExt = L".bakery.yml";
constexpr const wchar_t* kDefaultUserExt = L".user.yml";

// special
constexpr std::string_view kUpgradeProtocol = "upgrade.protocol";
constexpr std::string_view kInstallProtocol = "install.protocol";
constexpr std::string_view kAgentUpdater = "cmk-update-agent.exe";

// located in test_files/config
// constexpr const wchar_t* kDefaultDevConfig = L"check_mk_dev.yml";
constexpr const wchar_t* kDefaultDevConfigUTF16 = L"check_mk_dev_utf16.yml";
constexpr const wchar_t* kDefaultDevMinimum = L"check_mk_dev_minimum.yml";

constexpr const wchar_t* kDefaultDevUt = L"check_mk_dev_unit_testing.yml";

}  // namespace files

// *******************************************************
// Important internal API
// Example is in OnStart
// *******************************************************

// 1.
// we have to init folders depending from start type
// test, exe or service
// This is done once for whole life-cycle
bool DetermineWorkingFolders(AppType Type);

// 2. Prepare List of possible config names
std::vector<std::wstring> DefaultConfigArray(AppType Type);

// 3.
// must be called o program start.
// and check done too
[[nodiscard]] bool InitializeMainConfig(
    const std::vector<std::wstring>& config_filenames, YamlCacheOp cache_op);

// *******************************************************
// Internal API
// *******************************************************

// provides one or more file name to find and load on
// available paths

// how to use, look OnStart
// this function gets parse yaml to get information into known groups
void ProcessKnownConfigGroups();
void SetupEnvironmentFromGroups();

// sometimes we have to reload config without

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
std::wstring GetFileInstallDir() noexcept;  // for cap, ini and dat
std::wstring GetUserDir() noexcept;
std::wstring GetUpgradeProtocolDir() noexcept;
std::wstring GetBakeryDir() noexcept;
std::filesystem::path GetBakeryFile() noexcept;
std::wstring GetLocalDir() noexcept;
std::wstring GetStateDir() noexcept;
std::wstring GetPluginConfigDir() noexcept;
std::wstring GetUpdateDir() noexcept;       // for incoming MSI
std::wstring GetUserInstallDir() noexcept;  // storage for installed files
std::wstring GetSpoolDir() noexcept;
std::wstring GetTempDir() noexcept;
std::wstring GetLogDir() noexcept;
std::string GetHostName() noexcept;
std::wstring GetWorkingDir() noexcept;
std::wstring GetMsiExecPath() noexcept;

int GetBackupLogMaxCount() noexcept;
size_t GetBackupLogMaxSize() noexcept;

bool IsLoadedConfigOk() noexcept;

bool StoreUserYamlToCache() noexcept;

std::wstring StoreFileToCache(const std::filesystem::path& Filename) noexcept;

int RemoveInvalidNodes(YAML::Node node);

// std::wstring GetUserYamlFromCache() noexcept;

// *******************************************************

// yaml for Humans
enum ErrorCode {
    kMalformed = 1,  // exception during parsing
    kMissing = 2,    // no file at all
    kWeird = 3,      // strange
    kNotCheckMK = 4  // missing critical parts
};

enum FallbackPolicy {
    kNone = 0,      // do not fallback at all
    kStandard = 1,  // load Last Good, if not, generate Default
    kLastGoodOnly = 2,
    kGenerateDefault
};

// YAML API is here
YAML::Node LoadAndCheckYamlFile(const std::wstring& FileName, int Fallback,
                                int* ErrorCodePtr = nullptr) noexcept;
YAML::Node LoadAndCheckYamlFile(const std::wstring& FileName,
                                int* ErrorCodePtr = nullptr) noexcept;

// ***********************************************************
// API:
// ***********************************************************
// usage auto x = GetVal("global", "name", false);
template <typename T>
T GetVal(std::string Section, std::string Name, T Default,
         int* ErrorOut = nullptr) noexcept {
    auto yaml = GetLoadedConfig();
    if (yaml.size() == 0) {
        if (ErrorOut) *ErrorOut = Error::kEmpty;
        return Default;
    }
    try {
        auto section = yaml[Section];
        auto val = section[Name];
        if (val.IsScalar()) return val.as<T>();
        if (val.IsNull()) return {};
        return Default;
    } catch (const std::exception& e) {
        XLOG::l("Cannot read yml file {} with {}.{} code:{}",
                wtools::ConvertToUTF8(GetPathOfLoadedConfig()), Section, Name,
                e.what());
    }
    return Default;
}

// usage auto x = GetVal("global", "name");
inline YAML::Node GetNode(std::string Section, std::string Name,
                          int* ErrorOut = nullptr) noexcept {
    auto yaml = GetLoadedConfig();
    if (yaml.size() == 0) {
        if (ErrorOut) *ErrorOut = Error::kEmpty;
        return {};
    }
    try {
        auto section = yaml[Section];
        return section[Name];
    } catch (const std::exception& e) {
        XLOG::l("Cannot read yml file {} with {}.{} code:{}",
                wtools::ConvertToUTF8(GetPathOfLoadedConfig()), Section, Name,
                e.what());
    }
    return {};
}

// usage auto x = GetVal("global", "name");
inline std::optional<YAML::Node> GetGroup(const YAML::Node& Yaml,
                                          const std::string& Section) noexcept {
    if (Yaml.size() == 0) return {};

    try {
        return Yaml[Section];
    } catch (const std::exception& e) {
        XLOG::d("Absent {} in YAML exception is '{}'", Section, e.what());
    }
    return {};
}

inline std::optional<YAML::Node> GetGroupLoaded(const std::string& Section) {
    return GetGroup(GetLoadedConfig(), Section);
}

// safe method yo extract value from the yaml
template <typename T>
T GetVal(const YAML::Node& Yaml, std::string Name, T Default,
         int* ErrorOut = nullptr) noexcept {
    if (Yaml.size() == 0) {
        if (ErrorOut) *ErrorOut = Error::kEmpty;
        return Default;
    }
    try {
        auto val = Yaml[Name];
        if (!val.IsDefined()) return Default;

        if (val.IsScalar()) return val.as<T>();
        if (val.IsNull()) return {};
        return Default;
    } catch (const std::exception& e) {
        XLOG::l("Cannot read yml file {} with {} code:{}",
                wtools::ConvertToUTF8(GetPathOfLoadedConfig()), Name, e.what());
    }
    return Default;
}

template <typename T>
std::vector<T> ConvertNode2Sequence(const YAML::Node& Val) noexcept {
    try {
        if (!Val.IsDefined() || !Val.IsSequence()) return {};

        auto sz = Val.size();
        std::vector<T> arr;
        arr.reserve(sz);
        for (const auto& v : Val) {
            if (!v.IsDefined() || v.IsSequence()) {
                XLOG::t(XLOG_FUNC + " Invalid node type");
                continue;
            }
            arr.emplace_back(v.as<T>());
        }
        return arr;
    } catch (const std::exception& e) {
        XLOG::l(XLOG_FUNC + " exception happened '{}'", e.what());
    }
    return {};
}

using StringPairArray = std::vector<std::pair<std::string, std::string>>;

inline StringPairArray ConvertNode2StringPairArray(
    const YAML::Node& Val) noexcept {
    try {
        if (!Val.IsDefined() || !Val.IsSequence()) {
            XLOG::t(XLOG_FUNC + " Invalid node or absent node");
            return {};
        }

        auto sz = Val.size();
        StringPairArray arr;
        arr.reserve(sz);

        for (const auto& v : Val) {
            if (!v.IsDefined() || !v.IsMap()) {
                XLOG::t(XLOG_FUNC + " Invalid node type [{}]",
                        static_cast<int>(Val.Type()));
                continue;
            }

            auto sub_it = v.begin();  // This iterator points to
                                      // the single key/value pair
            auto name = sub_it->first.as<std::string>();
            auto body = sub_it->second.as<std::string>();
            arr.emplace_back(name, body);
        }
        return arr;

    } catch (const std::exception& e) {
        XLOG::l(XLOG_FUNC + " exception happened '{}'", e.what());
    }

    return {};
}

template <typename T>
std::vector<T> GetArray(const std::string& Section, const std::string& Name,
                        int* ErrorOut = nullptr) noexcept {
    auto yaml = GetLoadedConfig();
    if (yaml.size() == 0) {
        if (ErrorOut) *ErrorOut = Error::kEmpty;
        return {};
    }
    try {
        auto section = yaml[Section];
        auto val = section[Name];
        if (val.IsDefined() && val.IsSequence())
            return ConvertNode2Sequence<T>(val);

        // this is OK when nothing inside
        XLOG::d.t("Absent/Empty node {}.{} type is {}", Section, Name,
                  val.Type());
    } catch (const std::exception& e) {
        XLOG::l("Cannot read yml file {} with {}.{} code:{}",
                wtools::ConvertToUTF8(GetPathOfLoadedConfig()), Section, Name,
                e.what());
    }
    return {};
}

// used to convert arrays of maps into string pairs
// special case for more simple version of YAML when we are using
// sequences of maps  '- name: value'
inline StringPairArray GetPairArray(const std::string& Section,
                                    const std::string& Name,
                                    int* ErrorOut = nullptr) noexcept {
    auto yaml = GetLoadedConfig();
    if (yaml.size() == 0) {
        if (ErrorOut) *ErrorOut = Error::kEmpty;

        return {};
    }
    try {
        auto section = yaml[Section];
        auto val = section[Name];
        if (val.IsDefined() && val.IsSequence())
            return ConvertNode2StringPairArray(val);

        // this is OK when nothing inside
        XLOG::d.t("Absent/Empty node {}.{} type is {}", Section, Name,
                  val.Type());
    } catch (const std::exception& e) {
        XLOG::l("Cannot read yml file {} with {}.{} code:{}",
                wtools::ConvertToUTF8(GetPathOfLoadedConfig()), Section, Name,
                e.what());
    }
    return {};
}

// gets string from the yaml and split it in table using space as divider
std::vector<std::string> GetInternalArray(const std::string& Section,
                                          const std::string& Name,
                                          int* ErrorOut = nullptr) noexcept;

// opposite operation for the GetInternalArray
void PutInternalArray(YAML::Node Yaml, const std::string& Name,
                      std::vector<std::string>& Arr,
                      int* ErrorOut = nullptr) noexcept;

// opposite operation for the GetInternalArray
// used ONLY for testing
void PutInternalArray(const std::string& Section, const std::string& Name,
                      std::vector<std::string>& Arr,
                      int* ErrorOut = nullptr) noexcept;

// gets string from the yaml and split it in table using space as divider
std::vector<std::string> GetInternalArray(const YAML::Node& yaml_node,
                                          const std::string& name) noexcept;

template <typename T>
std::vector<T> GetArray(const YAML::Node& Yaml, const std::string& Name,
                        int* ErrorOut = nullptr) noexcept {
    if (Yaml.size() == 0) {
        if (ErrorOut) *ErrorOut = Error::kEmpty;
        return {};
    }
    try {
        auto val = Yaml[Name];
        if (val.IsSequence()) return ConvertNode2Sequence<T>(val);

        if (!val.IsDefined() || val.IsNull())
            XLOG::t("Node '{}' is not defined/empty,return empty array", Name);
        else
            XLOG::d("Node '{}' has bad type [{}]", Name, val.Type());
    } catch (const std::exception& e) {
        XLOG::l("Cannot read yml file {} with {} code:{}",
                wtools::ConvertToUTF8(GetPathOfLoadedConfig()), Name, e.what());
    }
    return {};
}

template <typename T>
std::vector<T> GetArray(YAML::Node node) noexcept {
    try {
        if (node.IsDefined() && node.IsSequence())
            return ConvertNode2Sequence<T>(node);
        XLOG::d.t("Invalid node type {}", node.Type());
    } catch (const std::exception& e) {
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
                         const std::string& name) noexcept;
// Merges map target_group[name] <--- source_group[name] using key
// if entry with key exists in target no action
bool MergeMapSequence(YAML::Node target_group, YAML::Node source_group,
                      const std::string& name, const std::string& key) noexcept;
// ***********************************************************

namespace details {
void KillDefaultConfig();
void LoadGlobal();
}  // namespace details

struct Group {
public:
    Group() : enabled_in_cfg_(false), exist_in_cfg_(false) {}
    bool existInConfig() const {
        std::lock_guard lk(lock_);
        return exist_in_cfg_;
    }

    bool enabledInConfig() const {
        std::lock_guard lk(lock_);
        return enabled_in_cfg_;
    }
    std::string name() const noexcept {
        std::lock_guard lk(lock_);
        return name_;
    }

    void reset() {
        std::lock_guard lk(lock_);
        name_ = "";
        enabled_in_cfg_ = false;
        exist_in_cfg_ = false;
    }

protected:
    // Data
    mutable std::mutex lock_;
    std::string name_;
    bool enabled_in_cfg_;
    bool exist_in_cfg_;
};

struct Global : public Group {
public:
    Global();

    void loadFromMainConfig();

    // #TODO move somewhere!
    // transfer global data into app environment
    void setupEnvironment();

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
        return flush_tcp_;
    }

    int globalEncrypt() const {
        std::lock_guard lk(lock_);
        return encrypt_;
    }

    std::wstring fullLogFileName() const {
        std::lock_guard lk(lock_);
        return logfile_as_wide_;
    }

    std::string fullLogFileNameAsString() const {
        std::lock_guard lk(lock_);
        return logfile_as_string_;
    }

    std::vector<std::string> onlyFrom() const noexcept {
        std::lock_guard lk(lock_);
        return only_from_;
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

    auto allowedSection(const std::string_view Name) const {
        std::lock_guard lk(lock_);

        // most important is disabled
        if (cma::tools::find(disabled_sections_, std::string(Name)))
            return false;

        if (!enabled_sections_.empty()) {
            return cma::tools::find(enabled_sections_, std::string(Name));
        }

        // default: both entries are empty,  section is enabled
        return true;
    }

    auto isSectionDisabled(const std::string& Name) const {
        std::lock_guard lk(lock_);

        // most important is disabled
        return cma::tools::find(disabled_sections_, Name);
    }

    bool isIpAddressAllowed(std::string_view Ip) const {
        if (!of::IsAddress(Ip)) {
            XLOG::d(XLOG_FUNC + " Bad param in {}", Ip);
            return false;
        }
        std::lock_guard lk(lock_);

        // empty only from vector allows any connection
        if (only_from_.size() == 0) return true;

        for (auto& o : only_from_) {
            if (of::IsValid(o, Ip)) return true;
        }

        return false;
    }

    std::vector<std::string> getOnlyFrom() const {
        std::lock_guard lk(lock_);
        return only_from_;
    }

    std::optional<std::string> getPasword() {
        std::lock_guard lk(lock_);
        if (encrypt_) return password_;
        return {};
    }

    void updateLogNamesByDefault();

private:
    // called from ctor or loader
    void calcDerivatives();
    void updateLogNames(std::filesystem::path log_path);
    void setDefaults();

    // check contents of only_from from the yml and fills array correct
    // * for ipv6-mode added mapped addresses of ipv4-entries and normal
    // ipv6-entries
    // * for non ipv6-mode added only ipv4-entries
    int fillOnlyFrom(const std::vector<std::string> Only) {
        only_from_.clear();

        for (auto& entry : Only) {
            if (!of::IsAddress(entry) && !of::IsNetwork(entry)) {
                XLOG::d("Bad param in ini {}", entry);
                continue;
            }

            bool only_v4 = !ipv6_;
            bool entry_ipv6 = of::IsIpV6(entry);
            //::IsIpV6(entry);

            // skipping ipv6 entries in ipv4 mode
            if (only_v4 && entry_ipv6) continue;

            only_from_.push_back(entry);

            // skipping because of
            // * in ipv4-mode no mapping
            // * for ipv6-entry no mapping too
            if (only_v4 || entry_ipv6) continue;

            // ipv6-mode:
            if (of::IsAddressV4(entry)) {
                // V4 address we are mapping to ipv6
                auto mapped = of::MapToV6Address(entry);
                if (mapped.empty()) continue;

                only_from_.push_back(mapped);
            } else if (of::IsNetworkV4(entry)) {
                // V4 network we are mapping to ipv6
                auto mapped = of::MapToV6Network(entry);
                if (mapped.empty()) continue;

                only_from_.push_back(mapped);
            }
        }
        return static_cast<int>(only_from_.size());
    }

private:
    // node from the config file
    YAML::Node me_;

    // root
    int port_;
    bool ipv6_;
    bool async_;
    bool flush_tcp_;
    std::vector<std::string> execute_;
    std::vector<std::string> only_from_;
    std::string password_;
    bool encrypt_;

    // sections
    std::vector<std::string> enabled_sections_;
    std::vector<std::string> disabled_sections_;

    // real time
    bool realtime_enabled_;
    bool realtime_encrypt_;
    int realtime_timeout_;
    int realtime_port_;
    std::vector<std::string> realtime_sections_;

    // wmi global
    int wmi_timeout_;

    // log
    std::filesystem::path yaml_log_path_;
    int debug_level_;  // 0, 1, 2

    bool windbg_;
    bool event_log_;
    std::string log_file_name_;

    // derivative
    std::filesystem::path logfile_;
    std::filesystem::path logfile_dir_;
    std::string logfile_as_string_;
    std::wstring logfile_as_wide_;
#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class AgentConfig;
    FRIEND_TEST(AgentConfig, GlobalTest);
#endif
};  // namespace cma::cfg

struct WinPerf : public Group {
public:
    struct Counter {
        Counter() = default;
        Counter(const std::string Id, const std::string Name)
            : id_(Id), name_(Name) {}
        auto name() const noexcept { return name_; }
        auto id() const noexcept { return id_; }

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
        return wtools::ConvertToUTF16(exe_name_);
    }

    auto prefix() const {
        std::lock_guard lk(lock_);
        return prefix_;
    }

    auto prefixWide() const {
        std::lock_guard lk(lock_);
        return wtools::ConvertToUTF16(prefix_);
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

    // gtest [+]
    std::wstring buildCmdLine() const;

private:
    // Data
    mutable std::mutex lock_;
    // node from the config file
    std::vector<Counter> counters_;
    std::string exe_name_;
    std::string prefix_;
    int timeout_;
};

/*
plugins:
# scripts in plugin
    enabled : no
    # default value, you may disable all scripts in local with no
    run : yes
    # folder : default or 'c:\myfolder\'  or whatever your want
    folder :
        - default   # special keyword to use default location
        - c:\mydlx  #
        - c:\zx     #
    # example: the windows_updates.vbs
    # plugin is executed asynchronous
    # and is only updated every 3600 seconds
    # it may fail(timeout / error) up to 3 times before the last known data
is discarded execution : # execution pattern for  windows - updates.vbs:
-pattern : windows_updates.vbs async : yes timeout : 120 cache_age : 3600
retry_count : 3 description : Update!!!!


    - pattern : ps_perf.ps1
    timeout : 20

    - pattern : '*.ps1'
    timeout : 10

    - pattern : '*'
    timeout : 30
    # When using the Check_MK Inventory plugin, it is a good idea to make
the # plugin being executed asynchronous to prevent it from hooking up the
    # whole agent processing.Additionally it should have a execution
timeout.
    - pattern     : mk_inventory.ps1
    async : yes
    timeout : 240
*/

// $BUILTIN_PLUGINS_PATH$ -> c:\Program Files (x86)\checkmk\service\plugins
// $CUSTOM_PLUGINS_PATH$ -> c:\ProgramData\checkmk\agent\plugins
// $CUSTOM_AGENT_PATH$ ->c:\ProgramData\checkmk\agent
std::string ReplacePredefinedMarkers(std::string_view work_path);

// replaces one value with other
bool ReplaceInString(std::string& InOut, std::string_view Marker,
                     std::string_view Replace);

bool PatchRelativePath(YAML::Node Yaml, const std::string& group_name,
                       const std::string& key_name,
                       std::string_view subkey_name, std::string_view marker);
class PluginInfo {
public:
    PluginInfo() {}

    // Async:
    PluginInfo(int timeout, int age, int retry)
        : async_(true)
        , timeout_(timeout)
        , cache_age_(age)
        , retry_(retry)
        , defined_(true) {
        // validation
    }

    // Sync:
    PluginInfo(int timeout, int retry)
        : async_(false)
        , timeout_(timeout)
        , cache_age_(0)
        , retry_(retry)
        , defined_(true) {}
    bool async() const noexcept { return async_; }
    int timeout() const noexcept { return timeout_; }
    int cacheAge() const noexcept { return cache_age_; }
    int retry() const noexcept { return retry_; }
    bool defined() const noexcept { return defined_; }

protected:
    // used only during testing
    void debugInit(bool async_value, int timeout_value, int cache_age,
                   int retry) {
        async_ = async_value;
        timeout_ = timeout_value;
        cache_age_ = cache_age;
        retry_ = retry;
        defined_ = true;
    }

    bool defined_ = false;
    bool async_ = false;

    int timeout_ = 0;    // from the config file, #TODO use chrono
    int cache_age_ = 0;  // from the config file, #TODO use chrono

    int retry_ = 0;
};

struct Plugins : public Group {
public:
    // describes how should certain modules executed
    struct ExeUnit : public cma::cfg::PluginInfo {
        ExeUnit() = default;
        // Sync
        ExeUnit(std::string_view Pattern, int Timeout, int Retry, bool Run)
            : PluginInfo(Timeout, Retry)  //
            , pattern_(Pattern)           //
            , run_(Run) {}

        // Async
        ExeUnit(std::string_view Pattern, int Timeout, int Age, int Retry,
                bool Run)
            : PluginInfo(Timeout, Age, Retry)  //
            , pattern_(Pattern)                //
            , run_(Run) {
            validateAndFix();
        }

        // Only For Testing Automation with Initializer Lists
        ExeUnit(std::string_view Pattern, bool Async, int Timeout, int Age,
                int Retry, bool Run)
            : pattern_(Pattern)  //
            , run_(Run) {
            debugInit(Async, Timeout, Age, Retry);
            // validation
            if (!async_ && cache_age_ != 0) {
                XLOG::d(
                    "Plugin Entry {} has invalid config async: {} and cache_age: {}. Setting as async.",
                    pattern_, async_, cache_age_);
                async_ = true;
            }
            validateAndFix();
        }

        auto pattern() const noexcept { return pattern_; }
        auto run() const noexcept { return run_; }

    private:
        void validateAndFix() {
            if (cacheAge() >= kMinimumCacheAge) return;
            if (cacheAge() == 0) return;  // this is special case

            if (!async_ && cacheAge() == 0) return;

            XLOG::t(
                "Plugin Entry '{}' has too low cache_age: [{}]. Setting at [{}]",
                pattern_, cacheAge(), kMinimumCacheAge);
            cache_age_ = kMinimumCacheAge;
        }

        const std::string pattern_;
        bool run_;
    };

    struct CmdLineInfo {
        std::wstring cmd_line_;
        std::vector<int> timeouts_;
    };

    Plugins() : max_wait_(kDefaultPluginTimeout), async_start_(true) {}

    // API:
    void loadFromMainConfig(const std::string& GroupName);

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
        return wtools::ConvertToUTF16(exe_name_);
    }

    auto asyncStart() const {
        std::lock_guard lk(lock_);
        return async_start_;
    }
    auto maxWait() const {
        std::lock_guard lk(lock_);
        return max_wait_;
    }
    void go();

    bool const isLocal() const { return local_; }

private:
    bool local_;
    // Data
    mutable std::mutex lock_;
    // node from the config file
    std::vector<ExeUnit> units_;
    std::vector<std::wstring> folders_;
    std::string exe_name_;
    bool async_start_;
    int max_wait_;
};

void LoadExeUnitsFromYaml(std::vector<Plugins::ExeUnit>& ExeUnit,
                          const std::vector<YAML::Node>& Yaml) noexcept;

// used to setup on start and forever. These environment variables are stable
void SetupPluginEnvironment();

void ProcessPluginEnvironment(
    std::function<void(std::string_view name, std::string_view value)>);

// called on every connect from monitoring site.
void SetupRemoteHostEnvironment(const std::string& IpAddress);

namespace groups {
extern Global global;
extern WinPerf winperf;
extern Plugins plugins;
extern Plugins localGroup;
}  // namespace groups

inline bool LogPluginOutput() { return false; }
inline bool LogMrpeOutput() { return false; }

}  // namespace cma::cfg

namespace cma::cfg {
constexpr std::string_view kIniFromInstallMarker =
    "# Created by Check_MK Agent Installer";

bool IsIniFileFromInstaller(const std::filesystem::path& filename);

enum class InstallationType { packaged, wato, unknown };
InstallationType DetermineInstallationType() noexcept;
void SetTestInstallationType(cma::cfg::InstallationType installation_type);
std::filesystem::path ConstructInstallFileName(
    const std::filesystem::path& dir) noexcept;
std::string GetTimeString();
}  // namespace cma::cfg

#include "cfg_details.h"
