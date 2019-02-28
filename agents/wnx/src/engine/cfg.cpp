// Configuration Parameters for whole Agent
#include "stdafx.h"

#define WIN32_LEAN_AND_MEAN
#include <windows.h>

#include <direct.h>  // known path
#include <shellapi.h>
#include <shlobj.h>  // known path

#include <atomic>
#include <filesystem>
#include <string>

#include "common/cfg_info.h"
#include "common/wtools.h"

#include "tools/_misc.h"     // setenv
#include "tools/_process.h"  // GetSomeFolder...
#include "tools/_raii.h"     // on out
#include "tools/_tgt.h"      // we need IsDebug

#include "yaml-cpp/yaml.h"

#include "cfg.h"
#include "cfg_details.h"
#include "logger.h"
#include "read_file.h"

namespace cma::cfg {

std::wstring WinPerf::buildCmdLine() const {
    std::unique_lock lk(lock_);
    auto counters = counters_;
    lk.unlock();

    std::wstring cmd_line;
    for (const auto& counter : counters) {
        if (counter.id().length() && counter.name().length()) {
            // check for allowed
            std::string name_to_check = vars::kWinPerfPrefixDefault;
            name_to_check += '_';
            name_to_check += counter.name();
            if (groups::global.isSectionDisabled(name_to_check)) continue;

            // adding to command line
            std::wstring name = wtools::ConvertToUTF16(counter.id());
            std::replace(name.begin(), name.end(), L' ', L'*');
            cmd_line += name;
            cmd_line += L":";
            cmd_line += wtools::ConvertToUTF16(counter.name());
            cmd_line += L" ";
        }
    }
    if (!cmd_line.empty() && cmd_line.back() == L' ') cmd_line.pop_back();
    return cmd_line;
}

namespace details {
ConfigInfo G_ConfigInfo;
// store boot fixed data
uint64_t RegisteredPerformanceFreq = wtools::QueryPerformanceFreq();
}  // namespace details

// API

uint64_t GetPerformanceFrequency() noexcept {
    return details::RegisteredPerformanceFreq;
}

YAML::Node GetLoadedConfig() noexcept {
    return details::G_ConfigInfo.getConfig();
}

std::wstring GetPathOfRootConfig() noexcept {
    return details::G_ConfigInfo.getRootYamlPath();
}
std::wstring GetPathOfBakeryConfig() noexcept {
    return details::G_ConfigInfo.getBakeryYamlPath();
}
std::wstring GetPathOfUserConfig() noexcept {
    return details::G_ConfigInfo.getUserYamlPath();
}

std::wstring GetPathOfLoadedConfig() noexcept {
    using namespace wtools;

    std::wstring wstr = fmt::format(
        L"'{}' '{}' '{}'", details::G_ConfigInfo.getRootYamlPath().c_str(),
        details::G_ConfigInfo.getBakeryDir().c_str(),
        details::G_ConfigInfo.getUserYamlPath().c_str());
    return wstr;
}

std::string GetPathOfLoadedConfigAsString() noexcept {
    return wtools::ConvertToUTF8(GetPathOfLoadedConfig());
}

std::wstring GetPathOfLoadedUserConfig() noexcept {
    return details::G_ConfigInfo.getUserYamlPath();
}

std::wstring GetUserPluginsDir() noexcept {
    return details::G_ConfigInfo.getUserPluginsDir();
}

std::wstring GetSystemPluginsDir() noexcept {
    return details::G_ConfigInfo.getSystemPluginsDir();
}

std::wstring GetUserDir() noexcept {
    return details::G_ConfigInfo.getUserDir();
}

std::wstring GetBakeryDir() noexcept {
    return details::G_ConfigInfo.getBakeryDir();
}

std::wstring GetRootDir() noexcept {
    return details::G_ConfigInfo.getRootDir();
}

std::wstring GetLocalDir() noexcept {
    return details::G_ConfigInfo.getLocalDir();
}

std::wstring GetStateDir() noexcept {
    return details::G_ConfigInfo.getStateDir();
}

std::wstring GetPluginConfigDir() noexcept {
    return details::G_ConfigInfo.getPluginConfigDir();
}

std::wstring GetSpoolDir() noexcept {
    return details::G_ConfigInfo.getSpoolDir();
}

std::wstring GetTempDir() noexcept {
    return details::G_ConfigInfo.getTempDir();
}

std::string GetHostName() noexcept {
    return details::G_ConfigInfo.getHostName();
}

std::wstring GetLogDir() noexcept {
    return details::G_ConfigInfo.getLogFileDir();
}

std::wstring GetWorkingDir() noexcept { return details::G_ConfigInfo.getCwd(); }

// #TODO gtest
bool IsLoadedConfigOk() noexcept { return details::G_ConfigInfo.isOk(); }

bool StoreUserYamlToCache() noexcept {
    namespace fs = std::filesystem;
    auto loaded = GetLoadedConfig();
    if (loaded.IsNull() || !loaded.IsMap()) return false;

    auto user_file = cma::cfg::details::G_ConfigInfo.getUserYamlPath();

    StoreFileToCache(user_file);
    return true;
}
// Copies any file to cache with extension last successfully loaded yaml file in
// the cache
std::wstring StoreFileToCache(const std::filesystem::path& Filename) noexcept {
    namespace fs = std::filesystem;
    std::error_code ec;
    if (!fs::exists(Filename, ec)) {
        XLOG::d("Attempting to save into cache not existing file '{}'",
                Filename.u8string());
        return {};
    }

    auto cache_path = details::G_ConfigInfo.getCacheDir();
    if (cache_path.empty()) {
        XLOG::l(XLOG_FLINE + "Can't create folder {}", cache_path.u8string());
        return {};
    }

    auto f = Filename;

    auto cache_file = cache_path / f.filename();

    try {
        // check copy over itself: this happens when cache is loaded
        if (Filename == cache_file.wstring()) return cache_file.wstring();

        std::error_code ec;
        fs::copy(fs::path(Filename), cache_file,
                 fs::copy_options::overwrite_existing, ec);
        if (ec.value() == 0) return cache_file.wstring();
        XLOG::l("Attempt to copy config file to cache {} failed with error {}",
                fs::path(Filename).u8string(), cache_file.u8string(),
                ec.value());

    } catch (std::exception& e) {
        XLOG::l("Exception during YAML saving to cache {}", e.what());
    } catch (...) {
        XLOG::l("Unbelievable!");
    }

    return cache_file.wstring();
}

// gtest [+]
// returns address where we could found cached config file
std::wstring GetYamlFromCache() noexcept {
    auto cache_path = details::G_ConfigInfo.getCacheDir();
    if (cache_path.empty()) {
        XLOG::l(XLOG_FLINE + "Can\'t create folder %s", cache_path.u8string());
        return {};
    }
    auto cache_file = cache_path / kDefaultConfigCacheFileName;
    if (std::filesystem::exists(cache_file)) return cache_file.wstring();

    return {};
}

}  // namespace cma::cfg

