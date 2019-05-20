#pragma once
// registry access
#define WIN32_LEAN_AND_MEAN
#include "windows.h"

// other files
#include <filesystem>
#include <string>
#include <vector>

#include "cfg.h"
#include "read_file.h"
#include "tools/_misc.h"

// Class to be used internally
// placed in h not cpp to be unit tested.
// should be used as global variable
// not thread safe
// initialized ONCE on start
namespace cma::cfg::details {

// tool to get ImagePath value from Registry
inline std::wstring FindServiceImagePath(const std::wstring ServiceValidName) {
    std::wstring key_path = L"System\\CurrentControlSet\\services\\";
    key_path += ServiceValidName;
    std::wstring service_path_new =
        wtools::GetRegistryValue(key_path, L"ImagePath", std::wstring());

    // check for very short strings
    if (service_path_new.length() < 2) return {};

    if (auto back = service_path_new.back(); back == L'\"')
        service_path_new.pop_back();
    if (auto front = service_path_new.front(); front == L'\"')
        service_path_new.erase(0, 1);

    return service_path_new;
}

class Folders {
public:
    // if ServiceValidName set, then we MUST find path
    // otherwise look for WorkFolder
    // otherwise current path to current exe
    bool setRoot(const std::wstring& ServiceValidName,  // look in registry
                 const std::wstring& WorkFolder);       // look in disk

    void createDataFolderStructure(const std::wstring& AgentDataFolder);

    // for testing and reloading
    void cleanAll();

    inline std::filesystem::path getSystemPlugins() const {
        return root_.empty() ? L"" : root_ / dirs::kAgentPlugins;
    }

    inline std::filesystem::path getUserPlugins() const {
        return getData() / dirs::kUserPlugins;
    }

    inline std::filesystem::path getProviders() const {
        return root_.empty() ? L"" : root_ / dirs::kAgentProviders;
    }

    inline std::filesystem::path getMrpe() const {
        return root_.empty() ? L"" : root_ / dirs::kAgentMrpe;
    }
    inline std::filesystem::path getRoot() const { return root_; }

    inline std::filesystem::path getUser() const { return data_; }

    inline std::filesystem::path getLocal() const {
        return getData() / dirs::kLocal;
    }

    inline std::filesystem::path getSpool() const {
        return getData() / dirs::kSpool;
    }

    inline std::filesystem::path getTemp() const {
        return getData() / dirs::kTemp;
    }

    inline std::filesystem::path getBakery() const {
        return data_ / dirs::kBakery;
    }

    inline std::filesystem::path getState() const {
        return data_ / dirs::kState;
    }

    inline std::filesystem::path getPluginConfigPath() const {
        return data_ / dirs::kPluginConfig;
    }

    inline std::filesystem::path getCache() const {
        return data_ / dirs::kCache;
    }

    inline std::filesystem::path getUpdate() const {
        return data_ / dirs::kUpdate;
    }

    inline std::filesystem::path getPublicLogs() const { return public_logs_; }
    inline std::filesystem::path getPrivateLogs() const {
        return private_logs_;
    }

    inline std::filesystem::path getData() const { return data_; }

private:
    // make [recursive] folder in windows
    // returns path if folder was created successfully
    // #TODO gtest?
    // #TODO into ConfigInfo
    std::filesystem::path makeDefaultDataFolder(
        const std::wstring& AgentDataFolder);
    std::filesystem::path root_;          // where is root
    std::filesystem::path data_;          // ProgramData
    std::filesystem::path public_logs_;   //
    std::filesystem::path private_logs_;  //

    // testing, enabled only in header we see gtest.h
#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class AgentConfig;
    FRIEND_TEST(AgentConfig, FoldersTest);
#endif
};

}  // namespace cma::cfg::details

namespace cma::cfg {
namespace details {

// critical and invisible global variables
// YAML config and PAThs are here
class ConfigInfo {
    enum { kMaxFiles = 3 };
    struct YamlData {
        YamlData(const std::filesystem::path& Path,
                 std::filesystem::file_time_type Timestamp)
            : path_(Path), bad_(false) {}

        void loadFile() {
            checkStatus();
            data_.clear();
            bad_ = false;
            if (!exists()) {
                XLOG::d.t("{} is absent, return", path_.u8string());
                return;
            }

            auto raw_data = cma::tools::ReadFileInVector(path_.wstring());
            if (raw_data.has_value()) {
                data_ = wtools::ConditionallyConvertFromUTF16(raw_data.value());
                checkData();
                return;
            }
        }

