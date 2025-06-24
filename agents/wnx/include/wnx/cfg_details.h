// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#pragma once

// other files
#include <filesystem>
#include <stack>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

#include "cfg.h"
#include "read_file.h"

namespace cma::cfg::details {

/// get ImagePath value from Registry
std::wstring FindServiceImagePath(std::wstring_view service_name);

std::filesystem::path ExtractPathFromServiceName(
    std::wstring_view service_name);

std::filesystem::path FindRootByExePath(const std::wstring &cmd_line);

enum class CleanMode { none, smart, all };

// The flag is based on AW report
constexpr bool g_remove_dirs_on_clean = true;

CleanMode GetCleanDataFolderMode();
bool CleanDataFolder(CleanMode mode);

class Folders {
public:
    // if ServiceValidName set, then we MUST find path
    // otherwise look for WorkFolder
    // otherwise current path to current exe
    bool setRoot(const std::wstring &service_name,  // look in registry
                 const std::wstring &preset_root);  // look in disk
    // deprecated API
    bool setRootEx(const std::wstring &service_name,  // look in registry
                   const std::wstring &preset_root);  // look in disk
    enum class Protection { no, yes };
    void createDataFolderStructure(const std::wstring &proposed_folder);

    /// for reloading
    void cleanAll();

    [[nodiscard]] std::filesystem::path getSystemPlugins() const {
        return root_.empty() ? L"" : root_ / dirs::kAgentPlugins;
    }

    [[nodiscard]] std::filesystem::path getUserPlugins() const {
        return getData() / dirs::kUserPlugins;
    }

    [[nodiscard]] std::filesystem::path getProviders() const {
        return root_.empty() ? L"" : root_ / dirs::kAgentProviders;
    }

    [[nodiscard]] std::filesystem::path getMrpe() const {
        return root_.empty() ? L"" : root_ / dirs::kAgentMrpe;
    }
    [[nodiscard]] std::filesystem::path getRoot() const { return root_; }

    [[nodiscard]] std::filesystem::path getUser() const { return data_; }

    [[nodiscard]] std::filesystem::path getLocal() const {
        return getData() / dirs::kLocal;
    }

    [[nodiscard]] std::filesystem::path getSpool() const {
        return getData() / dirs::kSpool;
    }

    [[nodiscard]] std::filesystem::path getTemp() const {
        return getData() / dirs::kTemp;
    }

    [[nodiscard]] std::filesystem::path getBakery() const {
        return data_ / dirs::kBakery;
    }

    [[nodiscard]] std::filesystem::path getState() const {
        return data_ / dirs::kState;
    }

    [[nodiscard]] std::filesystem::path getLib() const {
        return data_ / dirs::kLib;
    }
    [[nodiscard]] std::filesystem::path getAuState() const {
        return data_ / dirs::kAuStateLocation;
    }

    [[nodiscard]] std::filesystem::path getPluginConfigPath() const {
        return data_ / dirs::kPluginConfig;
    }

    [[nodiscard]] std::filesystem::path getLog() const {
        return data_ / dirs::kLog;
    }

    [[nodiscard]] std::filesystem::path getBackup() const {
        return data_ / dirs::kBackup;
    }

    [[nodiscard]] std::filesystem::path getUserBin() const {
        return data_ / dirs::kUserBin;
    }

    [[nodiscard]] std::filesystem::path getUpdate() const {
        return data_ / dirs::kUpdate;
    }

    [[nodiscard]] std::filesystem::path getPublicLogs() const {
        return public_logs_;
    }
    [[nodiscard]] std::filesystem::path getPrivateLogs() const {
        return private_logs_;
    }

    [[nodiscard]] std::filesystem::path getData() const { return data_; }

    /// returns path if folder was created successfully
    static std::filesystem::path makeDefaultDataFolder(
        std::wstring_view data_folder);

private:
    std::filesystem::path root_;          // where is root
    std::filesystem::path data_;          // ProgramData
    std::filesystem::path public_logs_;   //
    std::filesystem::path private_logs_;  //
};

std::vector<std::wstring_view> AllDirTable();
std::vector<std::wstring_view> RemovableDirTable();

int CreateTree(const std::filesystem::path &base_path);

}  // namespace cma::cfg::details

namespace cma::cfg {
namespace details {
constexpr size_t kMaxFoldersStackSize = 32;

/// low level API to combine sequences
enum class Combine { overwrite, merge, merge_value };
constexpr Combine GetCombineMode(std::string_view name);
void CombineSequence(std::string_view name, YAML::Node target_value,
                     const YAML::Node &source_value, Combine combine);

/// critical and invisible global variables
/// YAML config and PAThs are here
class ConfigInfo {
public:
    struct YamlData {
        YamlData(std::filesystem::path Path,
                 std::filesystem::file_time_type /*Timestamp*/) noexcept
            : path_(std::move(Path)) {}