namespace cma::cfg::details {
std::filesystem::path G_SolutionPath = SOLUTION_DIR;

void LoadGlobal() {
    groups::global.loadFromMainConfig();
    groups::global.setupEnvironment();
}

// test and reset function
void KillDefaultConfig() { details::G_ConfigInfo.cleanAll(); }

//
// creates predefined list of folders where we are going to search for a files
//
// ATTENTION: Production BUILD WILL OVERRIDE THIS During start
// normally you have to access in production build only to the folder where
// service is installed
static std::vector<std::filesystem::path> FillExternalCommandPaths() {
    using namespace std;
    using namespace std::filesystem;

    // #TODO replace with registry reading
    wstring service_path_old = L"C:\\Program Files (x86)\\check_mk";
    wstring service_path_new = L"C:\\Program Files (x86)\\check_mk_service";

    auto cur_dir = cma::tools::win::GetCurrentFolder();
    if (!exists(cur_dir)) {
        cur_dir.resize(0);
    }

    wstring exe_path = wtools::GetCurrentExePath();

    // filling
    vector<path> full;
    {
        auto remote_machine_string = cma::tools::win::GetEnv(L"REMOTE_MACHINE");

        // development deployment
        if (remote_machine_string[0]) full.emplace_back(remote_machine_string);

        // tests
        if (cur_dir.size()) full.emplace_back(cur_dir);

        // own path
        if (exe_path.size()) full.emplace_back(exe_path);

        // location of the services
        full.emplace_back(service_path_new);
        full.emplace_back(service_path_old);
    }

    // normalization
    vector<path> v;
    for (const auto& p : full) {
        v.emplace_back(p.lexically_normal());
    }

    return v;
}

// Typically called ONLY bu ConfigInfo
bool Folders::setRoot(const std::wstring& ServiceValidName,  // look in registry
                      const std::wstring& RootFolder         // look in disk
)

{
    using namespace std;
    namespace fs = std::filesystem;
    // code is a bit strange, because we have to have possibility use
    // one of possible roots
    // storage for paths
    vector<fs::path> full;
    auto emplace_parent = [&full](fs::path Path) {
        if (Path.empty()) return;

        std::error_code ec;
        if (fs::exists(Path, ec)) {
            // location of the services
            auto p = Path.parent_path();
            full.emplace_back(p.lexically_normal());
        } else {
            XLOG::l("Cannot emplace back path {}, error_code: {}",
                    Path.u8string(), ec.value());
        }
    };

    // Path from registry if provided(watest doesn't provide)
    auto service_path_new = FindServiceImagePath(ServiceValidName);
    emplace_parent(service_path_new);

    // working folder
    if (full.size() == 0) {
        error_code ec;
        fs::path work_dir = RootFolder;
        if (fs::exists(work_dir, ec))
            full.emplace_back(work_dir.lexically_normal());
    }

    // Current exe path used for tests
    if (full.size() == 0) {
        error_code ec;
        auto cur_dir = fs::current_path(ec);
        if (ec.value() == 0 && fs::exists(cur_dir, ec))
            full.emplace_back(cur_dir.lexically_normal());
    }

    if (full.size() == 0) {
        XLOG::l(XLOG_FUNC + " Parameters are invalid");
        return false;
    }

    root_ = full[0];

    return true;
}  // namespace cma::cfg::details

void Folders::createDataFolderStructure(const std::wstring& AgentDataFolder) {
    data_ = makeDefaultDataFolder(AgentDataFolder);
}

void Folders::cleanAll() {
    root_ = L"";
    data_ = L"";
    public_logs_ = L"";
    private_logs_ = L"";
}

//
// Not API. But quit important
// Create project defined Directory Structure in the Data Folder
// gtest[+] indirectly
// Returns error code
static auto CreateTree(const std::filesystem::path& Path) {
    namespace fs = std::filesystem;

    // directories to be created
    // should be more clear defined in cfg_info
    auto dir_list = {dirs::kBakery,         // config file(s)
                     dirs::kCache,          // cached data from agent
                     dirs::kState,          // state folder
                     dirs::kSpool,          // keine Ahnung
                     dirs::kUserPlugins,    // user plugins
                     dirs::kLocal,          // user local plugins
                     dirs::kTemp,           //
                     dirs::kPluginConfig};  //

    for (auto dir : dir_list) {
        std::error_code ec;
        auto success = fs::create_directories(Path / dir, ec);
        if (!success && ec.value() != 0) return ec.value();
    }

    return 0;
}

//
// if AgentDataFolder is empty(this is default behavior ) tries
// to create folder structure in next folders:
// 1. ProgramData/CorpName/AgentName
// 2. Public/CorpName/AgentName
//
std::filesystem::path Folders::makeDefaultDataFolder(
    const std::wstring& AgentDataFolder) {
    using namespace cma::tools;
    namespace fs = std::filesystem;
    auto draw_folder = [](const std::wstring& DataFolder) -> auto {
        fs::path app_data = DataFolder;
        app_data /= cma::cfg::kAppDataCompanyName;
        app_data /= cma::cfg::kAppDataAppName;
        return app_data;
    };

    if (AgentDataFolder.empty()) {
        auto app_data_folder = win::GetSomeSystemFolder(FOLDERID_ProgramData);
        // Program Data, normal operation
        auto app_data = draw_folder(app_data_folder);
        auto ret = CreateTree(app_data);
        if (ret == 0) return app_data;
        XLOG::l("Failed to access ProgramData Folder {}", ret);

        // Public, usually during testing
        app_data_folder = win::GetSomeSystemFolder(FOLDERID_Public);
        app_data = draw_folder(app_data_folder);
        ret = CreateTree(app_data);
        if (ret == 0) return app_data;
        XLOG::l("Failed to access Public Folder {}", ret);
        return {};
    } else {
        // testing path
        auto app_data = draw_folder(AgentDataFolder);
        auto ret = CreateTree(app_data);
        if (ret == 0) return app_data;
        XLOG::l("Failed to access Public Folder {}", ret);
        return {};
    }
}

}  // namespace cma::cfg::details

