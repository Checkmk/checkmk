// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

//
//
// Support for the Windows Agent  modules
//
//

#pragma once

#include <yaml-cpp/yaml.h>

#include <filesystem>
#include <string>
#include <string_view>

#include "cma_core.h"

namespace cma::cfg::modules {
constexpr std::string_view kNoExtension = ".";
constexpr std::string_view kExtension = ".cab";
constexpr int kResonableDirLengthMin = 20;
constexpr std::string_view g_module_uninstall_path =
    "checkmk_uninstalled_modules";

class Module {
public:
    // loader
    [[nodiscard]] bool loadFrom(const YAML::Node &node);

    // accessors
    [[nodiscard]] bool valid() const noexcept { return !name_.empty(); }
    [[nodiscard]] auto name() const noexcept { return name_; }
    [[nodiscard]] auto exts() const noexcept { return exts_; }
    [[nodiscard]] auto exec() const noexcept { return exec_; }
    [[nodiscard]] auto dir() const noexcept { return dir_; }

    [[nodiscard]] auto bin() const noexcept { return bin_; }
    [[nodiscard]] auto package() const noexcept { return package_; }

    [[nodiscard]] bool isModuleZip(
        const std::filesystem::path &file) const noexcept;

    // finds the package and executable
    bool prepareToWork(const std::filesystem::path &backup_dir,
                       const std::filesystem::path &modules_dir);

    //
    bool isMyScript(const std::filesystem::path &script) const noexcept;
    std::wstring buildCommandLine(
        const std::filesystem::path &script) const noexcept;

    // makes command line with script, if bin_ is empty returns nothing
    std::wstring buildCommandLineForced(
        const std::filesystem::path &script) const noexcept;

    void removeExtension(std::string_view ext);

private:
    void runPostInstall();

    void reset() noexcept;
    std::string name_;
    std::vector<std::string> exts_;
    std::wstring exec_;
    std::string dir_;

    std::filesystem::path bin_;      // executable from the exec:
    std::filesystem::path package_;  // path to valid package file

    std::filesystem::path findPackage(
        const std::filesystem::path &backup_dir) const noexcept;

    std::filesystem::path findBin(
        const std::filesystem::path &modules_dir) const noexcept;

#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class ModulesTest;
    FRIEND_TEST(ModulesTest, Loader);
    FRIEND_TEST(ModulesTest, Internal);
    FRIEND_TEST(ModulesTest, PrepareToWork);
    FRIEND_TEST(ModulesTest, IsMyScript);

    friend class ModuleCommanderTest;
    FRIEND_TEST(ModuleCommanderTest, InstallModulesIntegration);

#endif
};

[[nodiscard]] std::vector<Module> LoadFromConfig(const YAML::Node &yaml);

enum class InstallMode { normal, force };

using StringViewPair = std::pair<std::string_view, std::string_view>;
constexpr std::string_view post_install_script_name{"postinstall.cmd"};

class ModuleCommander {
public:
    struct UninstallStore {
        std::filesystem::path base_;
        std::filesystem::path package_file_;
        std::filesystem::path module_dir_;
    };
    void LoadDefault() noexcept;
    void InstallDefault(InstallMode mode) noexcept;
    void readConfig(YAML::Node &node);

    static bool IsQuickReinstallAllowed();

    void prepareToWork();
    bool isModuleScript(std::string_view filename);
    std::wstring buildCommandLine(std::string_view filename);

    int findModuleFiles(const std::filesystem::path &root);
    void installModules(const std::filesystem::path &root,
                        const std::filesystem::path &user,
                        InstallMode mode) const;

    static void moveModulesToStore(const std::filesystem::path &user);

    std::vector<std::string> getExtensions() const;

    static std::filesystem::path GetModBackup(
        const std::filesystem::path &user) {
        return user / dirs::kUserInstallDir / dirs::kInstalledModules;
    }

    static std::filesystem::path GetModInstall(
        const std::filesystem::path &user) {
        return user / dirs::kUserModules;
    }

    [[nodiscard]] static std::vector<StringViewPair> GetSystemExtensions();

    /// \brief Returns path in the %temp% where content of module will be moved
    static std::filesystem::path GetMoveLocation(
        const std::filesystem::path &module_file);

private:
    void removeSystemExtensions(YAML::Node &node);

    // internals static API
    static bool TryQuickInstall(const Module &mod,
                                const std::filesystem::path &root,
                                const std::filesystem::path &user);

    static bool InstallModule(const Module &mod,
                              const std::filesystem::path &root,
                              const std::filesystem::path &user,
                              InstallMode mode);

    // returns true when changes had been made
    static bool UninstallModuleZip(const std::filesystem::path &file,
                                   const std::filesystem::path &mod_root);

    // \brief Validates that default move dir contains good module
    static std::optional<UninstallStore> GetUninstallStore(
        const std::filesystem::path &file);

    static bool BackupModule(const std::filesystem::path &module_file,
                             const std::filesystem::path &backup_file);
    static bool PrepareCleanTargetDir(const std::filesystem::path &mod_dir);
    static void CreateBackupFolder(const std::filesystem::path &user);
    // internal API
    bool isBelongsToModules(const std::filesystem::path &file) const noexcept;
    static PathVector ScanDir(const std::filesystem::path &dir) noexcept;
    std::vector<std::filesystem::path> files_;
    std::vector<Module> modules_;
#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class ModuleCommanderTest;
    FRIEND_TEST(ModuleCommanderTest, FindModules);
    FRIEND_TEST(ModuleCommanderTest, InstallModulesIntegration);
    FRIEND_TEST(ModuleCommanderTest, Internal);
    FRIEND_TEST(ModuleCommanderTest, LowLevelFs);
    FRIEND_TEST(ModuleCommanderTest, PrepareToWork2);

    friend class ModuleCommander;
    FRIEND_TEST(ModuleCommander, ReadConfig);
#endif
};

}  // namespace cma::cfg::modules
