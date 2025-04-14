//
//
// Support for the Windows Agent  modules
//
//

#include "stdafx.h"

#include "wnx/modules.h"

#include <fmt/format.h>
#include <fmt/xchar.h>

#include <filesystem>
#include <fstream>
#include <ranges>
#include <string>

#include "common/cfg_info.h"
#include "common/wtools.h"
#include "tools/_misc.h"
#include "tools/_process.h"
#include "wnx/cfg.h"
#include "wnx/cma_core.h"
#include "wnx/logger.h"
#include "wnx/zip.h"

using namespace std::literals;
namespace fs = std::filesystem;
namespace rs = std::ranges;

namespace cma::cfg::modules {

void Module::reset() noexcept {
    name_.clear();
    exts_.clear();
    exec_.clear();
    dir_.clear();
    package_.clear();
    bin_.clear();
}

void Module::runPostInstall() const {
    fs::path work_dir = cfg::GetUserDir();
    work_dir /= dir();
    auto script_path = work_dir / post_install_script_name;
    if (std::error_code ec; fs::exists(script_path, ec)) {
        auto success =
            tools::RunCommandAndWait(script_path.wstring(), work_dir.wstring());
        XLOG::l.i("The command '{}' is {}", script_path,
                  success ? "successful" : "failed");
    }
}

fs::path Module::findPackage(const fs::path &backup_dir) const noexcept {
    try {
        auto file = backup_dir / (name() + std::string{kExtension});
        if (fs::exists(file) && fs::is_regular_file(file) &&
            fs::file_size(file) > 0) {
            return file;
        }

        XLOG::d.i("Module '{}' has no package installed, this is normal",
                  name());

    } catch (const std::exception &e) {
        XLOG::d.i(
            "Module '{}' has no package installed, this is normal, exception '{}'",
            name(), e);
    }
    return {};
}

fs::path Module::findBin(const fs::path &modules_dir) const noexcept {
    try {
        fs::path actual_dir = modules_dir.parent_path() / dir();
        fs::path default_dir = modules_dir / name();

        // default must exist
        if (!fs::exists(default_dir) || !fs::is_directory(default_dir)) {
            XLOG::d("Module '{}' has no work folder, this is bad", name());
            return {};
        }

        // check for actual
        std::error_code ec;
        if (fs::exists(actual_dir) && fs::is_directory(actual_dir) &&
            !fs::equivalent(default_dir, actual_dir, ec)) {
            // check symbolic link, actual is not the same as default
            XLOG::d("Module '{}' has predefined work folder", name());
        }
        auto table = tools::SplitString(exec(), L" ");

        auto bin = actual_dir / table[0];
        if (!fs::exists(bin) || !fs::is_regular_file(bin)) {
            XLOG::d("Module '{}' has no bin, this is bad", name());
            return {};
        }

        return bin;
    } catch (const std::exception &e) {
        XLOG::d("Module '{}' has no work folder, this is bad, exception '{}'",
                name(), e);
    }

    return {};
}

bool ModuleCommander::IsQuickReinstallAllowed() noexcept {
    const auto enabled_in_config =
        GetVal(groups::kModules, vars::kModulesQuickReinstall, true);
    return cfg::g_quick_module_reinstall_allowed && enabled_in_config;
}

bool Module::prepareToWork(const fs::path &backup_dir,
                           const fs::path &modules_dir) {
    package_ = findPackage(backup_dir);
    if (package_.empty()) {
        XLOG::d("Module '{}' has no package in backup dir '{}'", name(),
                backup_dir);
        return false;
    }

    bin_ = findBin(modules_dir);
    if (bin_.empty()) {
        XLOG::d("Module '{}' has no bin in modules dir '{}'", name(),
                modules_dir);
        return false;
    }
    runPostInstall();
    XLOG::l.i("Module '{}' is prepared to work with bin '{}'", name(), bin_);
    return true;
}

namespace {
/// extracts usual extension and unusual, e.g. ".checkmk.py"
std::string ExtractExtension(const fs::path &script) {
    if (!script.has_extension()) {
        return std::string{kNoExtension};
    }

    fs::path s{script};
    s.replace_extension("");
    return wtools::ToUtf8(s.extension().wstring() +
                          script.extension().wstring());
}
}  // namespace

bool Module::isMyScript(const fs::path &script) const noexcept {
    try {
        fs::path double_extension{ExtractExtension(script)};

        auto short_extension{
            wtools::ToUtf8(double_extension.extension().wstring())};
        if (rs::any_of(exts_, [&short_extension](const std::string &ext) {
                return tools::IsEqual(short_extension, ext);
            })) {
            return true;
        }

        if (rs::any_of(exts_, [&double_extension](const std::string &ext) {
                return tools::IsEqual(
                    wtools::ToUtf8(double_extension.wstring()), ext);
            })) {
            return true;
        }

    } catch (const std::exception &e) {
        XLOG::l(XLOG_FUNC + ": Exception '{}'", e);
    }

    return false;
}

// To remove owned extension if usage of the module is forbidden in config
void Module::removeExtension(std::string_view ext) {
    auto [a, b] = rs::remove_if(
        exts_, [ext](const std::string &cur_ext) { return cur_ext == ext; });

    exts_.erase(a, b);
}

std::wstring Module::buildCommandLineForced(
    const fs::path &script) const noexcept {
    try {
        if (bin().empty()) {
            return {};
        }
        const auto actual_dir = fs::path{GetUserDir()} / dir();
        return fmt::format(fmt::runtime((actual_dir / exec()).wstring()),
                           script.wstring());
    } catch (const std::exception &e) {
        XLOG::d("can't build valid command line for '{}', exception is '{}'",
                name(), e);
    }

    return {};
}

std::wstring Module::buildCommandLine(const fs::path &script) const noexcept {
    return isMyScript(script) ? buildCommandLineForced(script) : std::wstring{};
}

[[nodiscard]] bool Module::isModuleZip(const fs::path &file) const noexcept {
    try {
        return tools::IsEqual(name() + std::string(kExtension),
                              wtools::ToUtf8(file.wstring()));
    } catch (const std::exception &e) {
        XLOG::l("Failed something in isModuleFile '{}'", e);
        return false;
    }
}

// Table to keep logic pairs of 'system tool' and its file extension
static const std::vector<StringViewPair> g_system_extensions = {
    {cfg::vars::kModulesPython, ".py"sv}};

// API
[[nodiscard]] std::vector<StringViewPair>
ModuleCommander::GetSystemExtensions() {
    return g_system_extensions;
}

[[nodiscard]] std::vector<Module> LoadFromConfig(const YAML::Node &yaml) {
    try {
        auto module_yaml = yaml[groups::kModules];
        if (!GetVal(module_yaml, vars::kEnabled, true)) {
            return {};
        }

        // gather all modules in the table
        std::vector<Module> vec;
        auto module_array =
            GetArray<YAML::Node>(module_yaml, vars::kModulesTable);
        int index = 0;
        for (const auto &module_node : module_array) {
            Module m;
            ++index;
            if (!m.loadFrom(module_node) || !m.valid()) {
                XLOG::l.w("Skip module {}", index - 1);
                continue;
            }

            if (rs::any_of(vec, [&m](const Module &vec_m) {
                    return vec_m.name() == m.name();
                })) {
                XLOG::l.w("Skip module {} with duplicated name '{}'", index - 1,
                          m.name());
                continue;
            }

            vec.push_back(m);
        }

        XLOG::l.i("Processed [{}] module(s)", vec.size());
        return vec;

    } catch (const std::exception &e) {
        XLOG::l("Failed processing modules '{}'", e);
    }

    return {};
}

[[nodiscard]] bool Module::loadFrom(const YAML::Node &node) {
    try {
        name_ = node[vars::kModulesName].as<std::string>();
        exec_ =
            wtools::ConvertToUtf16(node[vars::kModulesExec].as<std::string>());
        exts_ = GetArray<std::string>(node[vars::kModulesExts]);

        // dir is optional
        auto dir = cfg::GetVal(node, vars::kModulesDir,
                               std::string{defaults::kModulesDir});
        if (dir.empty()) {
            dir = std::string{defaults::kModulesDir};
        }

        dir_ = fmt::format(fmt::runtime(dir), name());

    } catch (const std::exception &e) {
        XLOG::l("failed loading module '{}'", e);
        reset();
        return false;
    }

    if (name().empty() || name() == "null") {
        XLOG::l("Name is absent or not valid");
        reset();
        return false;
    }
    return true;
}

// internal API, should not be called directly
// scans all modules and remove form each corresponding extension if
// usage of the modules defined as 'system'
void ModuleCommander::removeSystemExtensions(YAML::Node &node) {
    try {
        auto m = node[groups::kModules];

        for (const auto &[name, ext] : ModuleCommander::GetSystemExtensions()) {
            auto system =
                GetVal(m, name, std::string(defaults::kModuleUsageDefaultMode));
            if (system == values::kModuleUsageSystem) {
                for (auto &module_node : modules_) {
                    module_node.removeExtension(ext);
                }
            }
        }
    } catch (const std::exception &e) {
        XLOG::l("Not possible to find modules.*** '{}'", e);
    }
}

void ModuleCommander::readConfig(YAML::Node &node) {
    modules_ = LoadFromConfig(node);
    removeSystemExtensions(node);
}

int ModuleCommander::findModuleFiles(const fs::path &root) {
    files_.clear();
    auto src_root = root / dirs::kFileInstallDir;
    for (const auto &m : modules_) {
        auto name = m.name();
        name += kExtension;
        std::error_code ec;
        if (fs::exists(src_root / name, ec)) {
            files_.emplace_back(src_root / name);
            XLOG::l.i("Module '{}' is added to the list", files_.back());
        }
    }

    return static_cast<int>(files_.size());
}

bool CreateDir(const fs::path &mod) noexcept {
    try {
        std::error_code ec;
        fs::create_directories(mod, ec);
        if (!fs::exists(mod, ec) || !fs::is_directory(mod, ec)) {
            XLOG::l("Failed to create folder '{}' error is '{}'", mod,
                    ec.message());
            return false;
        }
    } catch (std::exception &e) {
        XLOG::l("Failed to create folders to install modules '{}'", e);
        return false;
    }

    return true;
}

PathVector ModuleCommander::ScanDir(const fs::path &dir) noexcept {
    PathVector vec;
    for (const auto &p : fs::directory_iterator(dir)) {
        std::error_code ec;
        auto const &path = p.path();
        if (fs::is_directory(path, ec) || !fs::is_regular_file(path, ec) ||
            path.wstring().empty()) {
            continue;
        }

        vec.emplace_back(path);
    }

    return vec;
}

// check that name of the file is found among module names
bool ModuleCommander::isBelongsToModules(const fs::path &file) const noexcept {
    return rs::any_of(modules_, [file](const Module &m) {
        try {
            return tools::IsEqual(m.name() + std::string(kExtension),
                                  wtools::ToUtf8(file.filename().wstring()));
        } catch (const std::exception &e) {
            XLOG::l("Exception '{}' at ModuleCommander", e);
            return false;
        }
    });
}

bool ModuleCommander::UninstallModuleZip(const fs::path &file,
                                         const fs::path &mod_root) {
    std::error_code ec;
    if (!fs::exists(file, ec)) {
        XLOG::d.i("'{}' is absent, no need to uninstall", file);
        return false;
    }

    auto name = file.filename();
    name.replace_extension();
    auto target_dir = mod_root / name;

    auto count = wtools::KillProcessesByDir(target_dir);
    XLOG::d.i("Killed [{}] processes from dir '{}'", count, target_dir);

    if (IsQuickReinstallAllowed()) {
        try {
            XLOG::l.i("Quick uninstall allowed");
            // prepare
            fs::path move_location{GetMoveLocation(file)};
            fs::remove_all(move_location, ec);
            fs::create_directories(move_location);

            // execute
            fs::rename(target_dir, move_location / target_dir.filename());
            fs::rename(file, move_location / file.filename());
            return true;
        } catch (const fs::filesystem_error &e) {
            // fallback
            XLOG::l(
                "Exception during quick module uninstall '{}' files: '{}' '{}', falling back to remove.",
                e.what(), e.path1(), e.path2());
        }
    }

    fs::remove_all(target_dir, ec);
    fs::remove(file, ec);

    return true;
}

void ModuleCommander::CreateBackupFolder(const fs::path &user) {
    auto mod_backup = ModuleCommander::GetModBackup(user);
    std::error_code ec;
    if (fs::exists(mod_backup, ec)) {
        return;
    }
    XLOG::d.i("creating backup folder for modules installing '{}'", mod_backup);
    fs::create_directories(ModuleCommander::GetModBackup(user), ec);
}

bool ModuleCommander::BackupModule(const fs::path &module_file,
                                   const fs::path &backup_file) {
    std::error_code ec;
    if (fs::copy_file(module_file, backup_file,
                      fs::copy_options::overwrite_existing, ec)) {
        return true;
    }

    XLOG::l.crit("Error [{}] '{}' installing new mod", ec.value(),
                 ec.message());
    return false;
}

bool ModuleCommander::PrepareCleanTargetDir(const fs::path &mod_dir) {
    if (mod_dir.u8string().size() < kResonableDirLengthMin) {
        XLOG::l("target_dir '{}'is too short when installing new module '{}'",
                mod_dir);
        return false;
    }
    std::error_code ec;
    fs::remove_all(mod_dir, ec);
    fs::create_directories(mod_dir, ec);

    return true;
}

std::vector<std::string> ModuleCommander::getExtensions() const {
    std::vector<std::string> result;

    for (const auto &m : modules_) {
        auto exts = m.exts();
        result.insert(result.end(), exts.begin(), exts.end());
    }

    return result;
}
namespace {
std::vector<char> ReadFileBeginning(const fs::path &name, size_t count) {
    std::ifstream f;
    f.exceptions(std::ifstream::failbit | std::ifstream::badbit);
    try {
        f.open(name, std::ios::binary);
        std::vector<char> data;
        data.resize(count);
        f.read(data.data(), static_cast<std::streamsize>(count));
        f.close();

        return data;
    } catch (const std::ifstream::failure &e) {
        XLOG::l("Exception '{}' reading file '{}'", e.what(), name);
    }

    return {};
}

fs::path GetBackupFileName(const Module &mod, const fs::path &user) {
    auto backup_file = ModuleCommander::GetModBackup(user) / mod.name();
    backup_file += kExtension.data();
    return backup_file;
}

fs::path GetModuleFileName(const Module &mod, const fs::path &root) {
    auto module_file = root / dirs::kFileInstallDir / mod.name();
    module_file += kExtension.data();
    return module_file;
}

}  // namespace

std::optional<ModuleCommander::UninstallStore>
ModuleCommander::GetUninstallStore(const fs::path &file) {
    constexpr size_t min_size{1024};

    auto path = GetMoveLocation(file);
    auto expected_file = path / file.filename();
    auto expected_dir{expected_file};
    expected_dir.replace_extension();

    std::error_code ec;
    if (!fs::exists(expected_file, ec)) {
        XLOG::d.i("Quick installation not possible: not found '{}'",
                  expected_file);
        return {};
    }

    if (!fs::is_directory(expected_dir, ec)) {
        XLOG::d.i("Quick installation not possible: not found '{}'",
                  expected_dir);
        return {};
    }

    if (fs::file_size(file) != fs::file_size(expected_file) ||
        fs::file_size(file) < min_size) {
        XLOG::d.i(
            "Quick installation not possible: sizes are not the same or strange for '{}' and '{}' sizes are [{}] [{}]",
            expected_file, file, fs::file_size(expected_file),
            fs::file_size(file));
        return {};
    }

    auto file_data = ReadFileBeginning(file, min_size);
    auto expected_file_data = ReadFileBeginning(expected_file, min_size);
    if (!file_data.empty() && file_data == expected_file_data) {
        return UninstallStore{.base_ = path,
                              .package_file_ = expected_file,
                              .module_dir_ = expected_dir};
    }
    XLOG::d.i(
        "Quick installation not possible: files are not the same '{}' and '{}'",
        expected_file, file);
    return {};
}

bool ModuleCommander::TryQuickInstall(const Module &mod, const fs::path &root,
                                      const fs::path &user) {
    if (!ModuleCommander::IsQuickReinstallAllowed()) {
        XLOG::l.i("Quick reinstall is not allowed");
        return false;
    }

    auto uninstall_store = GetUninstallStore(GetModuleFileName(mod, root));
    if (!uninstall_store) {
        return false;
    }

    try {
        auto default_dir = GetModInstall(user) / mod.name();  // default
        XLOG::l.i("Starting quick reinstall");
        fs::remove_all(default_dir);
        fs::remove(default_dir);

        fs::rename(uninstall_store->package_file_,
                   GetBackupFileName(mod, user));
        fs::rename(uninstall_store->module_dir_, default_dir);
        XLOG::l.i("Quick reinstall is finished");

        return true;
    } catch (const fs::filesystem_error &e) {
        XLOG::l.i("Quick reinstall is failed '{}' file 1:'{}' file 2 '{}'",
                  e.what(), e.path1(), e.path2());
    }

    return false;
}

// #TODO - simplify the function
bool ModuleCommander::InstallModule(const Module &mod, const fs::path &root,
                                    const fs::path &user, InstallMode mode) {
    XLOG::l.i("Install module {}", mod.name());

    fs::path backup_file{GetBackupFileName(mod, user)};
    fs::path module_file{GetModuleFileName(mod, root)};

    std::error_code ec;
    if (!fs::exists(module_file, ec) || fs::file_size(module_file) == 0) {
        UninstallModuleZip(backup_file, GetModInstall(user));
        XLOG::l.i(
            "Installation of the module '{}' is not required, module file '{}'is "
            "absent or too short. Backup will be uninstalled",
            mod.name(), module_file);
        return false;
    }

    if (tools::AreFilesSame(backup_file, module_file) &&
        mode == InstallMode::normal) {
        XLOG::l.i(
            "Installation of the module '{}' is not required, module file '{}'is same",
            mod.name(), module_file);
        return false;
    }

    CreateBackupFolder(user);

    if (TryQuickInstall(mod, root, user)) {
        return true;
    }

    auto uninstalled = UninstallModuleZip(backup_file, GetModInstall(user));
    XLOG::d.i("The module in {} is {}", backup_file,
              uninstalled ? "uninstalled" : "failed to uninstall");

    if (!BackupModule(module_file, backup_file)) {
        XLOG::l("Can't backup module '{}': file '{}', backup '{}'", mod.name(),
                module_file, backup_file);
        return false;
    }

    fs::path default_dir = GetModInstall(user) / mod.name();  // default
    fs::path actual_dir = user / mod.dir();
    if (!PrepareCleanTargetDir(default_dir)) {
        return false;
    }

    if (tools::zip::Extract(backup_file.wstring(), actual_dir.wstring())) {
        fs::path postinstall{actual_dir};
        postinstall /= post_install_script_name;

        if (!fs::exists(postinstall, ec)) {
            XLOG::l.i("The module '{}' is absent", postinstall);
            return true;
        }
        auto success = tools::RunCommandAndWait(postinstall.wstring(),
                                                actual_dir.wstring());
        XLOG::l.i("The command '{}' is {}", postinstall,
                  success ? "successful" : "failed");

        return true;
    }

    XLOG::l("Extraction failed: removing backup file '{}' and default dir '{}'",
            backup_file.u8string(), default_dir.u8string());
    fs::remove(backup_file, ec);
    fs::remove_all(default_dir);

    return false;
}

void ModuleCommander::installModules(const fs::path &root, const fs::path &user,
                                     InstallMode mode) const {
    auto mod_root = GetModInstall(user);
    auto mod_backup = GetModBackup(user);
    if (!CreateDir(mod_root) || !CreateDir(mod_backup)) {
        return;
    }

    auto installed = ScanDir(mod_backup);

    // cleanup suspicious trash in modules dir, may left when we
    // changing modules names
    for (const auto &dir : installed) {
        if (!isBelongsToModules(dir)) {
            UninstallModuleZip(dir, mod_root);
        }
    }

    for (const auto &mod : modules_) {
        InstallModule(mod, root, user, mode);
    }
}

void ModuleCommander::moveModulesToStore(const fs::path &user) {
    auto mod_root = GetModInstall(user);
    auto mod_backup = GetModBackup(user);

    auto installed = ScanDir(mod_backup);

    for (const auto &dir : installed) {
        UninstallModuleZip(dir, mod_root);
    }
}

void ModuleCommander::InstallDefault(InstallMode mode) noexcept {
    try {
        auto root = GetRootDir();
        auto user = GetUserDir();
        auto yaml = GetLoadedConfig();
        XLOG::l.i("Reading module config {}",
                  mode == InstallMode::force ? "forced" : "normal");
        readConfig(yaml);
        XLOG::l.i("Finding modules");
        findModuleFiles(root);
        XLOG::l.i("Installing modules");
        installModules(root, user, mode);
        prepareToWork();
    } catch (const std::exception &e) {
        XLOG::l("Exception installing modules '{}'", e);
    }
}
void ModuleCommander::LoadDefault() noexcept {
    try {
        auto yaml = GetLoadedConfig();
        XLOG::l.i("Loading module config");
        readConfig(yaml);
        prepareToWork();
    } catch (const std::exception &e) {
        XLOG::l("Exception loading modules config '{}'", e);
    }
}

void ModuleCommander::prepareToWork() {
    auto mod_backup = GetModBackup(cfg::GetUserDir());
    auto mod_root = GetModInstall(cfg::GetUserDir());

    rs::for_each(modules_,
                 [&](auto &m) { m.prepareToWork(mod_backup, mod_root); });
}

bool ModuleCommander::isModuleScript(std::string_view filename) {
    return rs::any_of(modules_,
                      [&](const auto &m) { return m.isMyScript(filename); });
}

std::wstring ModuleCommander::buildCommandLine(
    std::string_view filename) const {
    for (const auto &m : modules_) {
        if (m.isMyScript(filename)) {
            return m.buildCommandLine(fs::path{filename});
        }
    }
    return {};
}

fs::path ModuleCommander::GetMoveLocation(const fs::path &module_file) {
    return fs::temp_directory_path() /
           (std::string{g_module_uninstall_path} +
            (GetModus() == Modus::service ? "_srv" : "_app")) /
           module_file.filename();
}

}  // namespace cma::cfg::modules