namespace cma::cfg {

// looks on path for config
// accepts either full path or just name of config
// Returns loaded one
bool InitializeMainConfig(const std::vector<std::wstring>& ConfigFileNames,
                          bool UseCacheOnFailure, bool UseAggregation) {
    namespace fs = std::filesystem;
    // ATTEMPT TO LOAD root config
    std::wstring usable_name;

    for (auto& name : ConfigFileNames) {
        // Root
        auto full_path = FindConfigFile(GetRootDir(), name);
        if (full_path.empty()) {
            XLOG::l.i(
                "Loading {} direct. User and Bakery files will be IGNORED",
                wtools::ConvertToUTF8(name));
            auto loaded = details::G_ConfigInfo.loadDirect(name);
            if (!loaded) continue;

            // file is loaded, write info in config file
            fs::path root_yaml = GetRootDir();
            XLOG::l("Loaded {} file, ONLY FOR debug/test mode",
                    root_yaml.u8string());

            // exit because full path
            return true;
        }

        // this is standard method
        fs::path root_yaml = GetRootDir();
        root_yaml /= name;
        XLOG::d("Found root config on path {}", root_yaml.u8string());
        usable_name = name;
        break;
    }

    auto code = details::G_ConfigInfo.loadAggregated(
        usable_name, UseCacheOnFailure, UseCacheOnFailure);

    if (code >= 0) return true;

    XLOG::l.e("Failed usable_name: '{}' at root: '{}' code is '{}'",
              wtools::ConvertToUTF8(usable_name),
              details::G_ConfigInfo.getRootDir().u8string(), code);

    return false;
}  // namespace cma::cfg

std::vector<std::wstring> DefaultConfigArray(StartTypes Type) {
    std::vector<std::wstring> cfg_files;
    cfg_files.emplace_back(files::kDefaultMainConfig);
    return cfg_files;
}

// API load all sections we can have in yaml
void ProcessKnownConfigGroups() {
    groups::global.loadFromMainConfig();
    groups::winperf.loadFromMainConfig();
    groups::plugins.loadFromMainConfig(groups::kPlugins);
    groups::localGroup.loadFromMainConfig(groups::kLocalGroup);
}

// API take loaded config and use it!
void SetupEnvironmentFromGroups() {
    groups::global.setupEnvironment();  // at the moment only global
}

// Find any file, usually executable on one of the our paths
// for execution
const std::wstring FindExeFileOnPath(const std::wstring File) {
    using namespace std::filesystem;
    auto paths = details::G_ConfigInfo.getExePaths();
    for (const auto& dir : paths) {
        auto file_path = dir / File;
        if (exists(file_path)) {
            return file_path.lexically_normal().wstring();
        }
    }
    return {};
}

std::vector<std::filesystem::path> GetExePaths() {
    return details::G_ConfigInfo.getExePaths();
}

// Find cfg file, usually YAML on one of the our paths for config
const std::wstring FindConfigFile(std::filesystem::path Dir,
                                  const std::wstring File) {
    namespace fs = std::filesystem;
    XLOG::d.t("trying path {}", Dir.u8string());
    auto file_path = Dir / File;
    std::error_code ec;
    if (fs::exists(file_path, ec)) {
        return file_path.lexically_normal().wstring();
    }
    XLOG::l("Config file '{}' not found status {}", file_path.u8string(),
            ec.value());
    return {};
}
};  // namespace cma::cfg

