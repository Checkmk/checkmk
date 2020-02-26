//
//
// Support for the Windows Agent  modules
//
//

#pragma once

#include <yaml-cpp/yaml.h>

#include <filesystem>
#include <string>

#include "cma_core.h"

namespace cma::cfg::modules {
constexpr std::string_view kNoExtension = ".";
constexpr std::string_view kExtension = ".zip";
constexpr std::string_view kTargetDir = ".target.dir";  // dir for installation
constexpr int kResonableDirLengthMin = 20;

class Module {
public:
    // loader
    [[nodiscard]] bool loadFrom(const YAML::Node& node);

    // accessors
    [[nodiscard]] bool valid() const noexcept { return !name_.empty(); }
    [[nodiscard]] auto name() const noexcept { return name_; }
    [[nodiscard]] auto exts() const noexcept { return exts_; }
    [[nodiscard]] auto exec() const noexcept { return exec_; }
    [[nodiscard]] auto dir() const noexcept { return dir_; }

    [[nodiscard]] auto bin() const noexcept { return bin_; }
    [[nodiscard]] auto zip() const noexcept { return zip_; }

    [[nodiscard]] bool isModuleZip(const std::filesystem::path& file) const
        noexcept;

    // finds the zip and executable
    bool prepareToWork(const std::filesystem::path& backup_dir,
                       const std::filesystem::path& modules_dir);

    //
    bool isMyScript(const std::filesystem::path& script) const noexcept;
    std::wstring buildCommandLine(const std::filesystem::path& script) const
        noexcept;

    // makes command line with script, if bin_ is empty returns nothing
    std::wstring buildCommandLineForced(
        const std::filesystem::path& script) const noexcept;

private:
    void reset() noexcept;
    std::string name_;
    std::vector<std::string> exts_;
    std::wstring exec_;
    std::string dir_;

    std::filesystem::path bin_;  // executable from the exec:
    std::filesystem::path zip_;  // path to valid zip file

    std::filesystem::path findZip(const std::filesystem::path& backup_dir) const
        noexcept;

    std::filesystem::path findBin(
        const std::filesystem::path& modules_dir) const noexcept;

#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class ModulesTest;
    FRIEND_TEST(ModulesTest, Loader);
    FRIEND_TEST(ModulesTest, Internal);
    FRIEND_TEST(ModulesTest, PrepareToWork);
    FRIEND_TEST(ModulesTest, IsMyScript);

    friend class ModuleCommanderTest;
    FRIEND_TEST(ModuleCommanderTest, InstallModules);

#endif
};

[[nodiscard]] std::vector<Module> LoadFromConfig(const YAML::Node& yaml);

enum class InstallMode { normal, force };

void Install(InstallMode mode) noexcept;

class ModuleCommander {
public:
    void LoadDefault() noexcept;
    void InstallDefault(InstallMode mode) noexcept;
    void readConfig(YAML::Node& node);

    void prepareToWork();
    bool isModuleScript(const std::string_view filename);
    std::wstring buildCommandLine(const std::string_view filename);

    int findModuleFiles(const std::filesystem::path& root);
    void installModules(const std::filesystem::path& root,
                        const std::filesystem::path& user,
                        InstallMode mode) const;

    static std::filesystem::path GetModBackup(
        const std::filesystem::path& user) {
        return user / dirs::kUserInstallDir / dirs::kInstalledModules;
    }

    static std::filesystem::path GetModInstall(
        const std::filesystem::path& user) {
        return user / dirs::kUserModules;
    }

private:
    // internals static API
    static bool InstallModule(const Module& module,
                              const std::filesystem::path& root,
                              const std::filesystem::path& user,
                              InstallMode mode);

    // returns true when changes had been made
    static bool UninstallModuleZip(const std::filesystem::path& file,
                                   const std::filesystem::path& mod_root);

    static bool RemoveContentByTargetDir(
        const std::vector<std::wstring>& content,
        const std::filesystem::path& target_dir);

    static bool CreateFileForTargetDir(const std::filesystem::path& module_dir,
                                       const std::filesystem::path& target_dir);

    static bool BackupModule(const std::filesystem::path& module_file,
                             const std::filesystem::path& backup_file);
    static bool PrepareCleanTargetDir(const std::filesystem::path& mod_dir);
    static void CreateBackupFolder(const std::filesystem::path& user);
    // internal API
    bool isBelongsToModules(const std::filesystem::path& file) const noexcept;
    static PathVector ScanDir(const std::filesystem::path& dir) noexcept;
    std::vector<std::filesystem::path> files_;
    std::vector<Module> modules_;
#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class ModuleCommanderTest;
    FRIEND_TEST(ModuleCommanderTest, FindModules);
    FRIEND_TEST(ModuleCommanderTest, InstallModules);
    FRIEND_TEST(ModuleCommanderTest, Internal);
    FRIEND_TEST(ModuleCommanderTest, LowLevelFs);
    FRIEND_TEST(ModuleCommanderTest, PrepareToWork2);

    friend class ModuleCommander;
    FRIEND_TEST(ModuleCommander, ReadConfig);
#endif
};

}  // namespace cma::cfg::modules
