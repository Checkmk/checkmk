//
//
// Support for the Windows Agent  modules
//
//

#pragma once

#include <yaml-cpp/yaml.h>

#include <filesystem>
#include <string>

namespace cma::cfg::modules {
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

    [[nodiscard]] bool isModuleFile(const std::filesystem::path& file) const
        noexcept;

private:
    void reset() noexcept;
    std::string name_;
    std::vector<std::string> exts_;
    std::wstring exec_;
    std::string dir_;

#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class Modules;
    FRIEND_TEST(ModulesTest, Loader);
    FRIEND_TEST(ModulesTest, Internal);
#endif
};

[[nodiscard]] std::vector<Module> LoadFromConfig(const YAML::Node& yaml);

enum class InstallMode { normal, force };

class ModuleCommander {
public:
    void readConfig(YAML::Node& node);
    int findModuleFiles(const std::filesystem::path& root);
    void installModules(const std::filesystem::path& root,
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
    bool isBelongsToModules(const std::filesystem::path& file) const noexcept;
    bool installModule(const Module& module, const std::filesystem::path& root,
                       const std::filesystem::path& user,
                       InstallMode mode) const;

    static bool uninstallModuleZip(const std::filesystem::path& file,
                                   const std::filesystem::path& mod_root);

    static bool removeContentByTargetDir(
        const std::vector<std::wstring>& content,
        const std::filesystem::path& target_dir);

    static bool createFileForTargetDir(const std::filesystem::path& module_dir,
                                       const std::filesystem::path& target_dir);

    std::vector<std::filesystem::path> files_;
    std::vector<Module> modules_;
#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class ModuleCommanderTest;
    FRIEND_TEST(ModuleCommanderTest, ReadConfig);
    FRIEND_TEST(ModuleCommanderTest, FindModules);
    FRIEND_TEST(ModuleCommanderTest, InstallModules);
    FRIEND_TEST(ModuleCommanderTest, Internal);
#endif
};

}  // namespace cma::cfg::modules