namespace cma::cfg {

// gtest [+] everywhere
const std::string GetCurrentLogFileName() {
    if (ConfigLoaded()) return groups::global.fullLogFileNameAsString();

    auto dir = cma::tools::win::GetSomeSystemFolder(cma::cfg::kPublicFolderId);
    static bool first_start = true;
    static std::string fname;
    if (first_start) {
        first_start = false;
        static std::filesystem::path p = dir;
        p /= kDefaultLogFileName;
        fname = p.u8string();
    }
    return fname;
}

const int GetCurrentDebugLevel() {
    if (ConfigLoaded()) return groups::global.debugLogLevel();
    return kDefaultLogLevel;
}

XLOG::EventLevel GetCurrentEventLevel() {
    return XLOG::EventLevel::kLogCritical;
}

const bool GetCurrentWinDbg() {
    if (ConfigLoaded()) return groups::global.windbgLog();
    return true;
}

const bool GetCurrentEventLog() {
    if (ConfigLoaded()) return groups::global.eventLog();
    return true;
}

}  // namespace cma::cfg

namespace cma::cfg {

// Safe loader of any yaml file with fallback on fail
YAML::Node LoadAndCheckYamlFile(const std::wstring FileName, int Fallback,
                                int* ErrorCodePtr) noexcept {
    namespace fs = std::filesystem;
    auto file_name = wtools::ConvertToUTF8(FileName);
    std::error_code ec;
    if (fs::exists(file_name)) {
        int error_code = 0;
        try {
            YAML::Node config = YAML::LoadFile(file_name);
            if (config[groups::kGlobal].IsDefined()) {
                if (ErrorCodePtr) *ErrorCodePtr = 0;
                return config;
            } else {
                error_code = ErrorCode::kNotCheckMK;
            }
        } catch (const YAML::ParserException& e) {
            XLOG::l.crit(XLOG_FLINE + " yaml: '{}'", e.what());
            error_code = ErrorCode::kMalformed;
        } catch (const YAML::BadFile& e) {
            XLOG::l.crit(XLOG_FLINE + " yaml: '{}'", e.what());
            error_code = ErrorCode::kMissing;
        } catch (...) {
            XLOG::l.crit("Strange exception");
            error_code = ErrorCode::kWeird;
        }
        if (ErrorCodePtr) *ErrorCodePtr = error_code;
    } else {
        XLOG::l("Attempt to load non-existing '{}', fallback...", file_name);
    }

    switch (Fallback) {
        case FallbackPolicy::kNone:
            return {};
        case FallbackPolicy::kGenerateDefault:
            xlog::l(XLOG_FLINE + " Error: Fallback %d NOT SUPPORTED", Fallback);
            return {};
        case FallbackPolicy::kLastGoodOnly:
            xlog::l(XLOG_FLINE + " Error: Fallback %d NOT SUPPORTED", Fallback);
            return {};
        case FallbackPolicy::kStandard:
            // try to use last good
            // generate good one and return
            xlog::l(XLOG_FLINE + " Error: Fallback %d NOT SUPPORTED", Fallback);
            return {};
        default:
            xlog::l(XLOG_FLINE + " Bad value used");
            return {};
    }
}

YAML::Node LoadAndCheckYamlFile(const std::wstring FileName,
                                int* ErrorCodePtr) noexcept {
    return LoadAndCheckYamlFile(FileName, kNone, ErrorCodePtr);
}

void SetupPluginEnvironment() {
    using namespace std;
    std::pair<std::string, std::wstring> dirs[] = {
        //
        {string(envs::kMkLocalDirName), cma::cfg::GetLocalDir()},
        {string(envs::kMkStateDirName), cma::cfg::GetStateDir()},
        {string(envs::kMkPluginsDirName), cma::cfg::GetUserPluginsDir()},
        {string(envs::kMkTempDirName), cma::cfg::GetTempDir()},
        {string(envs::kMkLogDirName), cma::cfg::GetLogDir()},
        {string(envs::kMkConfDirName), cma::cfg::GetPluginConfigDir()},
        {string(envs::kMkSpoolDirName), cma::cfg::GetSpoolDir()},
        //
    };

    for (auto& d : dirs)
        cma::tools::win::SetEnv(d.first, wtools::ConvertToUTF8(d.second));
}

};  // namespace cma::cfg