        void loadFile() {
            checkStatus();
            data_.clear();
            bad_ = false;
            if (!exists()) {
                XLOG::d.t("{} is absent, return", path_);
                return;
            }

            auto raw_data = tools::ReadFileInVector(path_.wstring());
            if (raw_data.has_value()) {
                data_ = wtools::ConditionallyConvertFromUtf16(raw_data.value());
                checkData();
            }
        }

        [[nodiscard]] bool exists() const noexcept { return exists_; }
        [[nodiscard]] bool bad() const noexcept { return bad_; }
        [[nodiscard]] bool changed() const noexcept {
            return last_loaded_time_ != timestamp_;
        }
        [[nodiscard]] const std::string &data() const noexcept { return data_; }
        [[nodiscard]] auto timestamp() const noexcept { return timestamp_; }

        std::filesystem::path path_;

    private:
        std::string data_;
        /// verifies exists and timestamp
        void checkStatus() noexcept {
            namespace fs = std::filesystem;
            std::error_code ec;
            exists_ = fs::exists(path_, ec);
            if (exists_) {
                timestamp_ = fs::last_write_time(path_, ec);
            } else {
                timestamp_ = std::filesystem::file_time_type::min();
            }
        }

        /// try to load data as yaml
        void checkData() {
            try {
                auto yaml = YAML::Load(data_);
                if (!yaml.IsDefined()) {
                    XLOG::l("Cannot load cfg '{}'", path_);
                    data_.clear();
                }
            } catch (const std::exception &e) {
                XLOG::l.crit("Can't load yaml file '{}', exception: '{}'",
                             path_, e.what());
                bad_ = true;
            } catch (...) {
                XLOG::l(XLOG::kBp)(XLOG_FLINE + " exception bad");
                bad_ = true;
            }
        }

        std::filesystem::file_time_type last_loaded_time_;
        bool exists_ = false;
        bool bad_ = true;
        std::filesystem::file_time_type timestamp_;
    };

    using sptr = std::shared_ptr<ConfigInfo>;
    ConfigInfo() = default;
    ConfigInfo(const ConfigInfo &) = delete;
    ConfigInfo &operator=(const ConfigInfo &) = delete;
    ConfigInfo(ConfigInfo &&) = delete;
    ConfigInfo &operator=(ConfigInfo &&) = delete;
    ~ConfigInfo() = default;
    void initFolders(
        const std::wstring &service_valid_name,  // look in registry
        const std::wstring &root_folder,         // look in disk
        const std::wstring &data_folder);        // look in disk

    void cleanFolders();
    void cleanConfig();

    // TODO (sk): move to tests
    /// Used in tests only( to prevent the tree from changing )
    bool pushFolders(const std::filesystem::path &root,
                     const std::filesystem::path &data);

    // TODO (sk): move to tests
    /// Used in tests only( to prevent the tree from changing )
    bool pushFoldersNoIo(const std::filesystem::path &root,
                         const std::filesystem::path &data);

    // TODO (sk): move to tests only( to prevent the tree from changing )
    /// Used in tests only to prevent context
    bool popFolders();

    // not so heavy operation, use free
    YAML::Node getConfig() const noexcept {
        std::lock_guard lk(lock_);
        if (ok_) {
            return yaml_;
        }

        return {};
    }

    void setConfig(const YAML::Node &yaml) {
        std::lock_guard lk(lock_);
        if (yaml_.IsDefined()) {
            yaml_ = yaml;
        }
    }

    std::wstring getRootYamlPath() const noexcept {
        std::lock_guard lk(lock_);
        return root_yaml_path_;
    }

    std::wstring getBakeryYamlPath() const noexcept {
        std::lock_guard lk(lock_);
        return bakery_yaml_path_;
    }

    std::wstring getUserYamlPath() const noexcept {
        std::lock_guard lk(lock_);
        return user_yaml_path_;
    }

    bool isGenerated() const noexcept { return generated_; }
    bool isOk() const noexcept { return ok_; }

    auto getExePaths() const {
        std::lock_guard lk(lock_);
        return exe_command_paths_;
    }

    auto getSystemPluginsDir() const {
        std::lock_guard lk(lock_);
        return folders_.getSystemPlugins();
    }

    auto getUserPluginsDir() const {
        std::lock_guard lk(lock_);
        return folders_.getUserPlugins();
    }

    auto getLocalDir() const {
        std::lock_guard lk(lock_);
        return folders_.getLocal();
    }
    auto getDataDir() const {
        std::lock_guard lk(lock_);
        return folders_.getData();
    }

