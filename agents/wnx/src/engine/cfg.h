
#pragma once

#include <string>
#include <string_view>

#include "common/cfg_info.h"
#include "common/wtools.h"

#include "yaml-cpp/yaml.h"

#include "logger.h"

#include "on_start.h"

namespace cma::cfg {
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
constexpr const wchar_t* kDefaultMainConfig = L"check_mk.yml";
constexpr const wchar_t* kDefaultBakeryExt = L".bakery.yml";
constexpr const wchar_t* kDefaultUserExt = L".user.yml";

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
bool DetermineWorkingFolders(StartTypes Type);

// 2. Prepare List of possible config names
std::vector<std::wstring> DefaultConfigArray(StartTypes Type);

// 3.
// must be called o program start.
// and check done too
[[nodiscard]] bool InitializeMainConfig(
    const std::vector<std::wstring>& ConfigFileNames, bool LoadCacheOnFailure,
    bool UseAggregation);

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

std::wstring GetUserPluginsDir() noexcept;
std::wstring GetSystemPluginsDir() noexcept;
std::wstring GetRootDir() noexcept;
std::wstring GetUserDir() noexcept;
std::wstring GetBakeryDir() noexcept;
std::wstring GetLocalDir() noexcept;
std::wstring GetStateDir() noexcept;
std::wstring GetPluginConfigDir() noexcept;
std::wstring GetSpoolDir() noexcept;
std::wstring GetTempDir() noexcept;
std::wstring GetLogDir() noexcept;
std::string GetHostName() noexcept;
std::wstring GetWorkingDir() noexcept;
std::wstring GetWorkingDir() noexcept;
bool IsLoadedConfigOk() noexcept;

bool StoreUserYamlToCache() noexcept;

std::wstring StoreFileToCache(const std::filesystem::path& Filename) noexcept;

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
YAML::Node LoadAndCheckYamlFile(const std::wstring FileName, int Fallback,
                                int* ErrorCodePtr = nullptr) noexcept;
YAML::Node LoadAndCheckYamlFile(const std::wstring FileName,
                                int* ErrorCodePtr = nullptr) noexcept;

// ***********************************************************
// API:
// ***********************************************************
// usage auto x = GetVal("global", "name", false);
template <typename T>
T GetVal(std::string Section, std::string Name, T Default,
         int* ErrorOut = 0) noexcept {
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
                          int* ErrorOut = 0) noexcept {
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
         int* ErrorOut = 0) noexcept {
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
    if (!Val.IsDefined()) {
        XLOG::d("Bad!");
        return {};
    }
    if (Val.IsSequence()) {
        auto sz = Val.size();
        std::vector<T> arr;
        arr.reserve(sz);
        for (size_t i = 0; i < sz; i++) {
            auto& v = Val[i];
            if (v.IsDefined() && !v.IsNull()) arr.emplace_back(Val[i].as<T>());
        }
        return arr;
    }

    if (Val.IsScalar()) {
        std::vector<T> arr;
        arr.emplace_back(Val.as<T>());
        return arr;
    }
    return {};
}

template <typename T>
std::vector<T> GetArray(std::string Section, std::string Name,
                        int* ErrorOut = 0) noexcept {
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
        else
            XLOG::d.e("Absent/Empty node {}.{} type is {}", Section, Name,
                      val.Type());
    } catch (const std::exception& e) {
        XLOG::l("Cannot read yml file {} with {}.{} code:{}",
                wtools::ConvertToUTF8(GetPathOfLoadedConfig()), Section, Name,
                e.what());
    }
    return {};
}

template <typename T>
std::vector<T> GetArray(const YAML::Node& Yaml, std::string Name,
                        int* ErrorOut = 0) noexcept {
    if (Yaml.size() == 0) {
        if (ErrorOut) *ErrorOut = Error::kEmpty;
        return {};
    }
    try {
        auto val = Yaml[Name];
        if (val.IsDefined() && val.IsSequence())
            return ConvertNode2Sequence<T>(val);
        else
            XLOG::d("Probably wrong something with {}", Name);
    } catch (const std::exception& e) {
        XLOG::l("Cannot read yml file {} with {} code:{}",
                wtools::ConvertToUTF8(GetPathOfLoadedConfig()), Name, e.what());
    }
    return {};
}

