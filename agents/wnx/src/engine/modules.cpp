//
//
// Support for the Windows Agent  modules
//
//

#include "stdafx.h"

#include "modules.h"

#include <fmt/format.h>

#include <filesystem>
#include <string>

#include "cfg.h"
#include "cma_core.h"
#include "common/cfg_info.h"
#include "common/wtools.h"
#include "logger.h"
#include "tools/_misc.h"
#include "zip.h"

using namespace std::literals;

namespace cma::cfg::modules {

void Module::reset() noexcept {
    name_.clear();
    exts_.clear();
    exec_.clear();
    dir_.clear();
    zip_.clear();
    bin_.clear();
}

std::filesystem::path Module::findZip(
    const std::filesystem::path &backup_dir) const noexcept {
    namespace fs = std::filesystem;
    try {
        auto zip = backup_dir / (name() + std::string{kExtension});
        if (fs::exists(zip) && fs::is_regular_file(zip) &&
            fs::file_size(zip) > 0)
            return zip;

        XLOG::d.i("Module '{}' has no zip installed, this is normal", name());

    } catch (const std::exception &e) {
        XLOG::d.i(
            "Module '{}' has no zip installed, this is normal, exception '{}'",
            name(), e.what());
    }
    return {};
}

std::filesystem::path Module::findBin(
    const std::filesystem::path &modules_dir) const noexcept {
    namespace fs = std::filesystem;
    fs::path actual_dir = modules_dir.parent_path() / dir();

    try {
        fs::path default_dir = modules_dir / name();

        // default must exist
        if (!fs::exists(default_dir) || !fs::is_directory(default_dir)) {
            XLOG::d("Module '{}' has no work folder, this is bad", name());
            return {};
        }

        // check for actual
        if (fs::exists(actual_dir) && fs::is_directory(actual_dir) &&
            !fs::equivalent(default_dir, actual_dir)) {
            // check symbolic link, actual is not the same as default
            XLOG::d("Module '{}' has predefined work folder", name());
        }
        auto table = cma::tools::SplitString(exec(), L" ");

        auto bin = actual_dir / table[0];
        if (!fs::exists(bin) || !fs::is_regular_file(bin)) {
            XLOG::d("Module '{}' has no bin, this is bad", name());
            return {};
        }

        return bin;
    } catch (const std::exception &e) {
        XLOG::d("Module '{}' has no work folder, this is bad, exception '{}'",
                name(), e.what());
    }

    return {};
}

bool Module::prepareToWork(const std::filesystem::path &backup_dir,
                           const std::filesystem::path &modules_dir) {
    namespace fs = std::filesystem;

    // Find Zip
    zip_ = findZip(backup_dir);
    if (zip_.empty()) return false;

    bin_ = findBin(modules_dir);
    if (bin_.empty()) return false;

    XLOG::l.i("Module '{}' is prepared to work with bin '{}'", name(),
              bin_.u8string());
    return true;
}

bool Module::isMyScript(const std::filesystem::path &script) const noexcept {
    using namespace std::literals;
    try {
        std::string extension{script.has_extension()
                                  ? script.extension().u8string()
                                  : kNoExtension};

        if (std::any_of(std::begin(exts_), std::end(exts_),
                        [extension](const std::string &ext) {
                            return cma::tools::IsEqual(extension, ext);
                        }))
            return true;
    } catch (const std::exception &e) {
        XLOG::l(XLOG_FUNC + ": Exception '{}'", e.what());
    }

    return false;
}

// To remove owned extension if usage of the module is forbidden in config
void Module::removeExtension(std::string_view ext) {
    auto end = std::remove_if(
        exts_.begin(), exts_.end(),
        [ext](const std::string &cur_ext) { return cur_ext == ext; });

    exts_.erase(end, exts_.end());
}

std::wstring Module::buildCommandLineForced(
    const std::filesystem::path &script) const noexcept {
    try {
        if (bin().empty()) return {};
        auto actual_dir = std::filesystem::path{GetUserDir()} / dir();
        auto result =
            fmt::format((actual_dir / exec()).wstring(), script.wstring());
        return result;
    } catch (const std::exception &e) {
        XLOG::d("can't build valid command line for '{}', exception is '{}'",
                name(), e.what());
    }

    return {};
}

std::wstring Module::buildCommandLine(
    const std::filesystem::path &script) const noexcept {
    if (!isMyScript(script)) return {};

    return buildCommandLineForced(script);
}

[[nodiscard]] bool Module::isModuleZip(
    const std::filesystem::path &file) const noexcept {
    try {
        return tools::IsEqual(name() + std::string(kExtension),
                              file.u8string());
    } catch (const std::exception &e) {
        XLOG::l("Failed something in isModuleFile '{}'", e.what());
        return false;
    }
}

// Table to keep logic pairs of 'system tool' and its file extension
static const std::vector<StringViewPair> SystemExtensions = {
    {cma::cfg::vars::kModulesPython, ".py"sv}};

// API
[[nodiscard]] const std::vector<StringViewPair>
ModuleCommander::GetSystemExtensions() {
    return SystemExtensions;
}

[[nodiscard]] std::vector<Module> LoadFromConfig(const YAML::Node &yaml) {
    try {
        auto m = yaml[groups::kModules];

        // check enable
        auto enabled = GetVal(m, vars::kEnabled, true);
        if (!enabled) return {};

        // gather all modules in the table
        std::vector<Module> vec;
        auto module_array = GetArray<YAML::Node>(m, vars::kModulesTable);
        int index = 0;
        for (const auto &module_node : module_array) {
            Module m;
            ++index;
            if (!m.loadFrom(module_node) || !m.valid()) {
                XLOG::l.w("Skip module {}", index - 1);
                continue;
            }

            if (std::any_of(std::begin(vec), std::end(vec),
                            [m](const Module &vec_m) {
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
        XLOG::l("Failed processing modules '{}'", e.what());
        return {};
    }

    return {};
}

[[nodiscard]] bool Module::loadFrom(const YAML::Node &node) {
    try {
        name_ = node[vars::kModulesName].as<std::string>();
        exec_ =
            wtools::ConvertToUTF16(node[vars::kModulesExec].as<std::string>());
        exts_ = GetArray<std::string>(node[vars::kModulesExts]);

        // dir is optional
        auto dir = cma::cfg::GetVal(node, vars::kModulesDir,
                                    std::string{defaults::kModulesDir});
        if (dir.empty()) dir = std::string{defaults::kModulesDir};

        dir_ = fmt::format(dir, name());

    } catch (const std::exception &e) {
        XLOG::l("failed loading module '{}'", e.what());
        reset();
        return false;
    }

    if (name().empty()) {
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

        for (auto &sys_ex : ModuleCommander::GetSystemExtensions()) {
            auto system =
                GetVal(m, sys_ex.first,
                       std::string(defaults::kModuleUsageDefaultMode));
            if (system == values::kModuleUsageSystem) {
                for (auto &module_node : modules_) {
                    module_node.removeExtension(sys_ex.second);
                }
            }
        }
    } catch (const std::exception &e) {
        XLOG::l.i("Not possible to find modules.*** '{}'", e.what());
    }
}

void ModuleCommander::readConfig(YAML::Node &node) {
    modules_ = LoadFromConfig(node);
    removeSystemExtensions(node);
}

int ModuleCommander::findModuleFiles(const std::filesystem::path &root) {
    namespace fs = std::filesystem;
    files_.clear();
    auto src_root = root / dirs::kFileInstallDir;
    for (auto &m : modules_) {
        auto name = m.name();
        name += kExtension;
        std::error_code ec;
        if (fs::exists(src_root / name, ec)) {
            files_.emplace_back(src_root / name);
            XLOG::l.i("Module '{}' is added to the list",
                      files_.back().u8string());
        }
    }

    return static_cast<int>(files_.size());
}

bool CreateDir(const std::filesystem::path &mod) noexcept {
    namespace fs = std::filesystem;
    try {
        std::error_code ec;
        fs::create_directories(mod, ec);
        if (!fs::exists(mod, ec) || !fs::is_directory(mod, ec)) {
            XLOG::l("Failed to create folder '{}' error is '{}'",
                    mod.u8string(), ec.message());
            return false;
        }
    } catch (std::exception &e) {
        XLOG::l("Failed to create folders to install modules '{}'", e.what());
        return false;
    }

    return true;
}

PathVector ModuleCommander::ScanDir(const std::filesystem::path &dir) noexcept {
    namespace fs = std::filesystem;
    PathVector vec;
    for (auto &p : fs::directory_iterator(dir)) {
        std::error_code ec;
        auto const &path = p.path();
        if (fs::is_directory(path, ec)) continue;
        if (!fs::is_regular_file(path, ec)) continue;

        auto path_string = path.wstring();
        if (path_string.empty()) continue;

        vec.emplace_back(path);
    }

    return vec;
}

// check that name of the file is found among module names
bool ModuleCommander::isBelongsToModules(
    const std::filesystem::path &file) const noexcept {
    return std::any_of(
        std::begin(modules_), std::end(modules_), [file](const Module &m) {
            try {
                return tools::IsEqual(m.name() + std::string(kExtension),
                                      file.filename().u8string());
            } catch (const std::exception &e) {
                XLOG::l("Exception '{}' at ModuleCommander", e.what());
                return false;
            }
        });
}

// looks for the kTargetDir file in target_dir - this is symbolic link to
// folder for remove content
bool ModuleCommander::RemoveContentByTargetDir(
    const std::vector<std::wstring> &content,
    const std::filesystem::path &target_dir) {
    namespace fs = std::filesystem;
    std::error_code ec;
    if (!fs::exists(target_dir, ec)) return false;

    if (!fs::exists(target_dir / kTargetDir, ec)) return false;

    auto dir =
        tools::ReadFileInString((target_dir / kTargetDir).wstring().c_str());

    if (dir.has_value() && fs::exists(*dir, ec) && fs::is_directory(*dir, ec)) {
        if (dir->size() < kResonableDirLengthMin) {
            XLOG::l("The dir '{}' is suspicious, skipping", *dir);
            return false;
        }
        fs::path d{*dir};

        auto count = wtools::KillProcessesByDir(d);
        XLOG::l.i("Killed [{}] processes from dir '{}'", count, d.u8string());
        for (auto line : content) {
            fs::remove_all(d / line, ec);
        }

        return true;
    }

    return false;
}

bool ModuleCommander::CreateFileForTargetDir(
    const std::filesystem::path &module_dir,
    const std::filesystem::path &target_dir) {
    namespace fs = std::filesystem;

    try {
        if (target_dir.u8string().size() < kResonableDirLengthMin) {
            XLOG::l("suspicious dir '{}' to create link",
                    target_dir.u8string());
            return false;
        }

        if (module_dir.u8string().size() < kResonableDirLengthMin) {
            XLOG::l("suspicious dir '{}' to create link",
                    module_dir.u8string());
            return false;
        }

        std::error_code ec;
        fs::create_directories(module_dir);

        std::ofstream ofs(module_dir / kTargetDir);

        if (!ofs) {
            XLOG::l("Can't open file {} error {}",
                    (module_dir / kTargetDir).u8string(), GetLastError());
            return false;
        }

        ofs << target_dir.u8string();
        return true;
    } catch (const std::exception &e) {
        XLOG::l(XLOG_FUNC + " Exception '{}' when creating '{}'", e.what(),
                (module_dir / kTargetDir).u8string());
        return false;
    }
}

bool ModuleCommander::UninstallModuleZip(
    const std::filesystem::path &file, const std::filesystem::path &mod_root) {
    namespace fs = std::filesystem;
    std::error_code ec;
    if (!fs::exists(file, ec)) {
        XLOG::d.i("'{}' is absent, no need to uninstall", file.u8string());
        return false;
    }

    auto name = file.filename();
    name.replace_extension("");
    auto target_dir = mod_root / name;
    auto list = cma::tools::zip::List(file.wstring());
    bool relink = RemoveContentByTargetDir(list, target_dir);

    if (!relink) {
        auto count = wtools::KillProcessesByDir(target_dir);
        XLOG::l.i("Killed [{}] processes from dir '{}'", count,
                  target_dir.u8string());
    }

    fs::remove_all(target_dir, ec);
    fs::remove(file, ec);

    return true;
}

void ModuleCommander::CreateBackupFolder(const std::filesystem::path &user) {
    namespace fs = std::filesystem;
    auto mod_backup = ModuleCommander::GetModBackup(user);
    std::error_code ec;
    if (fs::exists(mod_backup, ec)) return;

    XLOG::d.i("creating backup folder for modules installing '{}'",
              mod_backup.u8string());

    fs::create_directories(ModuleCommander::GetModBackup(user), ec);
}

bool ModuleCommander::BackupModule(const std::filesystem::path &module_file,
                                   const std::filesystem::path &backup_file) {
    namespace fs = std::filesystem;
    std::error_code ec;
    auto ret = fs::copy_file(module_file, backup_file,
                             fs::copy_options::overwrite_existing, ec);
    if (ret) return true;

    XLOG::l.crit("Error [{}] '{}' installing new mod", ec.value(),
                 ec.message());
    return false;
}

bool ModuleCommander::PrepareCleanTargetDir(
    const std::filesystem::path &mod_dir) {
    namespace fs = std::filesystem;

    if (mod_dir.u8string().size() < kResonableDirLengthMin) {
        XLOG::l("target_dir '{}'is too short when installing new module '{}'",
                mod_dir.u8string());
        return false;
    }
    std::error_code ec;
    fs::remove_all(mod_dir, ec);
    fs::create_directories(mod_dir, ec);

    return true;
}

std::vector<std::string> ModuleCommander::getExtensions() const {
    std::vector<std::string> result;

    for (auto &m : modules_) {
        auto exts = m.exts();
        result.insert(result.end(), exts.begin(), exts.end());
    }

    return result;
}

bool ModuleCommander::InstallModule(const Module &mod,
                                    const std::filesystem::path &root,
                                    const std::filesystem::path &user,
                                    InstallMode mode) {
    namespace fs = std::filesystem;
    using namespace cma::tools;

    auto backup_file = GetModBackup(user) / mod.name();
    backup_file += kExtension.data();
    auto module_file = root / dirs::kFileInstallDir / mod.name();
    module_file += kExtension.data();

    std::error_code ec;
    if (!fs::exists(module_file, ec) || fs::file_size(module_file) == 0) {
        UninstallModuleZip(backup_file, GetModInstall(user));
        XLOG::l.i(
            "Installation of the module '{}' is not required, module file '{}'is "
            "absent or too short. Backup will be uninstalled",
            mod.name(), module_file.u8string());
        return false;
    }

    if (AreFilesSame(backup_file, module_file) && mode == InstallMode::normal) {
        XLOG::l.i(
            "Installation of the module '{}' is not required, module file '{}'is same",
            mod.name(), module_file.u8string());
        return false;
    }

    CreateBackupFolder(user);

    auto uninstalled = UninstallModuleZip(backup_file, GetModInstall(user));

    if (!BackupModule(module_file, backup_file)) return false;

    fs::path default_dir = GetModInstall(user) / mod.name();  // default
    fs::path actual_dir = user / mod.dir();
    if (!PrepareCleanTargetDir(default_dir)) return false;

    if (!fs::equivalent(default_dir, actual_dir)) {
        // establish symbolic link
        CreateFileForTargetDir(default_dir, actual_dir);
    }

    auto ret = zip::Extract(backup_file.wstring(), actual_dir.wstring());
    if (ret) {
        fs::path postinstall{actual_dir};
        postinstall /= "postinstall.cmd";
        if (!fs::exists(module_file, ec)) return true;

        cma::tools::RunCommandAndWait(postinstall.wstring(),
                                      actual_dir.wstring());

        return true;
    }
    XLOG::l("Extraction failed: removing backup file '{}' and default dir '{}'",
            backup_file.u8string(), default_dir.u8string());
    fs::remove(backup_file, ec);
    fs::remove_all(default_dir);

    return false;
}

void ModuleCommander::installModules(const std::filesystem::path &root,
                                     const std::filesystem::path &user,
                                     InstallMode mode) const {
    namespace fs = std::filesystem;
    auto mod_root = GetModInstall(user);
    auto mod_backup = GetModBackup(user);
    if (!CreateDir(mod_root)) return;
    if (!CreateDir(mod_backup)) return;

    auto installed = ScanDir(mod_backup);

    for (auto &f : installed) {
        if (!isBelongsToModules(f)) {
            UninstallModuleZip(f, mod_root);
        }
    }

    for (auto &m : modules_) {
        InstallModule(m, root, user, mode);
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
        XLOG::l("Exception installing modules '{}'", e.what());
    }
}
void ModuleCommander::LoadDefault() noexcept {
    try {
        auto yaml = GetLoadedConfig();
        XLOG::l.i("Loading module config");
        readConfig(yaml);
        prepareToWork();
    } catch (const std::exception &e) {
        XLOG::l("Exception loading modules config '{}'", e.what());
    }
}

void ModuleCommander::prepareToWork() {
    namespace fs = std::filesystem;
    auto mod_backup = GetModBackup(cma::cfg::GetUserDir());
    auto mod_root = GetModInstall(cma::cfg::GetUserDir());

    for (auto &m : modules_) {
        m.prepareToWork(mod_backup, mod_root);
    }
}

bool ModuleCommander::isModuleScript(const std::string_view filename) {
    for (auto &m : modules_) {
        if (m.isMyScript(filename)) return true;
    }
    return false;
}

std::wstring ModuleCommander::buildCommandLine(
    const std::string_view filename) {
    namespace fs = std::filesystem;
    for (auto &m : modules_) {
        if (m.isMyScript(filename)) {
            return m.buildCommandLine(fs::path{filename});
        }
    }
    return {};
}

}  // namespace cma::cfg::modules