namespace cma::cfg::details {
void ConfigInfo::initAll(
    const std::wstring& ServiceValidName,  // look in registry
    const std::wstring& RootFolder,        // look in disk
    const std::wstring& AgentDataFolder)   // look in dis
{
    initEnvironment();
    folders_.setRoot(ServiceValidName, RootFolder);
    folders_.createDataFolderStructure(AgentDataFolder);

    // exe
    auto root = folders_.getRoot();
    constexpr const wchar_t* dir_tails[] = {
        dirs::kAgentBin, dirs::kAgentPlugins, dirs::kAgentProviders,
        dirs::kAgentUtils};
    for (auto& d : dir_tails) exe_command_paths_.emplace_back((root / d));
    exe_command_paths_.emplace_back(root);

    // all paths where we are looking for config files
    config_dirs_.emplace_back(folders_.getRoot());
    config_dirs_.emplace_back(folders_.getBakery());
    config_dirs_.emplace_back(folders_.getUser());
}

// normally used to reload configs or testing
void ConfigInfo::cleanAll() {
    std::lock_guard lk(lock_);
    XLOG::l.t(XLOG_FUNC + " !");
    exe_command_paths_.resize(0);  // root/utils, root/plugins etc
    config_dirs_.resize(0);        // root und data

    folders_.cleanAll();

    yaml_.reset();
    root_yaml_path_ = L"";
    user_yaml_path_ = L"";
    bakery_yaml_path_ = L"";
    aggregated_ = false;
    generated_ = false;
    ok_ = false;
}

void ConfigInfo::initEnvironment() {
    namespace fs = std::filesystem;
    // host name
    char host_name[256] = "";
    auto ret = ::gethostname(host_name, 256);
    if (ret != 0) {
        XLOG::l("Can\'t call gethostname, error {}", ret);
    }
    host_name_ = host_name;

    // working directory
    cwd_ = fs::current_path().wstring();
}

// probably global in the future
static void PrepareEnvironment() {
    using namespace std;
    using namespace cma::cfg;

    namespace fs = std::filesystem;

    auto fs_state_path = details::G_ConfigInfo.getStateDir();
    auto state_path = fs_state_path.u8string();

    // delete all files in folder - this is DEBUG ONLY
    if (0 && tgt::IsDebug()) {
        // #TDO remove testing code
        // code below is for early test and to be removed
        XLOG::l("RESETTING DAMNED STATE FOLDER - THIS IS NOT FOR PRODUCTION!");
        std::error_code ec;
        fs::remove_all(state_path, ec);
        if (ec.value()) {
            XLOG::l("Not enough writes to clear state file folder");
        }
        fs::create_directory(state_path);
    }
}

static bool IsYamlMap(YAML::Node Node) {
    if (!Node.IsDefined()) return false;
    return Node.IsMap();
}

static bool IsYamlSeq(YAML::Node Node) {
    if (!Node.IsDefined()) return false;
    return Node.IsSequence();
}

static bool IsYamlScalar(YAML::Node Node) {
    if (!Node.IsDefined()) return false;
    return Node.IsScalar();
}

// #TODO logging
bool ConfigInfo::smartMerge(YAML::Node Target, const YAML::Node Src) {
    // we are scanning source
    for (YAML::const_iterator it = Src.begin(); it != Src.end(); ++it) {
        auto& f = it->first;
        auto& s = it->second;
        if (!f.IsDefined()) {
            XLOG::l.bp(XLOG_FLINE + "  problems here");
            continue;
        }

        auto name = it->first.as<std::string>();
        auto grp = Target[name];
        if (IsYamlMap(grp)) {
            if (IsYamlMap(s)) {
                for (YAML::const_iterator itx = s.begin(); itx != s.end();
                     ++itx) {
                    smartMerge(grp, s);
                    // auto namex = itx->first.as<std::string>();
                    // grp[namex] = itx->second;
                }
            } else {
                XLOG::l.bp(XLOG_FLINE + " expected map from source {}", name);
            }
            continue;
        } else if (IsYamlSeq(grp)) {
            if (IsYamlSeq(s)) {
                grp = s;
            } else {
                XLOG::l.bp(XLOG_FLINE + " bad my bad");
            }
            continue;
        } else {
            if (s.IsDefined())
                grp = s;
            else {
                XLOG::l.bp(XLOG_FLINE + " bad src");
            }
        }
    }

    if (0) {
        std::filesystem::path temp_folder = "c:\\dev\\shared";
        auto path = temp_folder / "out";

        std::ofstream ofs(path.u8string());
        ofs << Target;
    }

    return true;
}

std::vector<ConfigInfo::YamlData> ConfigInfo::buildYamlData(
    const std::wstring& ConfigFileName) const noexcept {
    std::vector<YamlData> yamls = {
        {getRootDir() / ConfigFileName, root_yaml_time_},
        {getBakeryDir() / ConfigFileName, bakery_yaml_time_},
        {getUserDir() / ConfigFileName, user_yaml_time_}};

    yamls[1].path_.replace_extension(files::kDefaultBakeryExt);
    yamls[2].path_.replace_extension(files::kDefaultUserExt);

    for (auto& yd : yamls) {
        yd.loadFile();
    }

    return yamls;
}

// Config is typical config from the root
// we will load all others configs and try to merge
// success ALWAYS
void ConfigInfo::loadYamlDataWithMerge(YAML::Node Config,
                                       const std::vector<YamlData>& Yd) {
    namespace fs = std::filesystem;
    bool bakery_ok = false;
    bool user_ok = false;
    try {
        if (Yd[1].exists()) {
            YAML::Node b = YAML::LoadFile(Yd[1].path_.u8string());
            smartMerge(Config, b);
            bakery_ok = true;
        }
    } catch (...) {
        XLOG::l.bp("Bakery {} is bad", Yd[1].path_.u8string());
    }

    try {
        if (Yd[2].exists()) {
            YAML::Node b = YAML::LoadFile(Yd[2].path_.u8string());
            smartMerge(Config, b);
            user_ok = true;
        }
    } catch (...) {
        XLOG::l.bp("Bakery {} is bad", Yd[1].path_.u8string());
    }

    std::lock_guard lk(lock_);
    root_yaml_time_ = Yd[0].timestamp();
    bakery_yaml_time_ = bakery_ok ? Yd[1].timestamp() : bakery_yaml_time_.min();
    bakery_ok_ = bakery_ok;
    user_yaml_time_ = user_ok ? Yd[2].timestamp() : user_yaml_time_.min();
    user_ok_ = user_ok;
    yaml_ = Config;
    XLOG::d.t(
        "Loaded Config's root: '{}' size={} bakery: '{}' size={} user: '{}' size={}",
        Yd[0].path_.u8string(), Yd[0].data().size(), Yd[1].path_.u8string(),
        Yd[1].data().size(), Yd[2].path_.u8string(), Yd[2].data().size());

    // setting up paths  to the other files
    root_yaml_path_ = Yd[0].path_;
    bakery_yaml_path_ = Yd[1].path_;
    user_yaml_path_ = Yd[2].path_;
    fs::path temp_folder = "c:\\dev\\shared";
    auto path = temp_folder / "out";

    aggregated_ = true;
    ok_ = true;
}

// This function will load all three YAML files as a one
// Order main -> bakery -> user
// ON SUCCESS -> all successfully loaded diles are cached
// ON FAIL
// standard call is tryAggregateLoad(L"check_mk.yml", true, true);
// #TODO make this function elegant. REFACTOR ASAP
LoadCfgStatus ConfigInfo::loadAggregated(const std::wstring& ConfigFileName,
                                         bool SaveOnSuccess,
                                         bool RestoreOnFail) {
    if (ConfigFileName.empty()) {
        XLOG::l(XLOG_FLINE + " empty name");
        return LoadCfgStatus::kAllFailed;
    }
    namespace fs = std::filesystem;
    using namespace cma::tools;
    std::vector<YamlData> yamls = buildYamlData(ConfigFileName);

    // check root
    auto& root = yamls[0];
    if (!root.exists() || root.data().empty() || root.bad()) {
        XLOG::l.crit("Cannot find/read root cfg '{}'. Installation damaged.",
                     root.path_.u8string());
        return LoadCfgStatus::kAllFailed;
    }

    // check user
    auto& user = yamls[2];
    bool try_cache = user.exists() && user.bad();

    bool changed = false;
    for (auto& yd : yamls) {
        if (yd.changed()) {
            changed = true;
            break;
        }
    }

    if (!changed) return LoadCfgStatus::kFileLoaded;

    int error_code = 0;
    try {
        YAML::Node config = YAML::LoadFile(yamls[0].path_.u8string());

        if (config[groups::kGlobal].IsDefined()) {
            loadYamlDataWithMerge(config, yamls);

            if (ok_ && user_ok_ && SaveOnSuccess) StoreUserYamlToCache();
            return LoadCfgStatus::kFileLoaded;
        } else {
            error_code = ErrorCode::kNotCheckMK;
        }
    } catch (const YAML::ParserException& e) {
        XLOG::l.crit(XLOG_FLINE + " yaml: '{}'", e.what());
        error_code = ErrorCode::kMalformed;
    } catch (const YAML::BadFile& e) {
        XLOG::l.crit(XLOG_FLINE + " yaml: '{}'", e.what());
        error_code = ErrorCode::kMissing;
    } catch (...) {
        XLOG::l.crit("Strange exception");
        error_code = ErrorCode::kWeird;
    }

    if (error_code != 0) {
        ok_ = false;
        return LoadCfgStatus::kAllFailed;
    }
    return LoadCfgStatus::kFileLoaded;
    // CACHE
}

// LOOOONG operation
// when failed old config retained
bool ConfigInfo::loadDirect(const std::filesystem::path FullPath) {
    namespace fs = std::filesystem;
    int error = 0;
    auto file = FullPath;

    fs::path fpath = file;
    std::error_code ec;
    if (!fs::exists(fpath, ec)) {
        XLOG::l("File {} not found, code = {}", fpath.u8string(), ec.value());
        return false;
    }
    auto ftime = fs::last_write_time(fpath, ec);

    // we will load when error happens, or time changed or name changed
    bool load_required =
        ec.value() || ftime != root_yaml_time_ || file != root_yaml_path_;

    if (!load_required) {
        return ok_;
    }

    auto new_yaml = LoadAndCheckYamlFile(file, FallbackPolicy::kNone, &error);
    if (!new_yaml.size()) {
        return false;
    }

    std::lock_guard lk(lock_);
    root_yaml_time_ = ftime;
    yaml_ = new_yaml;
    root_yaml_path_ = file;
    XLOG::d.t("Loaded Config from  {}", file.u8string());

    // setting up paths  to the other files
    user_yaml_path_ = FullPath;
    root_yaml_time_ = std::filesystem::last_write_time(FullPath);
    user_yaml_path_.clear();
    user_yaml_time_ = decltype(user_yaml_time_)::min();
    bakery_yaml_path_.clear();
    user_yaml_time_ = user_yaml_time_;
    aggregated_ = false;
    ok_ = true;
    return true;
}

}  // namespace cma::cfg::details