/*
// deprecated
inline YAML::Node GetRootSection(std::string Section, int* Error = 0) noexcept {
    using namespace cma::cfg;
    using namespace std;

    auto yaml = GetLoadedConfig();
    if (yaml.size() == 0) {
        if (Error) *Error = Error::kEmpty;
        return {};
    }
    try {
        return yaml[Section];
    } catch (const exception& e) {
        XLOG::l("Cannot read section {} in yml file {} .{} code:{}",
                Section,                                         //
                wtools::ConvertToUTF8(GetPathOfLoadedConfig()),  //
                e.what());
        if (Error) *Error = Error::kNotFound;
        return {};
    }
}
*/

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

    bool realtimeEncrypt() const {
        std::lock_guard lk(lock_);
        return realtime_encrypt_;
    }

    auto getWmiTimeout() const {
        std::lock_guard lk(lock_);
        return wmi_timeout_;
    }
    std::string password() const {
        std::lock_guard lk(lock_);
        return password_;
    }

    bool publicLog() const {
        std::lock_guard lk(lock_);
        return public_log_;
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
        if (cma::tools::Find(disabled_sections_, std::string(Name)))
            return false;

        if (enabled_sections_.size()) {
            return cma::tools::Find(enabled_sections_, std::string(Name));
        }

        // default: both entries are empty,  section is enabled
        return true;
    }

    auto isSectionDisabled(const std::string Name) const {
        std::lock_guard lk(lock_);

        // most important is disabled
        return cma::tools::Find(disabled_sections_, Name);
    }

private:
    // called from ctor or loader
    void calcDerivatives();
    void setDefaults();

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
    bool realtime_encrypt_;
    int realtime_timeout_;
    std::vector<std::string> realtime_sections_;

    // wmi hlobal
    int wmi_timeout_;

    // log
    bool public_log_;
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
};

struct WinPerf : public Group {
public:
    struct Counter {
        Counter() {}
        Counter(const std::string Id, const std::string Name)
            : id_(Id), name_(Name) {}
        auto name() const { return name_; }
        auto id() const { return id_; }

    private:
        const std::string id_;
        const std::string name_;
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

// @core -> c:\Program Files (x86)\check_mk_service\plugins
// @user -> c:\ProgramData\CheckMK\agent\plugins
// @data ->c:\ProgramData\CheckMK\agent
std::string ReplacePredefinedMarkers(const std::string Path);
// mini tool
bool ReplaceInString(std::string& InOut, const std::string Marker,
                     const std::string Replace);

struct PluginInfo {
    PluginInfo() {}
    PluginInfo(bool Async, int Timeout, int Age, int Retry)
        : async_(Async), timeout_(Timeout), cache_age_(Age), retry_(Retry) {}
    auto async() const { return async_; }
    auto timeout() const { return timeout_; }
    auto cacheAge() const { return cache_age_; }
    auto retry() const { return retry_; }

protected:
    bool async_;
    int timeout_;
    int cache_age_;
    int retry_;
};

struct Plugins : public Group {
public:
    // describes how should certain modules executed
    struct ExeUnit : public cma::cfg::PluginInfo {
        ExeUnit() {}
        ExeUnit(const std::string Pattern, bool Async, int Timeout, int Age,
                int Retry, bool Run)
            : PluginInfo(Async, Timeout, Age, Retry)  //
            , pattern_(Pattern)                       //
            , run_(Run) {
            // validation
            if (!async_ && cache_age_ != 0) {
                XLOG::l(
                    "Plugin Entry {} has invalid config async: {} and cache_age: {}. Setting as async.",
                    pattern_, async_, cache_age_);
                async_ = true;
            }
            if (async_ && cache_age_ < kMinimumCacheAge) {
                XLOG::l(
                    "Plugin Entry {} has too low cache_age: {}. Setting at {}",
                    pattern_, cache_age_, kMinimumCacheAge);
                cache_age_ = kMinimumCacheAge;
            }
        }

        auto pattern() const { return pattern_; }
        auto run() const { return run_; }

    private:
        const std::string pattern_;
        bool run_;
    };

    struct CmdLineInfo {
        std::wstring cmd_line_;
        std::vector<int> timeouts_;
    };

    Plugins() : max_wait_(kDefaultPluginTimeout), async_start_(true) {}

    // API:
    void loadFromMainConfig(const std::string GroupName);

    // #TODO gtest
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

};  // namespace cma::cfg

void LoadExeUnitsFromYaml(std::vector<Plugins::ExeUnit>& ExeUnit,
                          const std::vector<YAML::Node> Yaml);

void SetupPluginEnvironment();

namespace groups {
extern Global global;
extern WinPerf winperf;
extern Plugins plugins;
extern Plugins localGroup;
}  // namespace groups

}  // namespace cma::cfg

#include "cfg_details.h"
