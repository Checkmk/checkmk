// Configuration Parameters for whole Agent
#include "stdafx.h"

#include "cfg.h"

#include <WinSock2.h>

#include <direct.h>  // known path
#include <shellapi.h>
#include <shlobj.h>  // known path
#include <versionhelpers.h>

#include <atomic>
#include <filesystem>
#include <string>

#include "cap.h"
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
#include "upgrade.h"
#include "windows_service_api.h"
namespace fs = std::filesystem;
using namespace std::string_literals;
using namespace std::string_view_literals;

namespace cma::cfg {
using ConfigRepo = MicroRepo<cma::cfg::details::ConfigInfo>;
// #TODO (sk): rework this
ConfigRepo g_configs;  // NOLINT

CfgNode CreateNode(const std::string &name) {
    return g_configs.createObject(name);
}

CfgNode GetNode(const std::string &name) { return g_configs.getObject(name); }

bool RemoveNode(const std::string &name) {
    return g_configs.removeObject(name);
}

}  // namespace cma::cfg

namespace cma {

namespace details {
Modus g_modus{Modus::app};
void SetModus(Modus m) {
    XLOG::d.i("change modus to {}", static_cast<uint32_t>(m));
    g_modus = m;
}
}  // namespace details

Modus GetModus() { return details::g_modus; }

};  // namespace cma

