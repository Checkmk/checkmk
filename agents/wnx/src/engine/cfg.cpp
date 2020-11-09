// Configuration Parameters for whole Agent
#include "stdafx.h"

#define WIN32_LEAN_AND_MEAN
#include <direct.h>  // known path
#include <shellapi.h>
#include <shlobj.h>  // known path
#include <versionhelpers.h>
#include <windows.h>

#include <atomic>
#include <filesystem>
#include <string>

#include "cap.h"
#include "cfg.h"
#include "cfg_details.h"
#include "cma_core.h"
#include "common/cfg_info.h"
#include "common/object_repo.h"
#include "common/version.h"
#include "common/wtools.h"
#include "common/yaml.h"
#include "logger.h"
#include "read_file.h"
#include "tools/_misc.h"     // setenv
#include "tools/_process.h"  // GetSomeFolder...
#include "tools/_raii.h"     // on out
#include "tools/_tgt.h"      // we need IsDebug
#include "windows_service_api.h"

namespace cma::cfg {
using ConfigRepo = MicroRepo<cma::cfg::details::ConfigInfo>;
extern ConfigRepo cfgs;
ConfigRepo cfgs;

CfgNode CreateNode(const std::string& name) { return cfgs.createObject(name); }

CfgNode GetNode(const std::string& name) { return cfgs.getObject(name); }

bool RemoveNode(const std::string& name) { return cfgs.removeObject(name); }

}  // namespace cma::cfg

namespace cma {

namespace details {

// internal and hidden global variables
// #GLOBAL x2
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