    auto getRootDir() const {
        std::lock_guard lk(lock_);
        return folders_.getRoot();
    }

    auto getBakeryDir() const {
        std::lock_guard lk(lock_);
        return folders_.getBakery();
    }

    auto getUserDir() const {
        std::lock_guard lk(lock_);
        return folders_.getUser();
    }

    auto getCacheDir() const {
        std::lock_guard lk(lock_);
        return folders_.getBackup();
    }

    auto getUserBinDir() const {
        std::lock_guard lk(lock_);
        return folders_.getUserBin();
    }

    auto getStateDir() const {
        std::lock_guard lk(lock_);
        return folders_.getState();
    }

    auto getLibDir() const {
        std::lock_guard lk(lock_);
        return folders_.getLib();
    }

    auto getAuStateDir() const {
        std::lock_guard lk(lock_);
        return folders_.getAuState();
    }

    auto getPluginConfigDir() const {
        std::lock_guard lk(lock_);
        return folders_.getPluginConfigPath();
    }

    auto getUpdateDir() const {
        std::lock_guard lk(lock_);
        return folders_.getUpdate();
    }

    auto getSpoolDir() const {
        std::lock_guard lk(lock_);
        return folders_.getSpool();
    }

    auto getTempDir() const {
        std::lock_guard lk(lock_);
        return folders_.getTemp();
    }

    auto getLogDir() const {
        std::lock_guard lk(lock_);
        return folders_.getLog();
    }

    auto getHostName() const {
        std::lock_guard lk(lock_);
        return host_name_;
    }

    auto getCwd() const {
        std::lock_guard lk(lock_);
        return cwd_;
    }

    auto getConfiguredLogFileDir() const {
        std::lock_guard lk(lock_);
        return logfile_dir_;
    }

    auto getMsiExecPath() const {
        std::lock_guard lk(lock_);
        return path_to_msi_exec_;
    }

    void setConfiguredLogFileDir(const std::wstring &Path) {
        std::lock_guard lk(lock_);
        logfile_dir_ = Path;
    }

    auto isBakeryLoaded() const {
        std::lock_guard lk(lock_);
        return bakery_ok_;
    }

    auto isUserLoaded() const {
        std::lock_guard lk(lock_);
        return user_ok_;
    }

    // main api call to load all three configs
    LoadCfgStatus loadAggregated(const std::wstring &config_filename,
                                 YamlCacheOp cache_op);

    static bool smartMerge(YAML::Node &target, const YAML::Node &source,
                           Combine combine);

    // THIS IS ONLY FOR TESTING
    bool loadDirect(const std::filesystem::path &file);
    bool loadDirect(std::string_view text);

    static uint64_t uniqId() noexcept { return uniq_id_; }

    void initEnvironment();

private:
    void fillExePaths(const std::filesystem::path &root);
    void fillConfigDirs();
    std::vector<YamlData> buildYamlData(
        const std::wstring &config_file_name) const;
    void mergeYamlData(YAML::Node &config_node,
                       const std::vector<YamlData> &yaml_data);
    // LOOOONG operation
    // when failed old config retained
    std::vector<std::filesystem::path>
        exe_command_paths_;  // root/utils, root/plugins etc
    std::vector<std::filesystem::path> config_dirs_;  // root and data

    std::string host_name_;
    std::wstring cwd_;
    std::wstring logfile_dir_;

    std::wstring path_to_msi_exec_;

    mutable std::mutex lock_;

    YAML::Node yaml_;
    Folders folders_;
    std::stack<Folders> folders_stack_;

    std::wstring root_yaml_path_;    // located in root
    std::wstring bakery_yaml_path_;  // located in bakery
    std::wstring user_yaml_path_;    // located in data

    std::filesystem::file_time_type root_yaml_time_;
    std::filesystem::file_time_type bakery_yaml_time_;
    std::filesystem::file_time_type user_yaml_time_;
    bool bakery_ok_ = false;
    bool user_ok_ = false;
    bool aggregated_ = false;
    bool generated_ = false;
    bool ok_ = false;

    static std::atomic<uint64_t> uniq_id_;
};

std::filesystem::path ConvertLocationToLogPath(std::string_view location);
std::filesystem::path GetDefaultLogPath();
std::wstring FindMsiExec();
std::string FindHostName();
}  // namespace details
details::ConfigInfo &GetCfg() noexcept;
using CfgNode = details::ConfigInfo::sptr;

CfgNode CreateNode(const std::string &name);
CfgNode GetNode(const std::string &name);
bool RemoveNode(const std::string &name);
}  // namespace cma::cfg