namespace cma::cfg {

InstallationType DetermineInstallationType() {
    fs::path source_install_yml{cma::cfg::GetRootInstallDir()};
    source_install_yml /= files::kInstallYmlFileW;

    try {
        auto file = YAML::LoadFile(source_install_yml.u8string());

        if (file[groups::kGlobal][vars::kInstall].as<std::string>() == "no"s) {
            return InstallationType::packaged;
        }

    } catch (const std::exception &e) {
        XLOG::l.i(
            "Exception '{}' when checking installation type '{}' - assumed wato installation",
            e.what(), source_install_yml.u8string());
    }

    return InstallationType::wato;
}

std::wstring WinPerf::buildCmdLine() const {
    std::unique_lock lk(lock_);
    auto counters = counters_;
    lk.unlock();

    std::wstring cmd_line;
    for (const auto &counter : counters) {
        if (counter.id().empty() || counter.name().empty()) {
            continue;
        }

        // check for allowed
        std::string name_to_check{vars::kWinPerfPrefixDefault};
        name_to_check += '_';
        name_to_check += counter.name();
        if (groups::global.isSectionDisabled(name_to_check)) {
            continue;
        }

        // adding to command line
        auto name = wtools::ConvertToUTF16(counter.id());
        std::replace(name.begin(), name.end(), L' ', L'*');
        cmd_line += name;
        cmd_line += L":";
        cmd_line += wtools::ConvertToUTF16(counter.name());
        cmd_line += L" ";
    }
    if (!cmd_line.empty() && cmd_line.back() == L' ') {
        cmd_line.pop_back();
    }
    return cmd_line;
}

// if not empty returns contents of the array
template <typename T>
static std::vector<T> OverrideTargetIfEmpty(YAML::Node target,
                                            const YAML::Node &source) {
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

void LogNodeAsBad(const YAML::Node &node, std::string_view comment) {
    XLOG::t("{}:  Type {}", comment, node.Type());
}

// merge source's content into the target if the content is absent in the target
// returns false only when data-structures are invalid
bool MergeStringSequence(YAML::Node target_group, YAML::Node source_group,
                         const std::string &name) {
    try {
        // check for source. if empty, leave
        auto source = source_group[name];
        if (!source.IsDefined() || !source.IsSequence()) {
            return true;
        }

        // check for target. if empty, override with non empty source, leave
        auto target = target_group[name];
        auto target_array = OverrideTargetIfEmpty<std::string>(target, source);
        if (target_array.empty()) {
            XLOG::d.t("Target '{}' is empty, overriding with source", name);
            return true;
        }

        // merging
        auto source_array = GetArray<std::string>(source);

        for (const auto &source_entry : source_array) {
            if (std::ranges::find(target_array, source_entry) ==
                target_array.end()) {
                target.push_back(source_entry);
            }
        }

    } catch (const std::exception &e) {
        XLOG::d("Failed to merge yaml '{}' seq '{}'", name, e.what());
        return false;
    }
    return true;
}

std::string GetMapNodeName(const YAML::Node &node) {
    try {
        if (!node.IsDefined()) {
            return "undefined";
        }
        if (node.IsSequence()) {
            return "sequence";
        }
        if (!node.IsMap()) {
            return "not-map";
        }

        for (const auto &kv : node) {
            return kv.first.as<std::string>();
        }

        return "unexpected";
    } catch (const std::exception &e) {
        return fmt::format("exception on node '{}'", e.what());
    }
}

// merge source's content into the target if the content is absent in the target
// returns false only when data-structures are invalid
bool MergeMapSequence(YAML::Node target_group, YAML::Node source_group,
                      const std::string &name, const std::string &key) {
    try {
        // check for source, if empty -> leave
        auto source = source_group[name];
        if (!source.IsDefined() || !source.IsSequence()) {
            return true;
        }

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
        for (const auto &source_entry : source_array) {
            auto source_key = GetVal(source_entry, key, std::string());

            if (source_key.empty()) {
                continue;
            }

            if (std::ranges::none_of(target_array, [&](const YAML::Node &Node) {
                    return source_key == GetVal(Node, key, std::string());
                })) {
                target.push_back(source_entry);
            }
        }
    } catch (const std::exception &e) {
        XLOG::d.t("Failed to merge yaml '{}.{}' map '{}'", name, key, e.what());
        return false;
    }

    return true;
}

// we have chaos with globals
namespace details {
ConfigInfo g_config_info;  // NOLINT
// store boot fixed data
uint64_t g_registered_performance_freq{
    static_cast<uint64_t>(wtools::QueryPerformanceFreq())};

fs::path GetDefaultLogPath() {
    fs::path dir = GetUserDir();
    if (dir.empty()) {
        return tools::win::GetSomeSystemFolder(cfg::kPublicFolderId);
    }

    return dir / dirs::kLog;
}

fs::path ConvertLocationToLogPath(std::string_view location) {
    if (location.empty()) {
        return GetDefaultLogPath();
    }

    std::error_code ec;
    if (!fs::is_directory(location, ec)) {
        XLOG::l("The log location '{}' is not valid, falling back to default",
                location);
        return GetDefaultLogPath();
    }

    return location;
}
}  // namespace details

namespace groups {
Global global;       // NOLINT
WinPerf winperf;     // NOLINT
Plugins plugins;     // NOLINT
Plugins localGroup;  // NOLINT

};  // namespace groups

// API

uint64_t GetPerformanceFrequency() noexcept {
    return details::g_registered_performance_freq;
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

std::wstring GetPathOfLoadedConfig() {
    return fmt::format(L"'{}','{}','{}'", GetCfg().getRootYamlPath().c_str(),
                       GetCfg().getBakeryDir().c_str(),
                       GetCfg().getUserYamlPath().c_str());
}

std::string GetPathOfLoadedConfigAsString() {
    return wtools::ToUtf8(GetPathOfLoadedConfig());
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
std::wstring GetUserBinDir() noexcept { return GetCfg().getUserBinDir(); }

std::wstring GetUpgradeProtocolDir() {
    auto dir = GetCfg().getUserDir() / dirs::kPluginConfig;
    return dir;
}

std::wstring GetBakeryDir() noexcept { return GetCfg().getBakeryDir(); }

fs::path GetBakeryFile() {
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

std::wstring GetRootUtilsDir() noexcept {
    auto root = GetCfg().getRootDir();
    return root / dirs::kAgentUtils;
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

std::wstring GetLogDir() noexcept { return GetCfg().getLogDir(); }

std::wstring GetWorkingDir() noexcept { return GetCfg().getCwd(); }

std::wstring GetMsiExecPath() noexcept { return GetCfg().getMsiExecPath(); }

bool IsLoadedConfigOk() noexcept { return GetCfg().isOk(); }

bool StoreUserYamlToCache() {
    auto loaded = GetLoadedConfig();
    if (loaded.IsNull() || !loaded.IsMap()) {
        return false;
    }

    auto user_file = cma::cfg::GetCfg().getUserYamlPath();

    StoreFileToCache(user_file);
    return true;
}
// Copies any file to cache with extension last successfully loaded yaml
// file in the cache
std::wstring StoreFileToCache(const fs::path &file_name) {
    std::error_code ec;
    if (!fs::exists(file_name, ec)) {
        XLOG::d("Attempting to save into cache not existing file '{}' [{}]",
                file_name, ec.value());
        return {};
    }

    auto cache_path = GetCfg().getCacheDir();
    if (cache_path.empty()) {
        XLOG::l(XLOG_FLINE + "Can't create folder {}", cache_path);
        return {};
    }

    auto cache_file = cache_path / file_name.filename();

    try {
        // check copy over itself: this happens when cache is loaded
        if (file_name == cache_file.wstring()) {
            return cache_file.wstring();
        }

        std::error_code ec;
        fs::copy(fs::path(file_name), cache_file,
                 fs::copy_options::overwrite_existing, ec);
        if (ec.value() == 0) {
            return cache_file.wstring();
        }
        XLOG::l(
            "Attempt to copy config file to cache '{}' failed with error [{}], '{}'",
            fs::path(file_name), cache_file, ec.value(), ec.message());

    } catch (std::exception &e) {
        XLOG::l("Exception during YAML saving to cache {}", e.what());
    } catch (...) {
        XLOG::l("Unbelievable!");
    }

    return cache_file.wstring();
}

}  // namespace cma::cfg

namespace cma::cfg::details {

void LoadGlobal() {
    groups::global.loadFromMainConfig();
    groups::global.setupLogEnvironment();
}

// test and reset function
void KillDefaultConfig() { GetCfg().cleanConfig(); }

fs::path FindRootByExePath(const std::wstring &cmd_line) {
    if (cmd_line.empty()) return {};  // something strange

    std::error_code ec;

    fs::path exe = cma::tools::RemoveQuotes(cmd_line);
    exe = exe.lexically_normal();
    if (!exe.has_extension()) {
        exe += ".exe";
    }
    if (!fs::exists(exe, ec)) {
        return {};  // something wrong probably
    }

    fs::path path = FindServiceImagePath(cma::srv::kServiceName);

    if (fs::equivalent(path.lexically_normal().parent_path(), exe.parent_path(),
                       ec)) {
        return path.parent_path().lexically_normal();
    }

    return {};
}

std::wstring FindServiceImagePath(std::wstring_view service_name) {
    if (service_name.empty()) {
        return {};
    }

    XLOG::l.t("Try registry '{}'", wtools::ToUtf8(service_name));

    auto key_path = L"System\\CurrentControlSet\\services\\"s;
    key_path += service_name;

    auto service_path_new =
        wtools::GetRegistryValue(key_path, L"ImagePath"sv, std::wstring());

    return cma::tools::RemoveQuotes(service_path_new);
}

fs::path ExtractPathFromServiceName(std::wstring_view service_name) {
    if (service_name.empty()) {
        return {};
    }
    XLOG::l.t("Try service: '{}'", wtools::ToUtf8(service_name));

    fs::path service_path = FindServiceImagePath(service_name);
    std::error_code ec;
    if (fs::exists(service_path, ec)) {
        auto p = service_path.parent_path();
        XLOG::l.t("Service is found '{}'", service_path);
        return p.lexically_normal();
    }

    XLOG::l("'{}' doesn't exist, error_code: [{}] '{}'", service_path,
            ec.value(), ec.message());

    return {};
}

// Typically called ONLY by ConfigInfo
// tries to find best suitable root folder
// Order: service_name, preset_root, argv[0], cwd
bool Folders::setRoot(const std::wstring &service_name,  // look in registry
                      const std::wstring &preset_root    // look in disk
) {
    XLOG::l.t("Setting root. service: '{}', preset: '{}'",
              wtools::ToUtf8(service_name), wtools::ToUtf8(preset_root));

    // Path from registry if provided
    auto service_path_new = ExtractPathFromServiceName(service_name);
    if (!service_path_new.empty()) {
        // location of the services
        root_ = service_path_new.lexically_normal();
        XLOG::l.i("Set root '{}' from registry '{}'", root_,
                  wtools::ToUtf8(service_name));
        return true;
    }

    XLOG::l.i("Service '{}' not found", wtools::ToUtf8(service_name));

    // working folder is defined
    std::error_code ec;
    fs::path work_dir = preset_root;
    if (!work_dir.empty() && fs::exists(work_dir, ec)) {
        root_ = work_dir.lexically_normal();
        XLOG::l.i("Set root '{}' direct from folder", root_);
        return true;
    }

    // By Exe
    auto ret = FindRootByExePath(wtools::GetCurrentExePath());
    if (!ret.empty()) {
        root_ = ret.lexically_normal();
        XLOG::l.i("Set root '{}' from executable", root_);
        return true;
    }

    // Current exe path used for tests
    auto cur_dir = fs::current_path(ec);
    if (ec.value() == 0 && fs::exists(cur_dir, ec)) {
        root_ = cur_dir.lexically_normal();
        XLOG::l.i("Set root '{}' from current path", root_);
        return true;
    }

    XLOG::l(XLOG_FUNC + " Parameters are invalid");
    return false;
}

// old API
bool Folders::setRootEx(const std::wstring &service_name,  // look in registry
                        const std::wstring &preset_root    // look in disk
) {
    // code is a bit strange, because we have to have possibility use
    // one of possible roots
    // storage for paths
    std::vector<fs::path> full;
    auto emplace_parent = [&full](const fs::path &path) {
        if (path.empty()) {
            return;
        }

        std::error_code ec;
        if (fs::exists(path, ec)) {
            // location of the services
            auto p = path.parent_path();
            full.emplace_back(p.lexically_normal());
        } else {
            XLOG::l("Cannot emplace back path {}, error_code: [{}] '{}'", path,
                    ec.value(), ec.message());
        }
    };

    // Path from registry if provided(watest doesn't provide)
    auto service_path_new = FindServiceImagePath(service_name);
    emplace_parent(service_path_new);

    // working folder
    if (full.empty()) {
        std::error_code ec;
        fs::path work_dir = preset_root;
        if (fs::exists(work_dir, ec)) {
            full.emplace_back(work_dir.lexically_normal());
        }
    }

    // Current exe path used for tests
    if (full.empty()) {
        std::error_code ec;
        auto cur_dir = fs::current_path(ec);
        if (ec.value() == 0 && fs::exists(cur_dir, ec)) {
            full.emplace_back(cur_dir.lexically_normal());
        }
    }

    if (full.empty()) {
        XLOG::l(XLOG_FUNC + " Parameters are invalid");
        return false;
    }

    root_ = full[0].lexically_normal();

    return true;
}  // namespace cma::cfg::details

void Folders::createDataFolderStructure(const std::wstring &proposed_folder,
                                        Protection protection) {
    try {
        fs::path folder = proposed_folder;
        data_ = makeDefaultDataFolder(folder.lexically_normal().wstring(),
                                      protection);
    } catch (const std::exception &e) {
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
    if (cma::tools::IsEqual(mode_text, values::kCleanupNone)) {
        return CleanMode::none;
    }

    if (cma::tools::IsEqual(mode_text, values::kCleanupSmart)) {
        return CleanMode::smart;
    }

    if (cma::tools::IsEqual(mode_text, values::kCleanupAll)) {
        return CleanMode::all;
    }

    return CleanMode::none;
}

namespace {
void RemoveCapGeneratedFile() {
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

void RemoveOwnGeneratedFiles() {
    auto [target_yml_example, ignore_it_again] = cap::GetExampleYmlNames();

    XLOG::l.i("Removing yml files.");

    fs::path user_yml{GetUserDir()};
    user_yml /= files::kUserYmlFile;
    std::vector<fs::path> files;
    if (cma::tools::AreFilesSame(target_yml_example, user_yml)) {
        files.emplace_back(user_yml);
    }

    files.emplace_back(target_yml_example);

    files.emplace_back(
        upgrade::ConstructProtocolFileName(GetUpgradeProtocolDir()));
    for (const auto &f : files) {
        std::error_code ec;
        XLOG::l.i("Removing user file '{}'", f);
        fs::remove(f, ec);
    }
}

void RemoveDirs(const fs::path &path) {
    std::error_code ec;
    auto del_dirs = details::RemovableDirTable();
    for (auto &d : del_dirs) {
        fs::remove_all(path / d, ec);
        XLOG::l.i("removed '{}' with status [{}]", path / d, ec.value());
    }

    auto std_dirs = details::AllDirTable();
    for (auto &d : std_dirs) {
        fs::remove(path / d, ec);
        XLOG::l.i("removed '{}' with status [{}]", path / d, ec.value());
    }
}
}  // namespace

// This function should be tested only manually
bool CleanDataFolder(CleanMode mode) {
    std::error_code ec;
    fs::path path = cma::cfg::GetUserDir();
    if (!fs::exists(path / dirs::kBakery, ec) ||
        !fs::exists(path / dirs::kUserPlugins, ec)) {
        XLOG::l.w(
            "Data Folder '{}' looks as invalid/damaged, processing is stopped",
            path);
        return false;
    }

    constexpr int event_log_code_99 = 99;
    switch (mode) {
        case CleanMode::none:
            XLOG::details::LogWindowsEventAlways(XLOG::EventLevel::information,
                                                 event_log_code_99,
                                                 "No cleaning");
            break;

        case CleanMode::smart: {
            XLOG::details::LogWindowsEventInfo(
                event_log_code_99,
                "Removing SMART from the Program Data Folder");
            RemoveCapGeneratedFile();
            RemoveOwnGeneratedFiles();
            if (g_remove_dirs_on_clean) {
                XLOG::l.i("cleaning dirs...");
                RemoveDirs(path);
            } else {
                XLOG::l.i(
                    "ATTENTION: cleaning of the dirs is disabled in this release");
            }
        } break;

        case CleanMode::all:
            XLOG::details::LogWindowsEventInfo(
                event_log_code_99, "Removing All from the Program Data Folder");
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
            dirs::kSpool,          // ???
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

/// Create project defined Directory Structure in the Data Folder
/// Returns error code
int CreateTree(const fs::path &base_path) {
    auto dir_list = AllDirTable();

    for (const auto &dir : dir_list) {
        std::error_code ec;
        auto success = fs::create_directories(base_path / dir, ec);
        if (!success && ec.value() != 0) {
            return ec.value();
        }
    }

    return 0;
}

//
// if AgentDataFolder is empty(this is default behavior ) tries
// to create folder structure in next folders:
// 1. ProgramData/CorpName/AgentName
//
fs::path Folders::makeDefaultDataFolder(std::wstring_view data_folder,
                                        Protection protection) {
    if (data_folder.empty()) {
        using cma::tools::win::GetSomeSystemFolder;
        auto draw_folder = [](std::wstring_view DataFolder) -> auto {
            fs::path app_data = DataFolder;
            app_data /= cma::cfg::kAppDataCompanyName;
            app_data /= cma::cfg::kAppDataAppName;
            return app_data;
        };

        // automatic data path, used ProgramData folder
        auto app_data_folder = GetSomeSystemFolder(FOLDERID_ProgramData);

        auto app_data = draw_folder(app_data_folder);
        auto ret = CreateTree(app_data);
        if (protection == Protection::yes) {
            XLOG::d.i("Protection requested");
            std::vector<std::wstring> commands;

            cma::security::ProtectAll(
                fs::path(app_data_folder) / cma::cfg::kAppDataCompanyName,
                commands);
            wtools::ExecuteCommandsAsync(L"all", commands);
        }

        if (ret == 0) {
            return app_data;
        }
        XLOG::l("Failed to access ProgramData Folder {}", ret);

        return {};
    }

    // path with a predefined folder
    fs::path app_data{data_folder};
    auto ret = CreateTree(app_data);
    if (ret == 0) {
        return app_data;
    }
    XLOG::l.bp("Failed to access Public Folder {}", ret);
    return {};
}

}  // namespace cma::cfg::details

namespace cma::cfg {

// looks on path for config
// accepts either full path or just name of config
bool InitializeMainConfig(const std::vector<std::wstring> &config_filenames,
                          YamlCacheOp cache_op) {
    std::wstring usable_name;

    for (const auto &name : config_filenames) {
        // Root
        auto full_path = FindConfigFile(GetRootDir(), name);
        if (full_path.empty()) {
            XLOG::l.i(
                "Loading {} direct. User and Bakery files will be IGNORED",
                wtools::ToUtf8(name));
            auto loaded = GetCfg().loadDirect(name);
            if (!loaded) continue;

            // file is loaded, write info in config file
            fs::path root_yaml = GetRootDir();
            XLOG::l("Loaded {} file, ONLY FOR debug/test mode", root_yaml);

            // exit because full path
            return true;
        }

        // this is standard method
        fs::path root_yaml = GetRootDir();
        root_yaml /= name;
        XLOG::l.i("Found root config on path {}", root_yaml);
        usable_name = name;
        break;
    }

    auto code = GetCfg().loadAggregated(usable_name, cache_op);

    if (code >= 0) {
        return true;
    }

    XLOG::l.e("Failed usable_name: '{}' at root: '{}' code is '{}'",
              wtools::ToUtf8(usable_name), GetCfg().getRootDir(), code);

    return false;
}

std::vector<std::wstring> DefaultConfigArray() {
    return {files::kDefaultMainConfig};
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

// Find any file, usually executable on one of the our paths
// for execution
std::wstring FindExeFileOnPath(const std::wstring &file_name) {
    auto paths = GetCfg().getExePaths();
    for (const auto &dir : paths) {
        auto file_path = dir / file_name;
        if (exists(file_path)) {
            return file_path.lexically_normal().wstring();
        }
    }
    return {};
}

std::vector<fs::path> GetExePaths() { return GetCfg().getExePaths(); }

// Find cfg file, usually YAML on one of the our paths for config
std::wstring FindConfigFile(const fs::path &dir_name,
                            const std::wstring &file_name) {
    XLOG::d.t("trying path {}", dir_name);
    auto file_path = dir_name / file_name;
    std::error_code ec;
    if (fs::exists(file_path, ec)) {
        return file_path.lexically_normal().wstring();
    }
    XLOG::l("Config file '{}' not found, status [{}]: {}", file_path,
            ec.value(), ec.message());
    return {};
}
};  // namespace cma::cfg

namespace cma::cfg {

std::string GetCurrentLogFileName() {
    if (ConfigLoaded()) {
        return groups::global.fullLogFileNameAsString();
    }

    static bool s_first_start = true;
    static std::string s_log_filename;
    if (s_first_start) {
        s_first_start = false;
        fs::path p{tools::win::GetSomeSystemFolder(cma::cfg::kPublicFolderId)};
        p /= kDefaultLogFileName;
        s_log_filename = p.u8string();
    }
    return s_log_filename;
}

int GetCurrentDebugLevel() {
    if (ConfigLoaded()) {
        return groups::global.debugLogLevel();
    }
    return kDefaultLogLevel;
}

XLOG::EventLevel GetCurrentEventLevel() { return XLOG::EventLevel::critical; }

bool GetCurrentWinDbg() {
    if (ConfigLoaded()) {
        return groups::global.windbgLog();
    }
    return true;
}

bool GetCurrentEventLog() {
    if (ConfigLoaded()) {
        return groups::global.eventLog();
    }
    return true;
}

}  // namespace cma::cfg

namespace cma::cfg {

// Safe loader of any yaml file with fallback on fail
YAML::Node LoadAndCheckYamlFile(const std::wstring &file_name,
                                FallbackPolicy fallback_policy,
                                int *error_code_ptr) {
    auto name = wtools::ToUtf8(file_name);
    if (fs::exists(file_name)) {
        int error_code = 0;
        try {
            YAML::Node config = YAML::LoadFile(name);
            if (config[groups::kGlobal].IsDefined()) {
                if (error_code_ptr != nullptr) *error_code_ptr = 0;
                return config;
            }

            error_code = ErrorCode::kNotCheckMK;

        } catch (const YAML::ParserException &e) {
            XLOG::l.crit(XLOG_FLINE + " yaml: '{}'", e.what());
            error_code = ErrorCode::kMalformed;
        } catch (const YAML::BadFile &e) {
            XLOG::l.crit(XLOG_FLINE + " yaml: '{}'", e.what());
            error_code = ErrorCode::kMissing;
        } catch (...) {
            XLOG::l.crit("Strange exception");
            error_code = ErrorCode::kWeird;
        }
        if (error_code_ptr != nullptr) *error_code_ptr = error_code;
    } else {
        XLOG::l("Attempt to load non-existing '{}', fallback...", name);
    }

    switch (fallback_policy) {
        case FallbackPolicy::kNone:
            break;
        case FallbackPolicy::kGenerateDefault:
        case FallbackPolicy::kLastGoodOnly:
        case FallbackPolicy::kStandard:
            XLOG::l(XLOG_FLINE + " Error: Fallback [{}] NOT SUPPORTED",
                    fallback_policy);
            return {};
    }

    return {};
}

YAML::Node LoadAndCheckYamlFile(const std::wstring &file_name,
                                int *error_code_ptr) {
    return LoadAndCheckYamlFile(file_name, FallbackPolicy::kNone,
                                error_code_ptr);
}

std::vector<std::string> StringToTable(const std::string &WholeValue) {
    auto table = cma::tools::SplitString(WholeValue, " ");

    for (auto &value : table) {
        cma::tools::AllTrim(value);
    }

    return table;
}

// gets string from the yaml and split it in table using space as divider
std::vector<std::string> GetInternalArray(std::string_view section_name,
                                          std::string_view value_name) {
    auto yaml = GetLoadedConfig();
    if (yaml.size() == 0) {
        return {};
    }

    try {
        auto section = yaml[section_name];
        return GetInternalArray(section, value_name);
    } catch (const std::exception &e) {
        XLOG::l("Cannot read yml file '{}' with '{}.{}' code:{}",
                wtools::ToUtf8(GetPathOfLoadedConfig()), section_name,
                value_name, e.what());
    }
    return {};
}

// opposite operation for the GetInternalArray
void PutInternalArray(YAML::Node yaml_node, std::string_view value_name,
                      std::vector<std::string> &arr) {
    try {
        auto section = yaml_node[value_name];
        if (arr.empty()) {
            section.remove(value_name);
            return;
        }

        auto result = cma::tools::JoinVector(arr, " ");
        if (result.back() == ' ') result.pop_back();
        yaml_node[value_name] = result;
    } catch (const std::exception &e) {
        XLOG::l("Cannot read yml file '{}' with '{}' code:'{}'",
                wtools::ToUtf8(GetPathOfLoadedConfig()), value_name, e.what());
    }
}

// opposite operation for the GetInternalArray
void PutInternalArray(std::string_view section_name,
                      std::string_view value_name,
                      std::vector<std::string> &arr) {
    auto yaml = GetLoadedConfig();
    if (yaml.size() == 0) {
        return;
    }
    try {
        auto section = yaml[section_name];
        PutInternalArray(section, value_name, arr);
    } catch (const std::exception &e) {
        XLOG::l("Cannot read yml file '{}' with '{}.{} 'code:'{}'",
                wtools::ToUtf8(GetPathOfLoadedConfig()), section_name,
                value_name, e.what());
    }
}

// gets string from the yaml and split it in table using space as divider
std::vector<std::string> GetInternalArray(const YAML::Node &yaml_node,
                                          std::string_view name) {
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
            for (const auto &node : val) {
                if (!node.IsDefined()) continue;

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

    } catch (const std::exception &e) {
        XLOG::l("Cannot read yml file '{}' with '{}' code:{}",
                wtools::ToUtf8(GetPathOfLoadedConfig()), name, e.what());
    }
    return {};
}

// #TODO refactor this trash
void SetupPluginEnvironment() {
    const std::array<std::pair<const std::string_view, const std::wstring>, 10>
        env_pairs{{{envs::kMkLocalDirName, GetLocalDir()},
                   {envs::kMkStateDirName, GetStateDir()},
                   {envs::kMkPluginsDirName, GetUserPluginsDir()},
                   {envs::kMkTempDirName, GetTempDir()},
                   {envs::kMkLogDirName, GetLogDir()},
                   {envs::kMkConfDirName, GetPluginConfigDir()},
                   {envs::kMkSpoolDirName, GetSpoolDir()},
                   {envs::kMkInstallDirName, GetUserInstallDir()},
                   {envs::kMkModulesDirName, GetUserModulesDir()},
                   {envs::kMkMsiPathName, GetUpdateDir()}}};

    for (const auto &d : env_pairs) {
        cma::tools::win::SetEnv(std::string{d.first}, wtools::ToUtf8(d.second));
    }
}

void ProcessPluginEnvironment(
    const std::function<void(std::string_view name, std::string_view value)>
        &func)

{
    const std::array<
        std::pair<const std::string_view, const std::function<std::wstring()>>,
        10>
        env_pairs{{
            // string conversion  is required because of string used in
            // interfaces
            // of SetEnv and ConvertToUTF8
            {envs::kMkLocalDirName, &GetLocalDir},
            {envs::kMkStateDirName, &GetStateDir},
            {envs::kMkPluginsDirName, &GetUserPluginsDir},
            {envs::kMkTempDirName, &GetTempDir},
            {envs::kMkLogDirName, &GetLogDir},
            {envs::kMkConfDirName, &GetPluginConfigDir},
            {envs::kMkSpoolDirName, &GetSpoolDir},
            {envs::kMkInstallDirName, &GetUserInstallDir},
            {envs::kMkMsiPathName, &GetUpdateDir},
            {envs::kMkModulesDirName, &GetUserModulesDir},
            //
        }};

    for (const auto &d : env_pairs) {
        func(d.first, wtools::ToUtf8(d.second()));
    }
}

// called upon every connection
// required for some plugins using state file
void SetupRemoteHostEnvironment(const std::string &ip_address) {
    tools::win::SetEnv(std::string(envs::kRemote), ip_address);
    tools::win::SetEnv(std::string(envs::kRemoteHost), ip_address);
}

};  // namespace cma::cfg

namespace cma::cfg::details {

std::tuple<bool, fs::path> IsInstallProtocolExists(const fs::path &root) {
    XLOG::l.i("Current root for install protocol '{}'", root);
    auto install_file = ConstructInstallFileName(root);
    if (install_file.empty()) {
        return {false, {}};
    }

    std::error_code ec;
    return {fs::exists(install_file, ec), install_file};
}

void ConfigInfo::fillExePaths(const fs::path &root) {
    constexpr std::array<std::wstring_view, 3> dir_tails{
        dirs::kAgentPlugins, dirs::kAgentProviders, dirs::kAgentUtils};

    for (const auto &d : dir_tails) {
        exe_command_paths_.emplace_back(root / d);
    }

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
    const std::wstring &service_valid_name,  // look in registry
    const std::wstring &root_folder,         // look in disk
    const std::wstring &data_folder)         // look in dis
{
    cleanFolders();
    folders_.createDataFolderStructure(
        data_folder, service_valid_name.empty() ? Folders::Protection::no
                                                : Folders::Protection::yes);

    // This is not very good idea, but we want
    // to start logging as early as possible
    XLOG::setup::ChangeDebugLogLevel(LogLevel::kLogDebug);
    groups::global.setLogFolder(folders_.getData() / dirs::kLog);
    groups::global.setupLogEnvironment();

    initEnvironment();

    folders_.setRoot(service_valid_name, root_folder);
    auto root = folders_.getRoot();

    if (!service_valid_name.empty()) {
        auto exe_path = FindServiceImagePath(service_valid_name);
        std::vector<std::wstring> commands;
        wtools::ProtectFileFromUserWrite(exe_path, commands);
        wtools::ProtectPathFromUserAccess(root, commands);
        wtools::ExecuteCommandsAsync(L"data", commands);
    }

    if (folders_.getData().empty()) {
        XLOG::l.crit("Data folder is empty.This is bad.");
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
    config_dirs_.resize(0);        // root and data

    folders_.cleanAll();
}

// normally used to reload configs and/or testing
void ConfigInfo::cleanConfig() {
    std::lock_guard lk(lock_);

    yaml_.reset();
    root_yaml_path_.clear();
    user_yaml_path_.clear();
    bakery_yaml_path_.clear();
    aggregated_ = false;
    generated_ = false;
    ok_ = false;
}

bool ConfigInfo::pushFolders(const fs::path &root, const fs::path &data) {
    std::lock_guard lk(lock_);
    if (folders_stack_.size() >= kMaxFoldersStackSize) {
        XLOG::l("Folders Stack is overflown, max size is [{}]",
                kMaxFoldersStackSize);
        return false;
    }
    folders_stack_.push(folders_);
    folders_.setRoot({}, root.wstring());
    folders_.createDataFolderStructure(data, Folders::Protection::no);

    return true;
}

bool ConfigInfo::pushFoldersNoIo(const fs::path &root,
                                 const fs::path & /*data*/) {
    std::lock_guard lk(lock_);
    if (folders_stack_.size() >= kMaxFoldersStackSize) {
        XLOG::l("Folders Stack is overflown, max size is [{}]",
                kMaxFoldersStackSize);
        return false;
    }
    folders_stack_.push(folders_);
    folders_.setRoot({}, root.wstring());
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

std::wstring FindMsiExec() {
    fs::path p = cma::tools::win::GetSystem32Folder();
    p /= "msiexec.exe";

    std::error_code ec;
    if (fs::exists(p, ec)) {
        XLOG::t.i("Found msiexec '{}'", p);
        return p.wstring();
    }

    XLOG::l.crit(
        "Cannot find msiexec '{}' error [{}] '{}', automatic update is not possible",
        p, ec.value(), ec.message());
    return {};
}

std::string FindHostName() {
    // host name
    constexpr int max_hostname_len = 256;
    char host_name[max_hostname_len] = "";  // NOLINT
    auto ret = ::gethostname(host_name, max_hostname_len);
    if (ret != 0) {
        XLOG::l("Can't call gethostname, error [{}]", ret);
        return {};
    }
    return host_name;
}

void ConfigInfo::initEnvironment() {
    host_name_ = FindHostName();
    cwd_ = fs::current_path().wstring();
    path_to_msi_exec_ = FindMsiExec();
}

namespace {

// NOTE: To avoid exception when getting Node type we must check that node is
// defined

bool IsYamlMap(const YAML::Node &node) {
    return node.IsDefined() && node.IsMap();
}

bool IsYamlSeq(const YAML::Node &node) {
    return node.IsDefined() && node.IsSequence();
}

std::string GetMapNodeName(const YAML::Node &node) {
    try {
        if (!IsYamlMap(node)) {
            return {};
        }

        auto iterator = node.begin();

        auto id = iterator->first;
        return id.as<std::string>();
    } catch (const std::exception &e) {
        XLOG::l(XLOG_FUNC + " Exception on conversion '{}'", e.what());
        return {};
    }
}
}  // namespace

constexpr Combine GetCombineMode(std::string_view name) {
    if (name == groups::kWinPerf) {
        return Combine::merge;
    }
    if (name == groups::kLogWatchEvent) {
        return Combine::merge_value;
    }

    return Combine::overwrite;
}

void CombineSequence(std::string_view name, YAML::Node target_value,
                     const YAML::Node &source_value, Combine combine) {
    if (!source_value.IsDefined() || source_value.IsNull()) {
        XLOG::t(XLOG_FUNC + " skipping empty section '{}'", name);
        return;
    }

    if (source_value.IsScalar()) {
        XLOG::d.t("Overriding seq named '{}' with scalar. OK.", name);
        target_value = source_value;
        return;
    }

    if (!IsYamlSeq(source_value)) {
        XLOG::l(XLOG_FLINE + " skipping '{}' : wrong type ", name);
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
            for (const auto &entry : source_value) {
                auto s_name = GetMapNodeName(entry);
                if (s_name.empty()) {
                    continue;
                }

                if (std::none_of(std::begin(target_value),
                                 std::end(target_value),
                                 [s_name](const YAML::Node &Node) -> bool {
                                     return s_name == GetMapNodeName(Node);
                                 })) {
                    target_value.push_back(entry);
                }
            }
            break;

        // by logfiles
        case Combine::merge_value: {
            auto new_seq = YAML::Clone(source_value);
            for (const auto &entry : target_value) {
                auto s_name = GetMapNodeName(entry);
                if (s_name.empty()) {
                    continue;
                }

                if (std::none_of(std::begin(source_value),
                                 std::end(source_value),
                                 [s_name](const YAML::Node &node) -> bool {
                                     return s_name == GetMapNodeName(node);
                                 })) {
                    new_seq.push_back(entry);
                }
            }
            target_value = new_seq;
            break;
        }
    }
}

static void loadMap(std::string_view name, YAML::Node target_value,
                    const YAML::Node &source_value) {
    // MAP
    if (!IsYamlMap(source_value)) {
        if (!source_value.IsNull()) {
            XLOG::l(XLOG_FLINE + " expected map '{}', we have [{}]", name,
                    source_value.Type());
        }
        return;
    }

    // MAP-MAP
    for (auto itx = source_value.begin(); itx != source_value.end(); ++itx) {
        auto combine_type = GetCombineMode(name);
        ConfigInfo::smartMerge(target_value, source_value, combine_type);
    }
}

// #TODO simplify or better rewrite in more common form
bool ConfigInfo::smartMerge(YAML::Node &target, const YAML::Node &source,
                            Combine combine) {
    // we are scanning source
    for (auto it = source.begin(); it != source.end(); ++it) {
        const auto source_name = it->first;
        const auto source_value = it->second;
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
            loadMap(name, target_value, source_value);
        } else if (IsYamlSeq(target_value)) {
            // SEQ
            CombineSequence(name, target_value, source_value, combine);
        } else {
            // SCALAR or UNDEF
            if (source_value.IsDefined()) {
                target_value = source_value;  // other just override
            } else {
                XLOG::l.bp(XLOG_FLINE + " bad source");
            }
        }
    }

    return true;
}

std::vector<ConfigInfo::YamlData> ConfigInfo::buildYamlData(
    const std::wstring &config_file_name) const {
    std::vector<YamlData> yamls = {
        {getRootDir() / config_file_name, root_yaml_time_},
        {getBakeryDir() / config_file_name, bakery_yaml_time_},
        {getUserDir() / config_file_name, user_yaml_time_}};

    yamls[1].path_.replace_extension(files::kDefaultBakeryExt);
    yamls[2].path_.replace_extension(files::kDefaultUserExt);

    for (auto &yd : yamls) {
        XLOG::d.t("Loading '{}'", yd.path_);
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
    static InfoStrings &get() {
        static InfoStrings s_the_instance;
        return s_the_instance;
    }
    ~InfoStrings() = default;

    InfoStrings(const InfoStrings &) = delete;
    InfoStrings &operator=(const InfoStrings &) = delete;

    InfoStrings(InfoStrings &&) = delete;
    InfoStrings &operator=(InfoStrings &&) = delete;

    [[nodiscard]] std::string agentString() const noexcept {
        return agent_string_;
    }
    [[nodiscard]] std::string osString() const noexcept { return os_string_; }

private:
    InfoStrings() {
        agent_string_ = makeAgentInfoString();
        os_string_ = makeOsInfoString();
    }

    // generates short info about agent(version, build, environment)
    // required to correctly identify client in log
    static std::string makeAgentInfoString() {
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

    static std::string makeOsInfoString() {
        const std::string_view server{IsWindowsServer() ? "server" : "desktop"};
        const std::string_view bits_count{Is64BitWindows() ? "64" : "32"};
        const std::string_view os_id{GetWindowsId()};

        return fmt::format("Win{}-{} {}", os_id, bits_count, server);
    }

    std::string agent_string_;
    std::string os_string_;
};

namespace {
bool TryMerge(YAML::Node &config_node, const ConfigInfo::YamlData &yaml_data) {
    if (!yaml_data.exists() || yaml_data.bad()) {
        return false;
    }

    auto bakery = YAML::LoadFile(yaml_data.path_.u8string());
    // special cases for plugins and folder
    PreMergeSections(bakery, config_node);

    // normal cases
    ConfigInfo::smartMerge(config_node, bakery, Combine::overwrite);
    return true;
}
}  // namespace

// config_node is a resulting full config
// yaml_data is array from root, bakery and user configs
// we will load all others configs and try to merge
void ConfigInfo::mergeYamlData(YAML::Node &config_node,
                               const std::vector<YamlData> &yaml_data) {
    bool bakery_ok = false;
    bool user_ok = false;

    const auto &root_data = yaml_data[0];
    const auto &bakery_data = yaml_data[1];
    const auto &user_data = yaml_data[2];

    try {
        bakery_ok = TryMerge(config_node, bakery_data);
    } catch (...) {
        XLOG::l("Bakery {} is bad", bakery_data.path_);
    }

    try {
        user_ok = TryMerge(config_node, user_data);
    } catch (...) {
        XLOG::l("User {} is bad", user_data.path_);
    }

    std::lock_guard lk(lock_);
    root_yaml_time_ = root_data.timestamp();
    bakery_yaml_time_ =
        bakery_ok ? bakery_data.timestamp() : fs::file_time_type::min();
    bakery_ok_ = bakery_ok;
    user_yaml_time_ =
        user_ok ? user_data.timestamp() : fs::file_time_type::min();
    user_ok_ = user_ok;

    yaml_ = config_node;

    XLOG::d.i(
        "Loaded Config Files by Agent {} @ '{}'\n"
        "    root:   '{}' size={} {}\n"
        "    bakery: '{}' size={} {}\n"
        "    user:   '{}' size={} {}",
        InfoStrings::get().agentString(), InfoStrings::get().osString(),
        //
        root_data.path_, root_data.data().size(),
        root_data.bad() ? "[FAIL]" : "[OK]",
        //
        bakery_data.path_, bakery_data.data().size(),
        bakery_data.bad() ? "[FAIL]" : "[OK]",
        //
        user_data.path_, user_data.data().size(),
        user_data.bad() ? "[FAIL]" : "[OK]");

    // setting up paths  to the other files
    root_yaml_path_ = root_data.path_;
    bakery_yaml_path_ = bakery_data.path_;
    user_yaml_path_ = user_data.path_;

    aggregated_ = true;
    g_uniq_id++;
    ok_ = true;
}

// This function will load all three YAML files as a one
// Order main -> bakery -> user
// ON SUCCESS -> all successfully loaded diles are cached
// ON FAIL
// standard call is tryAggregateLoad(L"check_mk.yml", true, true);
LoadCfgStatus ConfigInfo::loadAggregated(const std::wstring &config_filename,
                                         YamlCacheOp cache_op) {
    if (config_filename.empty()) {
        XLOG::l(XLOG_FLINE + " empty name");
        return LoadCfgStatus::kAllFailed;
    }
    auto yamls = buildYamlData(config_filename);

    // check root
    auto &root = yamls[0];
    if (!root.exists() || root.data().empty() || root.bad()) {
        XLOG::d("Cannot find/read root cfg '{}'. ", root.path_);
        return LoadCfgStatus::kAllFailed;
    }

    bool changed = false;
    for (auto &yd : yamls) {
        if (yd.changed()) {
            changed = true;
            break;
        }
    }

    if (!changed) return LoadCfgStatus::kFileLoaded;

    int error_code = 0;
    try {
        auto config = YAML::LoadFile(yamls[0].path_.u8string());

        if (config[groups::kGlobal].IsDefined()) {
            mergeYamlData(config, yamls);

            if (ok_ && user_ok_ && cache_op == YamlCacheOp::update) {
                StoreUserYamlToCache();
            }
            return LoadCfgStatus::kFileLoaded;
        }
        error_code = ErrorCode::kNotCheckMK;

    } catch (const YAML::ParserException &e) {
        XLOG::l.crit(XLOG_FLINE + " yaml: '{}'", e.what());
        error_code = ErrorCode::kMalformed;
    } catch (const YAML::BadFile &e) {
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
}

// LOOOONG operation
// when failed old config retained
bool ConfigInfo::loadDirect(const fs::path &file) {
    const fs::path &fpath = file;
    std::error_code ec;
    if (!fs::exists(fpath, ec)) {
        XLOG::l("File {} not found, code = [{}] '{}'", fpath, ec.value(),
                ec.message());
        return false;
    }
    auto ftime = fs::last_write_time(fpath, ec);

    // we will load when error happens, or time changed or name changed
    bool load_required =
        ec.value() != 0 || ftime != root_yaml_time_ || file != root_yaml_path_;

    if (!load_required) {
        return ok_;
    }

    auto new_yaml = LoadAndCheckYamlFile(file, FallbackPolicy::kNone);
    if (new_yaml.size() == 0) {
        return false;
    }

    std::lock_guard lk(lock_);
    root_yaml_time_ = ftime;
    yaml_ = new_yaml;
    root_yaml_path_ = file;
    XLOG::d.t("Loaded Config from  {}", file);

    // setting up paths  to the other files
    user_yaml_path_ = file;
    root_yaml_time_ = fs::last_write_time(file);
    user_yaml_path_.clear();
    user_yaml_time_ = decltype(user_yaml_time_)::min();
    bakery_yaml_path_.clear();
    aggregated_ = false;
    ok_ = true;
    g_uniq_id++;
    return true;
}

bool ConfigInfo::loadDirect(std::string_view text) {
    auto new_yaml = YAML::Load(std::string{text});
    if (new_yaml.size() == 0) {
        return false;
    }

    std::lock_guard lk(lock_);
    yaml_ = new_yaml;

    g_uniq_id++;
    return true;
}

}  // namespace cma::cfg::details

namespace cma::cfg {

// generates standard agent time string
std::string ConstructTimeString() {
    constexpr uint32_t k1000 = 1000;
    auto cur_time = std::chrono::system_clock::now();
    auto in_time_t = std::chrono::system_clock::to_time_t(cur_time);
    std::stringstream sss;
    auto ms =
        duration_cast<std::chrono::milliseconds>(cur_time.time_since_epoch()) %
        k1000;
    auto *loc_time = std::localtime(&in_time_t);
    auto p_time = std::put_time(loc_time, "%Y-%m-%d %T");
    sss << p_time << "." << std::setfill('0') << std::setw(3) << ms.count()
        << std::ends;

    return sss.str();
}

// makes the name of install.protocol file
// may return empty path
fs::path ConstructInstallFileName(const fs::path &dir) {
    if (dir.empty()) {
        XLOG::d("Attempt to create install protocol in current folder");
        return {};
    }

    fs::path protocol_file = dir;
    protocol_file /= cma::cfg::files::kInstallProtocol;
    return protocol_file;
}

bool IsNodeNameValid(std::string_view name) {
    if (name.empty()) {
        return true;
    }
    return name[0] != '_';
}

int RemoveInvalidNodes(YAML::Node node) {
    //
    if (!node.IsDefined() || !node.IsMap()) {
        return 0;
    }

    std::vector<std::string> to_remove;
    int counter = 0;

    for (YAML::const_iterator it = node.begin(); it != node.end(); ++it) {
        auto key = it->first.as<std::string>();  // <- key
        if (!IsNodeNameValid(key)) {
            XLOG::t("Removing node '{}'", key);
            to_remove.emplace_back(key);
            continue;
        }

        int sub_count = RemoveInvalidNodes(node[key]);
        counter += sub_count;
    }
    for (auto &r : to_remove) {
        node.remove(r);
        ++counter;
    }
    return counter;
}

bool ReplaceInString(std::string &in_out, std::string_view marker,
                     std::string_view value) {
    auto pos = in_out.find(marker);
    if (pos != std::string::npos) {
        in_out.replace(pos, marker.length(), value);
        return true;
    }
    return false;
}

std::string ReplacePredefinedMarkers(std::string_view work_path) {
    const std::array<std::pair<const std::string_view, const std::wstring>, 5>
        pairs{{// core:
               {vars::kPluginCoreFolder, GetSystemPluginsDir()},
               {vars::kPluginBuiltinFolder, GetSystemPluginsDir()},
               // pd:
               {vars::kPluginUserFolder, GetUserPluginsDir()},
               {vars::kLocalUserFolder, GetLocalDir()},
               {vars::kProgramDataFolder, GetUserDir()}}

        };

    std::string f(work_path);
    for (const auto &[marker, path] : pairs) {
        if (ReplaceInString(f, marker, wtools::ToUtf8(path))) {
            return f;
        }
    }

    return f;
}

// converts "any/relative/path" into
// "marker\\any\\relative\\path"
// return false if yaml is not suitable for patching
// normally used only by cvt
bool PatchRelativePath(YAML::Node yaml_config, std::string_view group_name,
                       std::string_view key_name, std::string_view subkey_name,
                       std::string_view marker) {
    if (group_name.empty() || key_name.empty() || subkey_name.empty() ||
        marker.empty()) {
        XLOG::l(XLOG_FUNC + " Problems with parameter '{}' '{}' '{}' '{}'",
                group_name, key_name, subkey_name, marker);
        return false;
    }
    auto group = yaml_config[group_name];
    if (!group.IsDefined() || !group.IsMap()) {
        return false;
    }

    auto key = group[key_name];
    if (!key.IsDefined() || !key.IsSequence()) {
        return false;
    }

    auto sz = key.size();
    const std::string name(subkey_name);
    for (size_t k = 0; k < sz; ++k) {
        auto node = key[k][name];
        if (!node.IsDefined() || !node.IsScalar()) {
            continue;
        }

        auto entry = node.as<std::string>();
        if (entry.empty()) {
            continue;
        }

        fs::path path = entry;
        auto p = path.lexically_normal();
        if (p.u8string()[0] == fs::path::preferred_separator) {
            continue;
        }
        if (p.u8string()[0] == marker[0]) {
            continue;
        }
        if (p.is_relative()) {
            key[k][name] = std::string(marker) + "\\" + entry;
        }
    }
    return true;
}

//*** WMIC uninstaller ***
// Run
// wmic product get name,version /format:csv
//      to get name and version
// Run
// wmic product where name="Check MK Agent 2.0" call uninstall /nointeractive
//      to remove the product
// Oprations ARE VERY LONG
constexpr std::string_view g_wmic_uninstall_command =
    "wmic product where name=\"{}\" call uninstall /nointeractive";

std::string CreateWmicCommand(std::string_view product_name) {
    return fmt::format(g_wmic_uninstall_command, product_name);
}

fs::path CreateWmicUninstallFile(const fs::path &temp_dir,
                                 std::string_view product_name) {
    auto file = temp_dir / "exec_uninstall.cmd";
    try {
        std::ofstream ofs(file.u8string());
        ofs << CreateWmicCommand(product_name);
        ofs.close();
        if (fs::exists(file)) {
            return file;
        }
        XLOG::l("Attempt to create '{}' file is failed", file);
        return {};
    } catch (const std::exception &e) {
        XLOG::l("Attempt to create '{}' file is failed with exception {}", file,
                e.what());
    }

    return {};
}

bool UninstallProduct(std::string_view name) {
    fs::path temp{cfg::GetTempDir()};
    auto fname = CreateWmicUninstallFile(temp, name);
    if (fname.empty()) {
        return false;
    }
    XLOG::l.i("Starting uninstallation command '{}'", fname);
    auto pid = tools::RunStdCommand(fname.wstring(), true);
    if (pid == 0) {
        XLOG::l("Failed to start '{}'", fname);
        return false;
    }
    XLOG::l.i("Started uninstallation command '{}' with pid [{}]", fname, pid);
    return true;
}

details::ConfigInfo &GetCfg() { return details::g_config_info; }
std::atomic<uint64_t> details::ConfigInfo::g_uniq_id = 1;

}  // namespace cma::cfg