    std::filesystem::path source_ini = cma::cfg::GetRootInstallDir();
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

void LogNodeAsBad(YAML::Node node, std::string_view comment) {
    if (false) {
        YAML::Emitter emit;
        emit << node;
        auto emitted = emit.c_str();
        XLOG::d.t("{}.  Type {}\n:\n{}\n:", comment, node.Type(), emitted);
    } else {
        XLOG::d.t("{}.  Type {}", comment, node.Type());
    }
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
        if (target_array.empty()) {
            XLOG::d.t("Target '{}' is empty, overriding with source", name);
            return true;  // nothing to process
        }

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

std::string GetMapNodeName(YAML::Node node) {
    try {
        if (!node.IsDefined()) return "undefined";
        if (node.IsSequence()) return "sequence";
        if (!node.IsMap()) return "not-map";

        for (const auto& kv : node) {
            return kv.first.as<std::string>();
        }

        return "unexpected";
    } catch (const std::exception& e) {
        return fmt::format("exception on node '{}'", e.what());
    }
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
        if (target_array.empty()) {
            XLOG::t("'{}' is empty and will be overridden", name);
            return true;  // nothing to process
        }

        XLOG::t("'{}' is not empty and will be extended", name);
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

std::filesystem::path GetDefaultLogPath() {
    std::filesystem::path dir = GetUserDir();
    if (dir.empty()) {
        auto rfid = cma::cfg::kPublicFolderId;
        return cma::tools::win::GetSomeSystemFolder(rfid);
    }

    return dir / dirs::kLog;
}

std::filesystem::path ConvertLocationToLogPath(std::string_view location) {
    if (location.empty()) return GetDefaultLogPath();

    std::error_code ec;
    if (!std::filesystem::is_directory(location, ec)) {
        XLOG::l("The log location '{}' is not valid, falling back to default",
                location);
        return GetDefaultLogPath();
    }

    return location;
}
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

YAML::Node GetLoadedConfig() noexcept { return GetCfg().getConfig(); }

std::wstring GetPathOfRootConfig() noexcept {
    return GetCfg().getRootYamlPath();
}
std::wstring GetPathOfBakeryConfig() noexcept {
    return GetCfg().getBakeryYamlPath();
}
std::wstring GetPathOfUserConfig() noexcept {
    return GetCfg().getUserYamlPath();
}

std::wstring GetPathOfLoadedConfig() noexcept {
    using namespace wtools;

    std::wstring wstr = fmt::format(
        L"'{}','{}','{}'", GetCfg().getRootYamlPath().c_str(),
        GetCfg().getBakeryDir().c_str(), GetCfg().getUserYamlPath().c_str());
    return wstr;
}

std::string GetPathOfLoadedConfigAsString() noexcept {
    return wtools::ConvertToUTF8(GetPathOfLoadedConfig());
}

std::wstring GetPathOfLoadedUserConfig() noexcept {
    return GetCfg().getUserYamlPath();
}

std::wstring GetUserPluginsDir() noexcept {
    return GetCfg().getUserPluginsDir();
}

std::wstring GetSystemPluginsDir() noexcept {
    return GetCfg().getSystemPluginsDir();
}

std::wstring GetUserDir() noexcept { return GetCfg().getUserDir(); }

std::wstring GetUpgradeProtocolDir() noexcept {
    auto dir = GetCfg().getUserDir() / dirs::kPluginConfig;
    return dir;
}

std::wstring GetBakeryDir() noexcept { return GetCfg().getBakeryDir(); }

std::filesystem::path GetBakeryFile() noexcept {
    auto bakery = GetCfg().getBakeryDir();
    bakery /= files::kDefaultMainConfig;
    bakery.replace_extension(files::kDefaultBakeryExt);
    return bakery;
}

std::wstring GetUserInstallDir() noexcept {
    auto data_dir = GetCfg().getUserDir();
    return data_dir / dirs::kUserInstallDir;
}

std::wstring GetRootDir() noexcept { return GetCfg().getRootDir(); }

std::wstring GetRootInstallDir() noexcept {
    auto root = GetCfg().getRootDir();
    return root / dirs::kFileInstallDir;
}

std::wstring GetUserModulesDir() noexcept {
    auto user = GetCfg().getUserDir();
    return user / dirs::kUserModules;
}

std::wstring GetLocalDir() noexcept { return GetCfg().getLocalDir(); }

std::wstring GetStateDir() noexcept { return GetCfg().getStateDir(); }

std::wstring GetAuStateDir() noexcept { return GetCfg().getAuStateDir(); }

std::wstring GetPluginConfigDir() noexcept {
    return GetCfg().getPluginConfigDir();
}

std::wstring GetUpdateDir() noexcept { return GetCfg().getUpdateDir(); }

std::wstring GetSpoolDir() noexcept { return GetCfg().getSpoolDir(); }

std::wstring GetTempDir() noexcept { return GetCfg().getTempDir(); }

std::string GetHostName() noexcept { return GetCfg().getHostName(); }

std::wstring GetLogDir() noexcept { return GetCfg().getLogFileDir(); }

std::wstring GetWorkingDir() noexcept { return GetCfg().getCwd(); }

std::wstring GetMsiExecPath() noexcept { return GetCfg().getMsiExecPath(); }

// #TODO gtest
bool IsLoadedConfigOk() noexcept { return GetCfg().isOk(); }

bool StoreUserYamlToCache() noexcept {
    namespace fs = std::filesystem;
    auto loaded = GetLoadedConfig();
    if (loaded.IsNull() || !loaded.IsMap()) return false;

    auto user_file = cma::cfg::GetCfg().getUserYamlPath();

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

    auto cache_path = GetCfg().getCacheDir();
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
    auto cache_path = GetCfg().getCacheDir();
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
    groups::global.setupLogEnvironment();
}

// test and reset function
void KillDefaultConfig() { GetCfg().cleanConfig(); }

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
    wstring service_path_new = L"C:\\Program Files (x86)\\checkmk\\service";

    std::error_code ec;
    auto cur_dir = current_path(ec);

    wstring exe_path = wtools::GetCurrentExePath();

    // filling
    vector<path> full;
    {
        auto remote_machine_string =
            cma::tools::win::GetEnv(cma::kRemoteMachine);

        // development deployment
        if (!remote_machine_string.empty()) {
            XLOG::l.i("THIS IS DEVELOPMENT MACHINE");
            full.emplace_back(remote_machine_string);
        }

        // tests
        if (!cur_dir.empty()) full.emplace_back(cur_dir);

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

static std::filesystem::path ExtractPathFromTheExecutable() {
    namespace fs = std::filesystem;
    std::error_code ec;
    std::wstring cmd_line = wtools::GetArgv(0);
    if (cmd_line.empty()) return {};  // something really bad

    fs::path exe = cma::tools::RemoveQuotes(cmd_line);
    exe = exe.lexically_normal();
    if (!fs::exists(exe, ec)) return {};  // something wrong probably

    fs::path path = FindServiceImagePath(cma::srv::kServiceName);
    if (path == exe) return path.parent_path().lexically_normal();

    return {};
}

std::wstring FindServiceImagePath(std::wstring_view service_name) noexcept {
    if (service_name.empty()) return {};

    XLOG::l.t("Try registry '{}'", wtools::ConvertToUTF8(service_name));

    std::wstring key_path = L"System\\CurrentControlSet\\services\\";
    key_path += service_name;
    auto service_path_new =
        wtools::GetRegistryValue(key_path, L"ImagePath", std::wstring());

    return cma::tools::RemoveQuotes(service_path_new);
}

std::filesystem::path ExtractPathFromServiceName(
    std::wstring_view service_name) noexcept {
    namespace fs = std::filesystem;
    if (service_name.empty()) return {};
    XLOG::l.t("Try service '{}'", wtools::ConvertToUTF8(service_name));

    fs::path service_path = FindServiceImagePath(service_name);
    std::error_code ec;
    if (fs::exists(service_path, ec)) {
        // location of the services
        auto p = service_path.parent_path();
        return p.lexically_normal();
    } else {
        XLOG::l("'{}' doesn't exist, error_code: [{}] '{}'",
                service_path.u8string(), ec.value(), ec.message());
    }
    return {};
}

// Typically called ONLY by ConfigInfo
// tries to find best suitable root folder
// Order: service_name, preset_root, argv[0], cwd
bool Folders::setRoot(const std::wstring& service_name,  // look in registry
                      const std::wstring& preset_root    // look in disk
) {
    namespace fs = std::filesystem;
    XLOG::d.t("Setting root. service: '{}', preset: '{}'",
              wtools::ConvertToUTF8(service_name),
              wtools::ConvertToUTF8(preset_root));

    // Path from registry if provided
    auto service_path_new = ExtractPathFromServiceName(service_name);
    if (!service_path_new.empty()) {
        // location of the services
        root_ = service_path_new.lexically_normal();
        XLOG::l.i("Set root '{}' from registry '{}'", root_.u8string(),
                  wtools::ConvertToUTF8(service_name));
        return true;
    }

    // working folder is defined
    std::error_code ec;
    fs::path work_dir = preset_root;
    if (!work_dir.empty() && fs::exists(work_dir, ec)) {
        root_ = work_dir.lexically_normal();
        XLOG::l.i("Set root '{}' direct from folder", root_.u8string());
        return true;
    }

    // argv[0]
    auto ret = ExtractPathFromTheExecutable();
    if (!ret.empty()) {
        root_ = ret.lexically_normal();
        XLOG::l.i("Set root '{}' from executable", root_.u8string());
        return true;
    }

    // Current exe path used for tests
    auto cur_dir = fs::current_path(ec);
    if (ec.value() == 0 && fs::exists(cur_dir, ec)) {
        root_ = cur_dir.lexically_normal();
        XLOG::l.i("Set root '{}' from current path", root_.u8string());
        return true;
    }

    XLOG::l(XLOG_FUNC + " Parameters are invalid");
    return false;
}

// old API
bool Folders::setRootEx(
    const std::wstring& ServiceValidName,  // look in registry
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
    if (full.empty()) {
        error_code ec;
        fs::path work_dir = RootFolder;
        if (fs::exists(work_dir, ec))
            full.emplace_back(work_dir.lexically_normal());
    }

    // Current exe path used for tests
    if (full.empty()) {
        error_code ec;
        auto cur_dir = fs::current_path(ec);
        if (ec.value() == 0 && fs::exists(cur_dir, ec))
            full.emplace_back(cur_dir.lexically_normal());
    }

    if (full.empty()) {
        XLOG::l(XLOG_FUNC + " Parameters are invalid");
        return false;
    }

    root_ = full[0].lexically_normal();

    return true;
}  // namespace cma::cfg::details

void Folders::createDataFolderStructure(const std::wstring& proposed_folder,
                                        CreateMode mode,
                                        Protection protection) {
    try {
        std::filesystem::path folder = proposed_folder;
        data_ = makeDefaultDataFolder(folder.lexically_normal().wstring(), mode,
                                      protection);
    } catch (const std::exception& e) {
        XLOG::l.bp("Cannot create Default Data Folder , exception : {}",
                   e.what());
    }
}

void Folders::cleanAll() {
    root_.clear();
    data_.clear();
    public_logs_.clear();
    private_logs_.clear();
}

CleanMode GetCleanDataFolderMode() {
    auto mode_text = GetVal(groups::kSystem, vars::kCleanupUninstall,
                            std::string(values::kCleanupSmart));
    if (cma::tools::IsEqual(mode_text, values::kCleanupNone))
        return CleanMode::none;

    if (cma::tools::IsEqual(mode_text, values::kCleanupSmart))
        return CleanMode::smart;

    if (cma::tools::IsEqual(mode_text, values::kCleanupAll))
        return CleanMode::all;

    return CleanMode::none;
}

static void RemoveCapGeneratedFile() {
    namespace fs = std::filesystem;
    auto [target_cap, ignore_it] = cap::GetInstallPair(files::kCapFile);
    XLOG::l.i("Removing generated files...");

    std::error_code ec;
    if (!fs::exists(target_cap, ec)) return;  // nothing to do

    XLOG::l.i("Removing files from the cap '{}' file...",
              target_cap.u8string());

    std::vector<std::wstring> files_on_disk;
    cap::Process(target_cap.u8string(), cap::ProcMode::remove, files_on_disk);
    XLOG::l.i("Removed [{}] files from the cap file.", files_on_disk.size());
}

static void RemoveOwnGeneratedFile() {
    namespace fs = std::filesystem;

    auto [target_yml_example, ignore_it_again] = cap::GetExampleYmlNames();
    std::error_code ec;

    if (!fs::exists(target_yml_example, ec)) return;  // nothing to do

    XLOG::l.i("Removing yml files.");
    fs::path user_yml = GetUserDir();
    user_yml /= files::kUserYmlFile;
    if (cma::tools::AreFilesSame(target_yml_example, user_yml)) {
        XLOG::l.i("Removing user yml files.");
        fs::remove(user_yml, ec);
    }
    XLOG::l.i("Removing example yml files.");
    fs::remove(target_yml_example, ec);
}

static void RemoveDirs(std::filesystem::path path) {
    namespace fs = std::filesystem;
    std::error_code ec;
    auto del_dirs = details::RemovableDirTable();
    for (auto& d : del_dirs) fs::remove_all(path / d, ec);

    auto std_dirs = details::AllDirTable();
    for (auto& d : std_dirs) fs::remove(path / d, ec);
}

// This function should be tested only manually
bool CleanDataFolder(CleanMode mode) {
    namespace fs = std::filesystem;

    std::error_code ec;
    fs::path path = cma::cfg::GetUserDir();
    if (!fs::exists(path / dirs::kBakery, ec) ||
        !fs::exists(path / dirs::kUserPlugins, ec)) {
        XLOG::l.w(
            "Data Folder '{}' looks as invalid/damaged, processing is stopped",
            path.u8string());
        return false;
    }

    switch (mode) {
        case CleanMode::none:
            XLOG::details::LogWindowsEventAlways(XLOG::EventLevel::information,
                                                 99, "No cleaning");
            break;

        case CleanMode::smart: {
            XLOG::details::LogWindowsEventInfo(
                99, "Removing SMART from the Program Data Folder");
            RemoveCapGeneratedFile();
            RemoveOwnGeneratedFile();
            RemoveDirs(path);
        } break;

        case CleanMode::all:
            XLOG::details::LogWindowsEventInfo(
                99, "Removing All from the Program Data Folder");
            fs::remove_all(path, ec);
            break;
    }

    return true;
}

std::vector<std::wstring_view> AllDirTable() {
    return {//
            // may not contain user content
            dirs::kBakery,       // config file(s)
            dirs::kUserBin,      // placeholder for ohm
            dirs::kBackup,       // backed up files
            dirs::kTemp,         //
            dirs::kInstall,      // for installing data
            dirs::kUpdate,       // for incoming MSI
            dirs::kUserModules,  // for all modules

            // may contain user content
            dirs::kState,          // state folder
            dirs::kSpool,          // keine Ahnung
            dirs::kUserPlugins,    // user plugins
            dirs::kLocal,          // user local plugins
            dirs::kMrpe,           // for incoming mrpe tests
            dirs::kLog,            // logs are located here
            dirs::kPluginConfig};  //
}

std::vector<std::wstring_view> RemovableDirTable() {
    return {
        dirs::kBakery,       // config file(s)
        dirs::kUserBin,      // placeholder for ohm
        dirs::kBackup,       // backed up files
        dirs::kTemp,         //
        dirs::kInstall,      // for installing data
        dirs::kUpdate,       // for incoming MSI
        dirs::kUserModules,  // for all modules
    };                       //
}

//
// Not API, but quite important
// Create project defined Directory Structure in the Data Folder
// gtest[+] indirectly
// Returns error code
int CreateTree(const std::filesystem::path& base_path) noexcept {
    namespace fs = std::filesystem;

    // directories to be created
    // should be more clear defined in cfg_info
    auto dir_list = AllDirTable();

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
//
std::filesystem::path Folders::makeDefaultDataFolder(
    std::wstring_view AgentDataFolder, CreateMode mode, Protection protection) {
    using namespace cma::tools;
    namespace fs = std::filesystem;
    auto draw_folder = [mode](std::wstring_view DataFolder) -> auto {
        fs::path app_data = DataFolder;
        if (mode == CreateMode::with_path) {
            app_data /= cma::cfg::kAppDataCompanyName;
            app_data /= cma::cfg::kAppDataAppName;
        }
        return app_data;
    };

    if (AgentDataFolder.empty()) {
        /// automatic data path, used ProgramData folder
        auto app_data_folder = win::GetSomeSystemFolder(FOLDERID_ProgramData);

        auto app_data = draw_folder(app_data_folder);
        auto ret = CreateTree(app_data);
        if (protection == Protection::yes) {
            cma::security::ProtectAll(fs::path(app_data_folder) /
                                      cma::cfg::kAppDataCompanyName);
        }

        if (ret == 0) return app_data;
        XLOG::l.bp("Failed to access ProgramData Folder {}", ret);

        if constexpr (false) {
            // Public fallback
            app_data_folder = win::GetSomeSystemFolder(FOLDERID_Public);
            app_data = draw_folder(app_data_folder);
            ret = CreateTree(app_data);
            if (ret == 0) return app_data;
            XLOG::l.crit("Failed to access Public Folder {}", ret);
        }
        return {};
    }

    // path with a custom folder
    auto app_data = draw_folder(AgentDataFolder);
    auto ret = CreateTree(app_data);
    if (ret == 0) return app_data;
    XLOG::l.bp("Failed to access Public Folder {}", ret);
    return {};
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
            auto loaded = GetCfg().loadDirect(name);
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

    auto code = GetCfg().loadAggregated(usable_name, cache_op);

    if (code >= 0) return true;

    XLOG::l.e("Failed usable_name: '{}' at root: '{}' code is '{}'",
              wtools::ConvertToUTF8(usable_name),
              GetCfg().getRootDir().u8string(), code);

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
    groups::global.setupLogEnvironment();  // at the moment only global
}

bool ReloadConfigAutomatically() { return false; }

// Find any file, usually executable on one of the our paths
// for execution
const std::wstring FindExeFileOnPath(const std::wstring& File) {
    using namespace std::filesystem;
    auto paths = GetCfg().getExePaths();
    for (const auto& dir : paths) {
        auto file_path = dir / File;
        if (exists(file_path)) {
            return file_path.lexically_normal().wstring();
        }
    }
    return {};
}

std::vector<std::filesystem::path> GetExePaths() {
    return GetCfg().getExePaths();
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
std::vector<std::string> GetInternalArray(std::string_view Section,
                                          std::string_view Name,
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
void PutInternalArray(YAML::Node Yaml, std::string_view name,
                      std::vector<std::string>& Arr, int* ErrorOut) noexcept {
    try {
        auto section = Yaml[name];
        if (Arr.empty()) {
            section.remove(name);
            return;
        }

        auto result = cma::tools::JoinVector(Arr, " ");
        if (result.back() == ' ') result.pop_back();
        Yaml[name] = result;
    } catch (const std::exception& e) {
        XLOG::l("Cannot read yml file '{}' with '{}' code:'{}'",
                wtools::ConvertToUTF8(GetPathOfLoadedConfig()), name, e.what());
    }
}

// opposite operation for the GetInternalArray
void PutInternalArray(std::string_view section_name, std::string_view key,
                      std::vector<std::string>& Arr, int* ErrorOut) noexcept {
    auto yaml = GetLoadedConfig();
    if (yaml.size() == 0) {
        if (ErrorOut) *ErrorOut = Error::kEmpty;
        return;
    }
    try {
        auto section = yaml[section_name];
        PutInternalArray(section, key, Arr, ErrorOut);
    } catch (const std::exception& e) {
        XLOG::l("Cannot read yml file '{}' with '{}.{} 'code:'{}'",
                wtools::ConvertToUTF8(GetPathOfLoadedConfig()), section_name,
                key, e.what());
    }
}

// gets string from the yaml and split it in table using space as divider
std::vector<std::string> GetInternalArray(const YAML::Node& yaml_node,
                                          std::string_view name) noexcept {
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
        // string conversion  is required because of string used in
        // interfaces
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
            {envs::kMkModulesDirName, &cma::cfg::GetUserModulesDir},
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

std::tuple<bool, std::filesystem::path> IsInstallProtocolExists(
    const std::filesystem::path& root) {
    XLOG::l.i("Current root for install protocol '{}'", root.u8string());
    auto install_file = ConstructInstallFileName(root);
    std::error_code ec;
    if (install_file.empty()) return {false, {}};

    return {std::filesystem::exists(install_file, ec), install_file};
}

// #TODO deprecated
[[deprecated]] void UpdateInstallProtocolFile(
    bool exists_install_protocol, const std::filesystem::path& install_file) {
    if (install_file.empty()) {
        XLOG::l("Install file cannot be generated, because it is not correct");
        return;
    }

    if (exists_install_protocol) {
        XLOG::l.i("Install protocol exists, no generation.");
        return;
    }

    XLOG::l.i("Creating '{}' to indicate that installation is finished",
              install_file.u8string());
    std::ofstream ofs(install_file, std::ios::binary);

    if (ofs) {
        ofs << "Installed:\n";
        ofs << "  time: '" << cma::cfg::ConstructTimeString() << "'\n";
    }
}

void ConfigInfo::fillExePaths(std::filesystem::path root) {
    constexpr const wchar_t* dir_tails[] = {
        dirs::kAgentPlugins, dirs::kAgentProviders, dirs::kAgentUtils};

    for (auto& d : dir_tails) exe_command_paths_.emplace_back(root / d);
    exe_command_paths_.emplace_back(root);
}

void ConfigInfo::fillConfigDirs() {
    config_dirs_.clear();
    config_dirs_.emplace_back(folders_.getRoot());
    config_dirs_.emplace_back(folders_.getBakery());
    config_dirs_.emplace_back(folders_.getUser());
}

// not thread safe, but called only on program start
void ConfigInfo::initFolders(
    const std::wstring& ServiceValidName,  // look in registry
    const std::wstring& RootFolder,        // look in disk
    const std::wstring& AgentDataFolder)   // look in dis
{
    cleanFolders();
    folders_.createDataFolderStructure(
        AgentDataFolder, Folders::CreateMode::with_path,
        ServiceValidName.empty() ? Folders::Protection::no
                                 : Folders::Protection::yes);

    // This is not very good idea, but we want
    // to start logging as early as possible
    XLOG::setup::ChangeDebugLogLevel(LogLevel::kLogDebug);
    groups::global.setLogFolder(folders_.getData() / dirs::kLog);
    groups::global.setupLogEnvironment();

    initEnvironment();

    folders_.setRoot(ServiceValidName, RootFolder);
    auto root = folders_.getRoot();

    if (!ServiceValidName.empty()) {
        auto exe_path = FindServiceImagePath(ServiceValidName);
        wtools::ProtectFileFromUserWrite(exe_path);
        wtools::ProtectPathFromUserAccess(root);
    }

    if (folders_.getData().empty())
        XLOG::l.crit("Data folder is empty.This is bad.");
    else {
        // code is disabled as deprecated
        // auto [exists_install_protocol, install_file] =
        //    IsInstallProtocolExists(root);
        // UpdateInstallProtocolFile(exists_install_protocol, install_file);
    }

    // exe
    fillExePaths(root);

    // all paths where we are looking for config files
    fillConfigDirs();
}

// normally used only during start
void ConfigInfo::cleanFolders() {
    std::lock_guard lk(lock_);
    exe_command_paths_.resize(0);  // root/utils, root/plugins etc
    config_dirs_.resize(0);        // root und data

    folders_.cleanAll();
}

// normally used to reload configs and/or testing
void ConfigInfo::cleanConfig() {
    std::lock_guard lk(lock_);

    yaml_.reset();
    root_yaml_path_ = L"";
    user_yaml_path_ = L"";
    bakery_yaml_path_ = L"";
    aggregated_ = false;
    generated_ = false;
    ok_ = false;
}

bool ConfigInfo::pushFolders(const std::filesystem::path& root,
                             const std::filesystem::path& data) {
    std::lock_guard lk(lock_);
    if (folders_stack_.size() >= kMaxFoldersStackSize) {
        XLOG::l("Folders Stack is overflown, max size is [{}]",
                kMaxFoldersStackSize);
        return false;
    }
    folders_stack_.push(folders_);
    folders_.setRoot({}, root.wstring());
    folders_.createDataFolderStructure(data, Folders::CreateMode::direct,
                                       Folders::Protection::no);

    return true;
}

bool ConfigInfo::popFolders() {
    std::lock_guard lk(lock_);
    if (folders_stack_.empty()) {
        XLOG::l("Imbalanced pop call for folders stack");
        return false;
    }

    folders_ = folders_stack_.top();
    folders_stack_.pop();
    return true;
}

std::wstring FindMsiExec() noexcept {
    std::filesystem::path p = cma::tools::win::GetSystem32Folder();
    p /= "msiexec.exe";

    std::error_code ec;
    if (std::filesystem::exists(p, ec)) {
        XLOG::t.i("Found msiexec {}", p.u8string());
        return p.wstring();
    }

    XLOG::l.crit(
        "Cannot find msiexec {} error [{}] '{}', automatic update is not possible",
        p.u8string(), ec.value(), ec.message());
    return {};
}

std::string FindHostName() noexcept {
    // host name
    char host_name[256] = "";
    auto ret = ::gethostname(host_name, 256);
    if (ret != 0) {
        XLOG::l("Can't call gethostname, error [{}]", ret);
        return {};
    }
    return host_name;
}

void ConfigInfo::initEnvironment() {
    host_name_ = FindHostName();
    cwd_ = std::filesystem::current_path().wstring();
    path_to_msi_exec_ = FindMsiExec();
}

// probably global in the future
static void PrepareEnvironment() {
    using namespace std;
    using namespace cma::cfg;

    namespace fs = std::filesystem;

    auto fs_state_path = GetCfg().getStateDir();
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

constexpr Combine GetCombineMode(std::string_view name) {
    if (name == groups::kWinPerf) return Combine::merge;
    if (name == groups::kLogWatchEvent) return Combine::merge_value;
    return Combine::overwrite;
}

void CombineSequence(std::string_view name, YAML::Node target_value,
                     const YAML::Node source_value, Combine combine) {
    if (source_value.IsScalar()) {
        XLOG::d.t("Overriding seq named '{}' with scalar, this is allowed",
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
    switch (combine) {
        case Combine::overwrite:
            target_value = source_value;
            return;

        // special case when we are merging some sequences from
        // different files
        case Combine::merge:
            for (auto entry : source_value) {
                auto s_name = GetMapNodeName(entry);
                if (s_name.empty()) continue;

                if (std::none_of(std::begin(target_value),
                                 std::end(target_value),
                                 [s_name](YAML::Node Node) -> bool {
                                     return s_name == GetMapNodeName(Node);
                                 }))
                    target_value.push_back(entry);
            }
            break;

        // by logfiles
        case Combine::merge_value: {
            YAML::Node new_seq = YAML::Clone(source_value);
            for (auto entry : target_value) {
                auto s_name = GetMapNodeName(entry);
                if (s_name.empty()) continue;

                if (std::none_of(std::begin(source_value),
                                 std::end(source_value),
                                 [s_name](YAML::Node node) -> bool {
                                     return s_name == GetMapNodeName(node);
                                 }))
                    new_seq.push_back(entry);
            }
            target_value = new_seq;
            break;
        }
    }
}

static void loadMap(std::string_view name, YAML::Node target_value,
                    const YAML::Node source_value, Combine combine) {
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
        auto combine_type = GetCombineMode(name);
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
            CombineSequence(name, target_value, source_value, combine);
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
    {
        auto tgt_plugin = target[groups::kPlugins];
        const auto src_plugin = source[groups::kPlugins];

        MergeStringSequence(tgt_plugin, src_plugin, vars::kPluginsFolders);
        MergeMapSequence(tgt_plugin, src_plugin, vars::kPluginsExecution,
                         vars::kPluginPattern);
    }

    // local:
    {
        auto tgt_local = target[groups::kLocal];
        const auto src_local = source[groups::kLocal];

        MergeStringSequence(tgt_local, src_local, vars::kPluginsFolders);
        MergeMapSequence(tgt_local, src_local, vars::kPluginsExecution,
                         vars::kPluginPattern);
    }
}

static bool Is64BitWindows() {
#if defined(_WIN64)
    return true;  // 64-bit programs run only on Win64
#elif defined(_WIN32)
    // 32-bit programs run on both 32-bit and 64-bit Windows
    // so must sniff
    BOOL f64 = FALSE;
    return IsWow64Process(GetCurrentProcess(), &f64) && f64;
#else
    return false;  // Win64 does not support Win16
#endif
}

// Scott Meyer method to have a safe singleton
// static variables with block scope created only once
class InfoStrings {
public:
    static InfoStrings& get() {
        static InfoStrings instance;
        return instance;
    }

    const std::string agentString() const noexcept { return agent_string_; }
    const std::string osString() const noexcept { return os_string_; }

private:
    InfoStrings() {
        agent_string_ = makeAgentInfoString();
        os_string_ = makeOsInfoString();
    }

    // generates short info about agent(version, build, environment)
    // required to correctly identify client in log
    static std::string makeAgentInfoString() noexcept {
        constexpr std::string_view build_bits =
            tgt::Is64bit() ? "64bit" : "32bit";
        constexpr std::string_view debug = tgt::IsDebug() ? "debug" : "release";
        constexpr std::string_view version = CHECK_MK_VERSION;
        constexpr std::string_view build_date = __DATE__;
        constexpr std::string_view build_time = __TIME__;
        return fmt::format("[{},{},{},{},{}]", version, build_bits, debug,
                           build_date, build_time);
    }

    // generates short info about OS
    // required to correctly identify client in log
    static std::string_view GetWindowsId() noexcept {
        if (IsWindows10OrGreater()) return "10";
        if (IsWindows8Point1OrGreater()) return "8.1";
        if (IsWindows8OrGreater()) return "8";
        if (IsWindows7SP1OrGreater()) return "7SP";
        if (IsWindows7OrGreater()) return "7";
        if (IsWindowsVistaSP2OrGreater()) return "VistaSp2";
        if (IsWindowsVistaSP1OrGreater()) return "VistaSp1";
        if (IsWindowsVistaOrGreater()) return "VistaSp";
        return "XP";
    }

    static std::string makeOsInfoString() noexcept {
        const std::string_view server =
            IsWindowsServer() ? "server" : "desktop";
        const std::string_view bits_count = Is64BitWindows() ? "64" : "32";

        const std::string_view os_id = GetWindowsId();

        return fmt::format("Win{}-{} {}", os_id, bits_count, server);
    }

    ~InfoStrings() = default;
    InfoStrings(const InfoStrings&) = delete;
    InfoStrings& operator=(const InfoStrings&) = delete;
    std::string agent_string_;
    std::string os_string_;
};

// node is typical config from the root
// we will load all others configs and try to merge
// success ALWAYS
void ConfigInfo::loadYamlDataWithMerge(YAML::Node node,
                                       const std::vector<YamlData>& Yd) {
    namespace fs = std::filesystem;
    bool bakery_ok = false;
    bool user_ok = false;
    try {
        if (Yd[1].exists() && !Yd[1].bad()) {
            auto bakery = YAML::LoadFile(Yd[1].path_.u8string());
            // special cases for plugins and folder
            PreMergeSections(bakery, node);

            // normal cases
            smartMerge(node, bakery, Combine::overwrite);
            bakery_ok = true;
        }
    } catch (...) {
        XLOG::l.bp("Bakery {} is bad", Yd[1].path_.u8string());
    }

    try {
        if (Yd[2].exists() && !Yd[2].bad()) {
            auto user = YAML::LoadFile(Yd[2].path_.u8string());
            // special cases for plugins and folder
            PreMergeSections(user, node);
            // normal cases
            smartMerge(node, user, Combine::overwrite);
            user_ok = true;
        }
    } catch (...) {
        XLOG::l.bp("User {} is bad", Yd[2].path_.u8string());
    }

    std::lock_guard lk(lock_);
    root_yaml_time_ = Yd[0].timestamp();
    bakery_yaml_time_ = bakery_ok ? Yd[1].timestamp() : bakery_yaml_time_.min();
    bakery_ok_ = bakery_ok;
    user_yaml_time_ = user_ok ? Yd[2].timestamp() : user_yaml_time_.min();
    user_ok_ = user_ok;

    // RemoveInvalidNodes(node); <-- disabled at the moment

    yaml_ = node;

    XLOG::d.i(
        "Loaded Config Files by Agent {} @ '{}'\n"
        "    root:   '{}' size={} {}\n"
        "    bakery: '{}' size={} {}\n"
        "    user:   '{}' size={} {}",
        InfoStrings::get().agentString(), InfoStrings::get().osString(),
        //
        Yd[0].path_.u8string(), Yd[0].data().size(),
        Yd[0].bad() ? "[FAIL]" : "[OK]",
        //
        Yd[1].path_.u8string(), Yd[1].data().size(),
        Yd[1].bad() ? "[FAIL]" : "[OK]",
        //
        Yd[2].path_.u8string(), Yd[2].data().size(),
        Yd[2].bad() ? "[FAIL]" : "[OK]");

    // setting up paths  to the other files
    root_yaml_path_ = Yd[0].path_;
    bakery_yaml_path_ = Yd[1].path_;
    user_yaml_path_ = Yd[2].path_;

    aggregated_ = true;
    uniq_id_++;
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
bool ConfigInfo::loadDirect(const std::filesystem::path& file) {
    namespace fs = std::filesystem;
    int error = 0;

    const fs::path& fpath = file;
    std::error_code ec;
    if (!fs::exists(fpath, ec)) {
        XLOG::l("File {} not found, code = [{}] '{}'", fpath.u8string(),
                ec.value(), ec.message());
        return false;
    }
    auto ftime = fs::last_write_time(fpath, ec);

    // we will load when error happens, or time changed or name changed
    bool load_required =
        ec.value() != 0 || ftime != root_yaml_time_ || file != root_yaml_path_;

    if (!load_required) {
        return ok_;
    }

    auto new_yaml = LoadAndCheckYamlFile(file, FallbackPolicy::kNone, &error);
    if (0 == new_yaml.size()) return false;

    std::lock_guard lk(lock_);
    root_yaml_time_ = ftime;
    yaml_ = new_yaml;
    root_yaml_path_ = file;
    XLOG::d.t("Loaded Config from  {}", file.u8string());

    // setting up paths  to the other files
    user_yaml_path_ = file;
    root_yaml_time_ = std::filesystem::last_write_time(file);
    user_yaml_path_.clear();
    user_yaml_time_ = decltype(user_yaml_time_)::min();
    bakery_yaml_path_.clear();
    aggregated_ = false;
    ok_ = true;
    uniq_id_++;
    return true;
}

}  // namespace cma::cfg::details

namespace cma::cfg {
bool IsIniFileFromInstaller(const std::filesystem::path& filename) {
    auto data = cma::tools::ReadFileInVector(filename);
    if (!data.has_value()) return false;

    constexpr std::string_view base = kIniFromInstallMarker;
    if (data->size() < base.length()) return false;

    auto content = data->data();
    return 0 == memcmp(content, base.data(), base.length());
}

// generates standard agent time string
std::string ConstructTimeString() {
    using namespace std::chrono;
    constexpr uint32_t k1000 = 1000;
    auto cur_time = system_clock::now();
    auto in_time_t = system_clock::to_time_t(cur_time);
    std::stringstream sss;
    auto ms = duration_cast<milliseconds>(cur_time.time_since_epoch()) % k1000;
    auto loc_time = std::localtime(&in_time_t);
    auto p_time = std::put_time(loc_time, "%Y-%m-%d %T");
    sss << p_time << "." << std::setfill('0') << std::setw(3) << ms.count()
        << std::ends;

    return sss.str();
}

// makes the name of install.protocol file
// may return empty path
std::filesystem::path ConstructInstallFileName(
    const std::filesystem::path& dir) {
    namespace fs = std::filesystem;
    if (dir.empty()) {
        XLOG::d("Attempt to create install protocol in current folder");
        return {};
    }
    fs::path protocol_file = dir;
    protocol_file /= cma::cfg::files::kInstallProtocol;
    return protocol_file;
}

bool IsNodeNameValid(std::string_view name) {
    if (name.empty()) return true;
    return name[0] != '_';
}

int RemoveInvalidNodes(YAML::Node node) {
    //
    if (!node.IsDefined() || !node.IsMap()) return 0;

    std::vector<std::string> to_remove;
    int counter = 0;

    for (YAML::const_iterator it = node.begin(); it != node.end(); ++it) {
        std::string key = it->first.as<std::string>();  // <- key
        if (!IsNodeNameValid(key)) {
            XLOG::t("Removing node '{}'", key);
            to_remove.emplace_back(key);
            continue;
        }

        int sub_count = RemoveInvalidNodes(node[key]);
        counter += sub_count;
    }
    for (auto& r : to_remove) {
        node.remove(r);
        ++counter;
    }
    return counter;
}

bool ReplaceInString(std::string& in_out, std::string_view marker,
                     std::string_view value) {
    auto pos = in_out.find(marker);
    if (pos != std::string::npos) {
        in_out.replace(pos, marker.length(), value);
        return true;
    }
    return false;
}

std::string ReplacePredefinedMarkers(std::string_view work_path) {
    const std::pair<const std::string_view, const std::wstring> pairs[] = {
        // core:
        {vars::kPluginCoreFolder, GetSystemPluginsDir()},
        {vars::kPluginBuiltinFolder, GetSystemPluginsDir()},
        // pd:
        {vars::kPluginUserFolder, GetUserPluginsDir()},
        {vars::kLocalUserFolder, GetLocalDir()},
        {vars::kProgramDataFolder, GetUserDir()}

    };

    std::string f(work_path);
    for (const auto& [marker, path] : pairs) {
        if (ReplaceInString(f, marker, wtools::ConvertToUTF8(path))) return f;
    }

    return f;
}

// converts "any/relative/path" into
// "marker\\any\\relative\\path"
// return false if yaml is not suitable for patching
// normally used only by cvt
bool PatchRelativePath(YAML::Node Yaml, std::string_view group_name,
                       std::string_view key_name, std::string_view subkey_name,
                       std::string_view marker) {
    namespace fs = std::filesystem;
    if (group_name.empty() || key_name.empty() || subkey_name.empty() ||
        marker.empty()) {
        XLOG::l(XLOG_FUNC + " Problems with parameter '{}' '{}' '{}' '{}'",
                group_name, key_name, subkey_name, marker);
        return false;
    }
    auto group = Yaml[group_name];
    if (!group.IsDefined()) return false;
    if (!group.IsMap()) return false;

    auto key = group[key_name];
    if (!key.IsDefined() || !key.IsSequence()) return false;

    auto sz = key.size();
    const std::string name(subkey_name);
    for (size_t k = 0; k < sz; ++k) {
        auto node = key[k][name];
        if (!node.IsDefined() || !node.IsScalar()) continue;

        auto entry = node.as<std::string>();
        if (entry.empty()) continue;

        fs::path path = entry;
        auto p = path.lexically_normal();
        if (p.u8string()[0] == fs::path::preferred_separator) continue;
        if (p.u8string()[0] == marker[0]) continue;
        if (p.is_relative()) {
            key[k][name] = std::string(marker) + "\\" + entry;
        }
    }
    return true;
}

constexpr std::string_view kWmicUninstallCommand =
    "wmic product where name=\"{}\" call uninstall /nointeractive";

std::string CreateWmicCommand(std::string_view product_name) {
    return fmt::format(kWmicUninstallCommand, product_name);
}

std::filesystem::path CreateWmicUninstallFile(
    const std::filesystem::path& temp_dir, std::string_view product_name) {
    auto file = temp_dir / "exec_uninstall.cmd";
    try {
        std::ofstream ofs(file.u8string());
        ofs << CreateWmicCommand(product_name);
        ofs.close();
        if (std::filesystem::exists(file)) return file;
        XLOG::l("Attempt to create '{}' file is failed", file.u8string());
        return {};
    } catch (const std::exception& e) {
        XLOG::l("Attempt to create '{}' file is failed with exception {}",
                file.u8string(), e.what());
    }

    return {};
}

bool UninstallProduct(std::string_view name) {
    if constexpr (tgt::IsWindows()) {
        std::filesystem::path temp = cma::cfg::GetTempDir();
        auto fname = CreateWmicUninstallFile(temp, name);
        if (fname.empty()) return false;
        auto pid = cma::tools::RunStdCommand(fname.wstring(), true);
        if (pid == 0) {
            XLOG::l("Failed to start '{}'", fname.u8string());
        }
        return true;
    }

    return false;
}

details::ConfigInfo& GetCfg() { return details::G_ConfigInfo; }
std::atomic<uint64_t> details::ConfigInfo::uniq_id_ = 1;

}  // namespace cma::cfg