        bool exists() const { return exists_; }
        bool bad() const { return bad_; }
        bool changed() const { return last_loaded_time_ != timestamp_; }
        const std::string& data() const { return data_; }
        auto timestamp() const { return timestamp_; }

        std::filesystem::path path_;

    private:
        std::string data_;
        // verifies exists and timestamp
        void checkStatus() {
            namespace fs = std::filesystem;
            std::error_code ec;
            exists_ = fs::exists(path_, ec);
            if (exists_)
                timestamp_ = fs::last_write_time(path_, ec);
            else
                timestamp_ = timestamp_.min();
        }

        // try to load data as yaml
        void checkData() {
            try {
                auto yaml = YAML::Load(data_);
                if (!yaml.IsDefined()) {
                    XLOG::l("Cannot load cfg '{}'", path_.u8string());
                    data_.clear();
                }
            } catch (const std::exception& e) {
                XLOG::l(XLOG::kBp)(
                    XLOG_FLINE + " exception in the yaml file: '{}'", e.what());
                bad_ = true;
            } catch (...) {
                XLOG::l(XLOG::kBp)(XLOG_FLINE + " exception bad");
                bad_ = true;
            }
        }

        std::filesystem::file_time_type last_loaded_time_;
        bool exists_;
        bool bad_;
        std::filesystem::file_time_type timestamp_;
    };

public:
    void initAll(const std::wstring& ServiceValidName,  // look in registry
                 const std::wstring& RootFolder,        // look in disk
                 const std::wstring& AgentDataFolder);  // look in disk

    void cleanAll();

    // not so heavy operation, use free
    // #TODO probably replace with shared_ptr
    YAML::Node getConfig() const noexcept {
        std::lock_guard lk(lock_);
        if (ok_) return yaml_;

        return {};
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

    bool isGenerated() const { return generated_; }
    bool isOk() const { return ok_; }

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
        return folders_.getCache();
    }

    auto getStateDir() const {
        std::lock_guard lk(lock_);
        return folders_.getState();
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

    auto getHostName() const {
        std::lock_guard lk(lock_);
        return host_name_;
    }

    auto getCwd() const {
        std::lock_guard lk(lock_);
        return cwd_;
    }

    auto getLogFileDir() const {
        std::lock_guard lk(lock_);
        return logfile_dir_;
    }

    auto getMsiExecPath() const {
        std::lock_guard lk(lock_);
        return path_to_msi_exec_;
    }

    size_t getBackupLogMaxSize() const noexcept { return backup_log_max_size_; }

    int getBackupLogMaxCount() const noexcept { return backup_log_max_count_; }

    void setLogFileDir(const std::wstring& Path) {
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
    LoadCfgStatus loadAggregated(const std::wstring& config_filename,
                                 YamlCacheOp cache_op);

    enum class Combine { overwrite, merge };
    static bool smartMerge(YAML::Node Target, YAML::Node Src, Combine combine);

    // THIS IS ONLY FOR TESTING
    bool loadDirect(const std::filesystem::path& FullPath);

private:
    std::vector<YamlData> buildYamlData(
        const std::wstring& ConfigFileName) const noexcept;
    void loadYamlDataWithMerge(YAML::Node Config,
                               const std::vector<YamlData>& Yd);
    // LOOOONG operation
    // when failed old config retained
    void initEnvironment();
    std::vector<std::filesystem::path>
        exe_command_paths_;  // root/utils, root/plugins etc
    std::vector<std::filesystem::path> config_dirs_;  // root and data

    details::Folders folders_;

    std::string host_name_;
    std::wstring cwd_;
    std::wstring logfile_dir_;

    std::wstring path_to_msi_exec_;

    // #TODO
    void GenerateDefaultConfig() {}
    mutable std::mutex lock_;

    YAML::Node yaml_;

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

    std::atomic<int> backup_log_max_count_ = kBackupLogMaxCount;
    std::atomic<size_t> backup_log_max_size_ = kBackupLogMaxSize;

#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class StartTest;
    FRIEND_TEST(StartTest, CheckStatus);
#endif
};
extern ConfigInfo G_ConfigInfo;

}  // namespace details
}  // namespace cma::cfg
