// Configuration Parameters for whole Agent
#include "stdafx.h"

#define WIN32_LEAN_AND_MEAN
#include <direct.h>  // known path
#include <shellapi.h>
#include <shlobj.h>  // known path
#include <windows.h>

#include <atomic>
#include <filesystem>
#include <string>

#include "cfg.h"
#include "cfg_details.h"
#include "common/cfg_info.h"
#include "common/wtools.h"
#include "logger.h"
#include "read_file.h"
#include "tools/_misc.h"     // setenv
#include "tools/_process.h"  // GetSomeFolder...
#include "tools/_raii.h"     // on out
#include "tools/_tgt.h"      // we need IsDebug
#include "yaml-cpp/yaml.h"

namespace cma {
namespace details {
// internal and hidden variables
// #TODO to be relocated in the application parameters global
bool G_Service = false;  // set to true only when we run service
bool G_Test = false;     // set to true only when we run watest
}  // namespace details

bool IsService() { return details::G_Service; }
bool IsTest() { return details::G_Test; }

};  // namespace cma

namespace cma::cfg {

InstallationType G_TestInstallationType = InstallationType::packaged;
void SetTestInstallationType(InstallationType installation_type) {
    G_TestInstallationType = installation_type;
}

InstallationType DetermineInstallationType() noexcept {
    if (cma::IsTest()) return G_TestInstallationType;

    std::filesystem::path source_ini = cma::cfg::GetFileInstallDir();
    source_ini /= files::kIniFile;
    return IsIniFileFromInstaller(source_ini) ? InstallationType::packaged
                                              : InstallationType::wato;
}

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

// if not empty returns contents of the array
template <typename T>
static std::vector<T> OverrideTargetIfEmpty(YAML::Node target,
                                            YAML::Node source) {
    // special case: we have no node or no valid node in target
    auto target_array = GetArray<T>(target);
    if (target_array.empty()) {
        // we override if we have good source
        // this is important for the strange case with old or bad file
        target = source;
        return {};
    }
    return target_array;
}

// merge source's content into the target if the content is absent in the target
// returns false only when data-structures are invalid
bool MergeStringSequence(YAML::Node target_group, YAML::Node source_group,
                         const std::string& name) noexcept {
    try {
        // check for source. if empty, leave
        auto source = source_group[name];
        if (!source.IsDefined() || !source.IsSequence()) return true;

        // check for target. if empty, override with non empty source, leave
        auto target = target_group[name];
        auto target_array = OverrideTargetIfEmpty<std::string>(target, source);
        if (target_array.empty()) return true;  // nothing to process

        // merging
        auto source_array = GetArray<std::string>(source);

        for (auto source_entry : source_array) {
            auto found = cma::tools::find(target_array, source_entry);
            if (!found) target.push_back(source_entry);
        }

    } catch (const std::exception& e) {
        XLOG::d.t("Failed to merge yaml '{}' seq '{}'", name, e.what());
        return false;
    }
    return true;
}

// merge source's content into the target if the content is absent in the target
// returns false only when data-structures are invalid
bool MergeMapSequence(YAML::Node target_group, YAML::Node source_group,
                      const std::string& name,
                      const std::string& key) noexcept {
    try {
        // check for source, if empty -> leave
        auto source = source_group[name];
        if (!source.IsDefined() || !source.IsSequence()) return true;

        // check for target, if empty override with non empty source and leave
        auto target = target_group[name];
        auto target_array = OverrideTargetIfEmpty<YAML::Node>(target, source);
        if (target_array.empty()) return true;  // nothing to process

        // merging
        // GetVal is used to avoid loop-breaking exceptions on strange or
        // obsolete node
        auto source_array = GetArray<YAML::Node>(source);
        for (auto source_entry : source_array) {
            auto source_key = GetVal(source_entry, key, std::string());

            if (source_key.empty()) continue;  // we skip empty(and bad!)

            if (cma::tools::none_of(target_array, [&](YAML::Node Node) {
                    return source_key == GetVal(Node, key, std::string());
                }))
                target.push_back(source_entry);
        }
    } catch (const std::exception& e) {
        XLOG::d.t("Failed to merge yaml '{}.{}' map '{}'", name, key, e.what());
        return false;
    }

    return true;
}

// we have chaos with globals
namespace details {
ConfigInfo G_ConfigInfo;
// store boot fixed data
uint64_t RegisteredPerformanceFreq = wtools::QueryPerformanceFreq();
}  // namespace details

// stores EVERYTHING which can be configured
namespace groups {
Global global;
WinPerf winperf;
Plugins plugins;
Plugins localGroup;
};  // namespace groups

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

int GetBackupLogMaxCount() noexcept {
    return details::G_ConfigInfo.getBackupLogMaxCount();
}

size_t GetBackupLogMaxSize() noexcept {
    return details::G_ConfigInfo.getBackupLogMaxSize();
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

std::filesystem::path GetBakeryFile() noexcept {
    auto bakery = details::G_ConfigInfo.getBakeryDir();
    bakery /= files::kDefaultMainConfig;
    bakery.replace_extension(files::kDefaultBakeryExt);
    return bakery;
}

std::wstring GetUserInstallDir() noexcept {
    auto data_dir = details::G_ConfigInfo.getUserDir();
    return data_dir / dirs::kUserInstallDir;
}

std::wstring GetRootDir() noexcept {
    return details::G_ConfigInfo.getRootDir();
}

std::wstring GetFileInstallDir() noexcept {
    auto root = details::G_ConfigInfo.getRootDir();
    return root / dirs::kFileInstallDir;
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

std::wstring GetUpdateDir() noexcept {
    return details::G_ConfigInfo.getUpdateDir();
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

std::wstring GetMsiExecPath() noexcept {
    return details::G_ConfigInfo.getMsiExecPath();
}

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
// Copies any file to cache with extension last successfully loaded yaml
// file in the cache
std::wstring StoreFileToCache(const std::filesystem::path& Filename) noexcept {
    namespace fs = std::filesystem;
    std::error_code ec;
    if (!fs::exists(Filename, ec)) {
        XLOG::d("Attempting to save into cache not existing file '{}' [{}]",
                Filename.u8string(), ec.value());
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
        XLOG::l(
            "Attempt to copy config file to cache '{}' failed with error [{}], '{}'",
            fs::path(Filename).u8string(), cache_file.u8string(), ec.value(),
            ec.message());

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

// Typically called ONLY by ConfigInfo
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
            XLOG::l("Cannot emplace back path {}, error_code: [{}] '{}'",
                    Path.u8string(), ec.value(), ec.message());
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

    root_ = full[0].lexically_normal();

    return true;
}  // namespace cma::cfg::details

void Folders::createDataFolderStructure(const std::wstring& AgentDataFolder) {
    try {
        std::filesystem::path folder = AgentDataFolder;
        data_ = makeDefaultDataFolder(folder.lexically_normal().wstring());
    } catch (const std::exception& e) {
        XLOG::l.bp("Cannot create Default Data Folder , exception : {}",
                   e.what());
    }
}

void Folders::cleanAll() {
    root_ = L"";
    data_ = L"";
    public_logs_ = L"";
    private_logs_ = L"";
}

//
// Not API, but quite important
// Create project defined Directory Structure in the Data Folder
// gtest[+] indirectly
// Returns error code
static int CreateTree(const std::filesystem::path& base_path) noexcept {
    namespace fs = std::filesystem;

    // directories to be created
    // should be more clear defined in cfg_info
    auto dir_list = {dirs::kBakery,         // config file(s)
                     dirs::kAgentBin,       // placeholder for ohm
                     dirs::kCache,          // cached data from agent
                     dirs::kState,          // state folder
                     dirs::kSpool,          // keine Ahnung
                     dirs::kUserPlugins,    // user plugins
                     dirs::kLocal,          // user local plugins
                     dirs::kTemp,           //
                     dirs::kInstall,        // for installing data
                     dirs::kUpdate,         // for incoming MSI
                     dirs::kMrpe,           // for incoming mrpe tests
                     dirs::kPluginConfig};  //

    for (auto dir : dir_list) {
        std::error_code ec;
        auto success = fs::create_directories(base_path / dir, ec);
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
bool InitializeMainConfig(const std::vector<std::wstring>& config_filenames,
                          YamlCacheOp cache_op) {
    namespace fs = std::filesystem;
    // ATTEMPT TO LOAD root config
    std::wstring usable_name;

    for (auto& name : config_filenames) {
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
        XLOG::l.i("Found root config on path {}", root_yaml.u8string());
        usable_name = name;
        break;
    }

    auto code = details::G_ConfigInfo.loadAggregated(usable_name, cache_op);

    if (code >= 0) return true;

    XLOG::l.e("Failed usable_name: '{}' at root: '{}' code is '{}'",
              wtools::ConvertToUTF8(usable_name),
              details::G_ConfigInfo.getRootDir().u8string(), code);

    return false;
}

std::vector<std::wstring> DefaultConfigArray(AppType Type) {
    std::vector<std::wstring> cfg_files;

    cfg_files.emplace_back(files::kDefaultMainConfig);
    return cfg_files;
}

// API load all sections we can have in yaml
void ProcessKnownConfigGroups() {
    groups::global.loadFromMainConfig();
    groups::winperf.loadFromMainConfig();
    groups::plugins.loadFromMainConfig(groups::kPlugins);
    groups::localGroup.loadFromMainConfig(groups::kLocal);
}

// API take loaded config and use it!
void SetupEnvironmentFromGroups() {
    groups::global.setupEnvironment();  // at the moment only global
}

// Find any file, usually executable on one of the our paths
// for execution
const std::wstring FindExeFileOnPath(const std::wstring& File) {
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
const std::wstring FindConfigFile(const std::filesystem::path& Dir,
                                  const std::wstring& File) {
    namespace fs = std::filesystem;
    XLOG::d.t("trying path {}", Dir.u8string());
    auto file_path = Dir / File;
    std::error_code ec;
    if (fs::exists(file_path, ec)) {
        return file_path.lexically_normal().wstring();
    }
    XLOG::l("Config file '{}' not found, status [{}]: {}", file_path.u8string(),
            ec.value(), ec.message());
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

XLOG::EventLevel GetCurrentEventLevel() { return XLOG::EventLevel::critical; }

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
YAML::Node LoadAndCheckYamlFile(const std::wstring& FileName, int Fallback,
                                int* ErrorCodePtr) noexcept {
    namespace fs = std::filesystem;
    auto file_name = wtools::ConvertToUTF8(FileName);
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
        case FallbackPolicy::kLastGoodOnly:
        case FallbackPolicy::kStandard:
            XLOG::l(XLOG_FLINE + " Error: Fallback [{}] NOT SUPPORTED",
                    Fallback);
            return {};
        default:
            XLOG::l(XLOG_FLINE + " Bad value used [{}]", Fallback);
            return {};
    }
}

YAML::Node LoadAndCheckYamlFile(const std::wstring& FileName,
                                int* ErrorCodePtr) noexcept {
    return LoadAndCheckYamlFile(FileName, kNone, ErrorCodePtr);
}

std::vector<std::string> StringToTable(const std::string& WholeValue) {
    auto table = cma::tools::SplitString(WholeValue, " ");

    for (auto& value : table) {
        cma::tools::AllTrim(value);
    }

    return table;
}

// gets string from the yaml and split it in table using space as divider
std::vector<std::string> GetInternalArray(const std::string& Section,
                                          const std::string& Name,
                                          int* ErrorOut) noexcept {
    auto yaml = GetLoadedConfig();
    if (yaml.size() == 0) {
        if (ErrorOut) *ErrorOut = Error::kEmpty;
        return {};
    }

    try {
        auto section = yaml[Section];
        return GetInternalArray(section, Name);
    } catch (const std::exception& e) {
        XLOG::l("Cannot read yml file '{}' with '{}.{}' code:{}",
                wtools::ConvertToUTF8(GetPathOfLoadedConfig()), Section, Name,
                e.what());
    }
    return {};
}

// opposite operation for the GetInternalArray
void PutInternalArray(YAML::Node Yaml, const std::string& Name,
                      std::vector<std::string>& Arr, int* ErrorOut) noexcept {
    try {
        auto section = Yaml[Name];
        if (Arr.empty()) {
            section.remove(Name);
            return;
        }

        auto result = cma::tools::JoinVector(Arr, " ");
        if (result.back() == ' ') result.pop_back();
        Yaml[Name] = result;
    } catch (const std::exception& e) {
        XLOG::l("Cannot read yml file '{}' with '{}' code:'{}'",
                wtools::ConvertToUTF8(GetPathOfLoadedConfig()), Name, e.what());
    }
}

// opposite operation for the GetInternalArray
void PutInternalArray(const std::string& Section, const std::string& Name,
                      std::vector<std::string>& Arr, int* ErrorOut) noexcept {
    auto yaml = GetLoadedConfig();
    if (yaml.size() == 0) {
        if (ErrorOut) *ErrorOut = Error::kEmpty;
        return;
    }
    try {
        auto section = yaml[Section];
        PutInternalArray(section, Name, Arr, ErrorOut);
    } catch (const std::exception& e) {
        XLOG::l("Cannot read yml file '{}' with '{}.{} 'code:'{}'",
                wtools::ConvertToUTF8(GetPathOfLoadedConfig()), Section, Name,
                e.what());
    }
}

// gets string from the yaml and split it in table using space as divider
std::vector<std::string> GetInternalArray(const YAML::Node& yaml_node,
                                          const std::string& name) noexcept {
    try {
        auto val = yaml_node[name];
        if (!val.IsDefined() || val.IsNull()) {
            XLOG::t("Absent yml node '{}'", name);
            return {};
        }

        // sections: df mem
        // this is for backward compatibility
        if (val.IsScalar()) {
            auto str = val.as<std::string>();
            return StringToTable(str);
        }

        // sections: [df, mem]
        // sections:
        //   - [df, mem]
        //   - ps
        //   - check_mk logwatch
        if (val.IsSequence()) {
            std::vector<std::string> result;
            for (auto node : val) {
                if (node.IsScalar()) {
                    auto str = node.as<std::string>();
                    auto sub_result = StringToTable(str);
                    cma::tools::ConcatVector(result, sub_result);
                    continue;
                }
                if (node.IsSequence()) {
                    auto sub_result = GetArray<std::string>(node);
                    cma::tools::ConcatVector(result, sub_result);
                    continue;
                }
                XLOG::d("Invalid node structure '{}'", name);
            }

            return result;
        }

        // this is OK when nothing inside
        XLOG::d("Invalid type for node '{}' type is {}", name, val.Type());

    } catch (const std::exception& e) {
        XLOG::l("Cannot read yml file '{}' with '{}' code:{}",
                wtools::ConvertToUTF8(GetPathOfLoadedConfig()), name, e.what());
    }
    return {};
}

// #TODO refactor this trash
void SetupPluginEnvironment() {
    using namespace std;

    const std::pair<const std::string, const std::wstring> env_pairs[] = {
        // string conversion  is required because of string used in interfaces
        // of SetEnv and ConvertToUTF8
        {string(envs::kMkLocalDirName), cma::cfg::GetLocalDir()},
        {string(envs::kMkStateDirName), cma::cfg::GetStateDir()},
        {string(envs::kMkPluginsDirName), cma::cfg::GetUserPluginsDir()},
        {string(envs::kMkTempDirName), cma::cfg::GetTempDir()},
        {string(envs::kMkLogDirName), cma::cfg::GetLogDir()},
        {string(envs::kMkConfDirName), cma::cfg::GetPluginConfigDir()},
        {string(envs::kMkSpoolDirName), cma::cfg::GetSpoolDir()},
        {string(envs::kMkInstallDirName), cma::cfg::GetUserInstallDir()},
        {string(envs::kMkMsiPathName), cma::cfg::GetUpdateDir()},
        //
    };

    for (auto& d : env_pairs)
        cma::tools::win::SetEnv(d.first, wtools::ConvertToUTF8(d.second));
}

void ProcessPluginEnvironment(
    std::function<void(std::string_view name, std::string_view value)> foo)

{
    const std::pair<const std::string_view,
                    const std::function<std::wstring(void)>>
        env_pairs[] = {
            // string conversion  is required because of string used in
            // interfaces
            // of SetEnv and ConvertToUTF8
            {envs::kMkLocalDirName, &cma::cfg::GetLocalDir},
            {envs::kMkStateDirName, &cma::cfg::GetStateDir},
            {envs::kMkPluginsDirName, &cma::cfg::GetUserPluginsDir},
            {envs::kMkTempDirName, &cma::cfg::GetTempDir},
            {envs::kMkLogDirName, &cma::cfg::GetLogDir},
            {envs::kMkConfDirName, &cma::cfg::GetPluginConfigDir},
            {envs::kMkSpoolDirName, &cma::cfg::GetSpoolDir},
            {envs::kMkInstallDirName, &cma::cfg::GetUserInstallDir},
            {envs::kMkMsiPathName, &cma::cfg::GetUpdateDir},
            //
        };

    for (auto [value, func] : env_pairs) {
        foo(value, wtools::ConvertToUTF8(func()));
    }
}

// called upon every connection
// required for some plugins using state file
void SetupRemoteHostEnvironment(const std::string& IpAddress) {
    using namespace cma::tools;

    win::SetEnv(std::string(envs::kRemote), IpAddress);
    win::SetEnv(std::string(envs::kRemoteHost), IpAddress);
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
        XLOG::l("Can\'t call gethostname, error [{}]", ret);
    }
    host_name_ = host_name;

    // working directory
    cwd_ = fs::current_path().wstring();

    // msi exec
    path_to_msi_exec_.clear();
    fs::path p = cma::tools::win::GetSystem32Folder();
    p /= "msiexec.exe";
    std::error_code ec;
    if (fs::exists(p, ec)) {
        XLOG::l.i("Found msiexec {}", p.u8string());
        path_to_msi_exec_ = p.wstring();
    } else
        XLOG::l.crit(
            "Cannot find msiexec {} error [{}] '{}', automatic update is not possible",
            p.u8string(), ec.value(), ec.message());
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
            XLOG::l("Not enough rights to clear state file folder [{}]",
                    ec.value());
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

// simple function to get name of the node
// #TODO promote as official API
static std::string GetMapNodeName(const YAML::Node& Node) noexcept {
    try {
        if (!Node.IsDefined() || !Node.IsMap()) return {};
        auto s_iterator = Node.begin();

        auto s_id = s_iterator->first;
        return s_id.as<std::string>();
    } catch (const std::exception& e) {
        XLOG::l(XLOG_FUNC + " Exception on conversion '{}'", e.what());
        return {};
    }
}

constexpr bool IsSmartMerge(std::string_view name) {
    return name == groups::kWinPerf;
}

static void loadSequence(std::string_view name, YAML::Node target_value,
                         const YAML::Node source_value,
                         ConfigInfo::Combine combine) {
    if (source_value.IsScalar()) {
        XLOG::d(
            XLOG_FLINE + " overriding seq with scalar '{}' this is temporary",
            name);  // may happen when with empty sequence sections
        target_value = source_value;
        return;
    }

    if (!IsYamlSeq(source_value)) {
        XLOG::l.t(XLOG_FLINE + " skipping section '{}' as different type",
                  name);  // may happen when with empty sequence sections
        return;
    }

    // SEQ-SEQ here
    if (combine == ConfigInfo::Combine::overwrite) {
        target_value = source_value;
        return;
    }

    // special case when we are merging some sequences from
    // different files
    for (auto entry : source_value) {
        auto s_name = GetMapNodeName(entry);
        if (s_name.empty()) continue;

        if (std::none_of(std::begin(target_value), std::end(target_value),
                         [s_name](YAML::Node Node) -> bool {
                             return s_name == GetMapNodeName(Node);
                         }))
            target_value.push_back(entry);
    }
}

static void loadMap(std::string_view name, YAML::Node target_value,
                    const YAML::Node source_value,
                    ConfigInfo::Combine combine) {
    // MAP
    if (!IsYamlMap(source_value)) {
        if (!source_value.IsNull())
            XLOG::l(XLOG_FLINE + " expected map '{}', we have [{}]", name,
                    source_value.Type());
        return;
    }

    // MAP-MAP
    for (YAML::const_iterator itx = source_value.begin();
         itx != source_value.end(); ++itx) {
        auto combine_type = IsSmartMerge(name) ? ConfigInfo::Combine::merge
                                               : ConfigInfo::Combine::overwrite;
        ConfigInfo::smartMerge(target_value, source_value, combine_type);
    }
}

// #TODO simplify or better rewrite in more common form
bool ConfigInfo::smartMerge(YAML::Node target, const YAML::Node source,
                            Combine combine) {
    // we are scanning source
    for (YAML::const_iterator it = source.begin(); it != source.end(); ++it) {
        auto& source_name = it->first;
        auto& source_value = it->second;
        if (!source_name.IsDefined()) {
            XLOG::l.bp(XLOG_FLINE + "  problems here");
            continue;
        }

        auto name = source_name.as<std::string>();
        auto target_value = target[name];

        // cases to process
        //    target ----     source -----------
        // 1. MAP: valid is   MAP, all other skipped
        // 2. SEQ: valid is   SEQ and Scalar, all other skipped
        // 3. OTHER: valid is DEFINED

        if (IsYamlMap(target_value)) {
            loadMap(name, target_value, source_value, combine);
        } else if (IsYamlSeq(target_value)) {
            // SEQ
            loadSequence(name, target_value, source_value, combine);
        } else {
            // SCALAR or UNDEF
            if (source_value.IsDefined())
                target_value = source_value;  // other just override
            else {
                XLOG::l.bp(XLOG_FLINE + " bad source");
            }
        }
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
        XLOG::d.t("Loading {}", yd.path_.u8string());
        yd.loadFile();
    }

    return yamls;
}

// declares what should be merged
static void PreMergeSections(YAML::Node target, YAML::Node source) {
    // plugins:
    auto tgt_plugin = target[groups::kPlugins];
    const auto src_plugin = source[groups::kPlugins];

    MergeStringSequence(tgt_plugin, src_plugin, vars::kPluginsFolders);
    MergeMapSequence(tgt_plugin, src_plugin, vars::kPluginsExecution,
                     vars::kPluginPattern);

    // local:
    auto tgt_local = target[groups::kLocal];
    auto src_local = source[groups::kLocal];

    MergeStringSequence(tgt_local, src_local, vars::kPluginsFolders);
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
            auto bakery = YAML::LoadFile(Yd[1].path_.u8string());
            // special cases for plugins and folder
            PreMergeSections(bakery, Config);

            // normal cases
            smartMerge(Config, bakery, Combine::overwrite);
            bakery_ok = true;
        }
    } catch (...) {
        XLOG::l.bp("Bakery {} is bad", Yd[1].path_.u8string());
    }

    try {
        if (Yd[2].exists()) {
            auto user = YAML::LoadFile(Yd[2].path_.u8string());
            // special cases for plugins and folder
            PreMergeSections(user, Config);
            // normal cases
            smartMerge(Config, user, Combine::overwrite);
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
LoadCfgStatus ConfigInfo::loadAggregated(const std::wstring& config_filename,
                                         YamlCacheOp cache_op) {
    if (config_filename.empty()) {
        XLOG::l(XLOG_FLINE + " empty name");
        return LoadCfgStatus::kAllFailed;
    }
    namespace fs = std::filesystem;
    using namespace cma::tools;
    std::vector<YamlData> yamls = buildYamlData(config_filename);

    // check root
    auto& root = yamls[0];
    if (!root.exists() || root.data().empty() || root.bad()) {
        XLOG::d("Cannot find/read root cfg '{}'. ", root.path_.u8string());
        return LoadCfgStatus::kAllFailed;
    }

    // check user
    auto& user = yamls[2];

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

            if (ok_ && user_ok_ && cache_op == YamlCacheOp::update)
                StoreUserYamlToCache();
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
bool ConfigInfo::loadDirect(const std::filesystem::path& FullPath) {
    namespace fs = std::filesystem;
    int error = 0;
    auto file = FullPath;

    fs::path fpath = file;
    std::error_code ec;
    if (!fs::exists(fpath, ec)) {
        XLOG::l("File {} not found, code = [{}] '{}'", fpath.u8string(),
                ec.value(), ec.message());
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

namespace cma::cfg {
bool IsIniFileFromInstaller(const std::filesystem::path& filename) {
    namespace fs = std::filesystem;

    auto data = cma::tools::ReadFileInVector(filename);
    if (!data.has_value()) return false;

    constexpr std::string_view base = kIniFromInstallMarker;
    if (data->size() < base.length()) return false;

    auto content = data->data();
    return !memcmp(content, base.data(), base.length());
}

}  // namespace cma::cfg
