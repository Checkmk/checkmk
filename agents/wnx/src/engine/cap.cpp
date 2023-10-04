// Windows Tools

#include "stdafx.h"

#include "wnx/cap.h"

#include <cstdint>
#include <filesystem>
#include <fstream>
#include <string>

#include "common/cma_yml.h"
#include "common/yaml.h"
#include "tools/_win.h"
#include "wnx/cfg.h"
#include "wnx/cma_core.h"
#include "wnx/logger.h"
#include "wnx/upgrade.h"
namespace fs = std::filesystem;
namespace rs = std::ranges;
using namespace std::chrono_literals;

namespace {
std::string ErrorCodeToMessage(std::error_code ec) {
    return fmt::format("failed [{}] {}", ec.value(), ec.message());
}

void CopyFileWithLog(const fs::path &target, const fs::path &source) {
    if (std::error_code ec; fs::copy_file(source, target, ec)) {
        XLOG::l.i("Copy file '{}' to '{}' [OK]", source, target);
    } else {
        XLOG::l("Copy file '{}' to '{}' failed {}", source, target,
                ErrorCodeToMessage(ec));
    }
}

bool RemoveFileWithLog(const fs::path &f) {
    std::error_code ec;
    const auto success = fs::remove(f, ec);
    if (success || !ec) {
        XLOG::l.i("Remove '{}' [OK]", f);
    } else {
        XLOG::l("Remove '{}' {}", f, ErrorCodeToMessage(ec));
    }

    //
    return success;
}
}  // namespace

namespace cma::cfg::cap {

// calculate valid path and create folder
// returns path
std::wstring ProcessPluginPath(const std::string &name) {
    // Extract basename and dirname from path
    fs::path fpath(name);
    fs::path plugin_folder = GetUserDir();

    plugin_folder /= fpath;

    return plugin_folder.lexically_normal().wstring();
}

// -1 means FAILURE
// 0 means end of file
// all other name should be read
std::optional<uint32_t> ReadFileNameLength(std::ifstream &cap_file) {
    uint8_t length = 0;
    cap_file.read(reinterpret_cast<char *>(&length), sizeof length);
    if (cap_file.good()) {
        return length;
    }

    if (cap_file.eof()) {
        XLOG::l.t("End of CAP-file. OK!");
        return 0;
    }

    XLOG::l("Unexpected problems with CAP-file name header");
    return {};
}

// File format
// [BYTE][variable][INT32][variable]
std::string ReadFileName(std::ifstream &cap_file, uint32_t length) {
    size_t buffer_length = length;
    ++buffer_length;

    std::vector<char> data_buffer(buffer_length, 0);
    cap_file.read(data_buffer.data(), length);

    if (!cap_file.good()) {
        XLOG::l("Unexpected problems with CAP-file name body");
        return {};
    }

    data_buffer[length] = '\0';

    XLOG::d.t("Processing file '{}'", data_buffer.data());

    return {data_buffer.data()};
}

// skips too big files or invalid data
std::optional<std::vector<char>> ReadFileData(std::ifstream &cap_file) {
    uint32_t length = 0;
    cap_file.read(reinterpret_cast<char *>(&length), sizeof length);
    if (!cap_file.good()) {
        XLOG::l("Unexpected problems with CAP-file data header");
        return {};
    }
    XLOG::d.t("Processing {} bytes of data", length);

    // ATTENTION: Value below must be bigger than cap.py::MAX_ALLOWED_SIZE
    // This limit is only to avoid RAM problems, real control should be
    // performed by WATO.
    constexpr uint32_t max_allowed_size = 1024 * 1024 * 1024;
    if (length > max_allowed_size) {
        XLOG::l.crit("Size of data is too big {} allowed {}", length,
                     max_allowed_size);
        return {};
    }
    const size_t buffer_length = length;
    std::vector<char> data_buffer(buffer_length, 0);
    cap_file.read(data_buffer.data(), length);

    if (!cap_file.good()) {
        XLOG::l("Unexpected problems with CAP-file data body");
        return {};
    }
    return data_buffer;
}

constexpr uint32_t kInternalMax{256};

// reads name and data
// writes file
// if problems or end - return false
FileInfo ExtractFile(std::ifstream &cap_file) {
    const auto result = ReadFileNameLength(cap_file);
    if (!result.has_value()) {
        XLOG::l.crit("Invalid cap file, to long name");
        return {{}, {}, false};
    }
    auto length = result.value();
    if (length == 0) {
        XLOG::l.t("File CAP end!");
        return {{}, {}, true};
    }
    if (length > kInternalMax) {
        XLOG::l.crit("Invalid cap file, to long name {}", length);
        return {{}, {}, false};
    }

    const auto name = ReadFileName(cap_file, length);
    if (name.empty() || !cap_file.good()) {
        if (!cap_file.eof()) {
            XLOG::l.crit("Invalid cap file, [name]");
            return {{}, {}, false};
        }

        return {{}, {}, false};
    }

    if (const auto content = ReadFileData(cap_file);
        content.has_value() && cap_file.good()) {
        return {name, content.value(), false};
    }

    XLOG::l.crit("Invalid cap file, [name] {}", name);
    return {{}, {}, false};
}

// may create dirs too
// may create empty file
bool StoreFile(const std::wstring &name, const std::vector<char> &data) {
    fs::path fpath = name;
    std::error_code ec;
    if (!fs::create_directories(fpath.parent_path(), ec) && ec) {
        XLOG::l.crit("Cannot create path to '{}', status = {}",
                     fpath.parent_path(), ec.value());
        return false;
    }

    // Write plugin
    try {
        std::ofstream ofs(name, std::ios::binary | std::ios::trunc);
        if (ofs.good()) {
            ofs.write(data.data(), static_cast<std::streamsize>(data.size()));
            return true;
        }
        XLOG::l.crit("Cannot create file to '{}', status = {}", fpath,
                     ::GetLastError());

    } catch (const std::exception &e) {
        XLOG::l("Exception on create/write file '{}',  '{}'", fpath, e.what());
    }
    return false;
}

[[nodiscard]] std::wstring GetProcessToKill(std::wstring_view name) {
    const fs::path p = name;
    if (!p.has_filename()) {
        return {};
    }
    if (!tools::IsEqual(wtools::ToUtf8(p.extension().wstring()),
                        kAllowedExtension)) {
        return {};
    }

    auto proc_name = p.filename().wstring();
    if (proc_name.length() < kMinimumProcessNameLength) {
        return {};
    }

    return proc_name;
}

static std::string GetTryKillMode() {
    return GetVal(groups::kGlobal, vars::kTryKillPluginProcess,
                  std::string{defaults::kTryKillPluginProcess});
}

namespace {
const std::array<std::wstring, 3> g_try_to_kill_allowed_names = {
    L"cmk-update-agent.exe", L"mk_logwatch.exe", L"mk_jolokia.exe"};
}

[[nodiscard]] bool IsAllowedToKill(std::wstring_view proc_name) {
    const auto try_kill_mode = GetTryKillMode();
    if (try_kill_mode == values::kTryKillSafe) {
        XLOG::d.i("Mode is safe, checking on list");
        if (rs::any_of(g_try_to_kill_allowed_names,
                       [proc_name](const std::wstring &name) {
                           return tools::IsEqual(proc_name, name);
                       })) {
            return true;
        }

        XLOG::l.w("Can't kill the process for file '{}' as not safe process",
                  wtools::ToUtf8(proc_name));
        return false;
    }

    return try_kill_mode == values::kTryKillAll;
}

// we will try to kill the process with name of the executable if
// we cannot write to the file
[[nodiscard]] bool StoreFileAgressive(const std::wstring &name,
                                      const std::vector<char> &data,
                                      uint32_t attempts_count) {
    for (uint32_t i = 0; i < attempts_count + 1; ++i) {
        if (StoreFile(name, data)) {
            return true;
        }

        // we try to kill potentially running process
        auto proc_name = GetProcessToKill(name);
        if (proc_name.empty()) {
            XLOG::l.w("Can't kill the process for file '{}'",
                      wtools::ToUtf8(name));
            return false;
        }

        if (!IsAllowedToKill(proc_name)) {
            return false;
        }

        wtools::KillProcessFully(proc_name, 9);
        tools::sleep(500ms);
    }

    return false;
}

[[nodiscard]] bool IsStoreFileAgressive() noexcept {
    return GetTryKillMode() != values::kTryKillNo;
}

bool CheckAllFilesWritable(const std::string &directory) {
    bool all_writable = true;
    for (const auto &p : fs::recursive_directory_iterator(directory)) {
        std::error_code ec;
        auto const &path = p.path();
        if (fs::is_directory(path, ec) || !fs::is_regular_file(path, ec)) {
            continue;
        }

        auto path_string = path.wstring();
        if (path_string.empty()) {
            continue;
        }

        auto *handle =
            ::CreateFile(path_string.c_str(),                 // file to open
                         GENERIC_WRITE,                       // open for write
                         FILE_SHARE_READ | FILE_SHARE_WRITE,  // NOLINT
                         nullptr,  // default security
                         OPEN_EXISTING,
                         FILE_ATTRIBUTE_NORMAL,  // normal file
                         nullptr);
        if (wtools::IsGoodHandle(handle)) {
            ::CloseHandle(handle);
        } else {
            XLOG::d("file '{}' is not writable, error {}", path,
                    GetLastError());
            all_writable = false;
            break;
        }
    }
    return all_writable;
}

// internal or advanced usage
bool ExtractAll(const std::string &cap_name, const fs::path &to) {
    std::ifstream ifs(cap_name, std::ifstream::in | std::ifstream::binary);
    if (!ifs) {
        XLOG::l.crit("Unable to open Check_MK-Agent package {} ", cap_name);
        return false;
    }

    while (!ifs.eof()) {
        const auto [name, data, eof] = ExtractFile(ifs);
        if (eof) {
            return true;
        }

        if (name.empty()) {
            XLOG::l("CAP file {} looks as bad", cap_name);
            return false;
        }
        if (data.empty()) {
            XLOG::t("CAP file {} has empty file {}", cap_name, name);
        }
        StoreFile(to / name, data);
    }

    XLOG::l("CAP file '{}' looks as bad with unexpected eof", cap_name);
    return false;
}

bool Process(const std::string &cap_name, ProcMode mode,
             std::vector<std::wstring> &files_left_on_disk) {
    std::ifstream ifs(cap_name, std::ifstream::in | std::ifstream::binary);
    if (!ifs) {
        XLOG::l.crit("Unable to open Check_MK-Agent package {} ", cap_name);
        return false;
    }

    while (!ifs.eof()) {
        auto [name, data, eof] = ExtractFile(ifs);
        if (eof) {
            return true;
        }

        if (name.empty()) {
            XLOG::l("CAP file {} looks as bad", cap_name);
            return false;
        }
        if (data.empty()) {
            XLOG::l.w("CAP file {} has emty file file {}", cap_name, name);
        }
        const auto full_path = ProcessPluginPath(name);

        if (mode == ProcMode::install) {
            const auto success =
                IsStoreFileAgressive()
                    ? StoreFileAgressive(full_path, data,
                                         kMaxAttemptsToStoreFile)
                    : StoreFile(full_path, data);
            if (!success) {
                XLOG::l("Can't store file '{}'", wtools::ToUtf8(full_path));
            }

            std::error_code ec;
            if (fs::exists(full_path, ec)) {
                files_left_on_disk.push_back(full_path);
            }
        } else if (mode == ProcMode::remove) {
            std::error_code ec;
            const auto removed = fs::remove(full_path, ec);
            if (removed || ec.value() == 0) {
                files_left_on_disk.push_back(full_path);
            } else {
                XLOG::l("Cannot remove '{}' error {}",
                        wtools::ToUtf8(full_path), ec.value());
            }
        } else if (mode == ProcMode::list) {
            files_left_on_disk.push_back(full_path);
        }
    }

    XLOG::l("CAP file {} looks as bad with unexpected eof", cap_name);
    return false;
}

bool NeedReinstall(const fs::path &target, const fs::path &source) {
    std::error_code ec;
    if (!fs::exists(source, ec)) {
        XLOG::d.w("Source File '{}' is absent, reinstall not possible", source);
        return false;
    }

    if (!fs::exists(target, ec)) {
        XLOG::d.i("Target File '{}' is absent, reinstall is mandatory", target);
        return true;
    }

    // now both file are present
    if (fs::last_write_time(source, ec) > fs::last_write_time(target, ec)) {
        return true;
    }
    XLOG::d.i("Timestamp OK, checking file content...");
    return !tools::AreFilesSame(target, source);
}

// returns true when changes had been done
bool ReinstallCaps(const fs::path &target_cap, const fs::path &source_cap) {
    bool changed = false;
    std::error_code ec;
    std::vector<std::wstring> files_left;
    if (fs::exists(target_cap, ec)) {
        if (Process(wtools::ToStr(target_cap), ProcMode::remove, files_left)) {
            XLOG::l.t("File '{}' uninstall-ed", target_cap);
            fs::remove(target_cap, ec);
            for (auto &name : files_left)
                XLOG::l.i("\tRemoved '{}'", wtools::ToUtf8(name));
            changed = true;
        }
    } else
        XLOG::l.t("File '{}' is absent, skipping uninstall", target_cap);

    files_left.clear();
    if (fs::exists(source_cap, ec)) {
        if (Process(wtools::ToStr(source_cap), ProcMode::install, files_left)) {
            XLOG::l.t("File '{}' installed", source_cap);
            fs::copy_file(source_cap, target_cap, ec);
            for (auto &name : files_left)
                XLOG::l.i("\tAdded '{}'", wtools::ToUtf8(name));
            changed = true;
        }
    } else
        XLOG::l.t("File '{}' is absent, skipping install", source_cap);

    return changed;
}

namespace details {
void UninstallYaml(const fs::path &bakery_yaml, const fs::path &target_yaml) {
    if (RemoveFileWithLog(target_yaml)) {
        RemoveFileWithLog(bakery_yaml);
    }
}

void InstallYaml(const fs::path &bakery_yaml, const fs::path &target_yaml,
                 const fs::path &source_yaml) {
    std::error_code ec;
    if (fs::exists(source_yaml, ec)) {
        CopyFileWithLog(target_yaml, source_yaml);
        CopyFileWithLog(bakery_yaml, source_yaml);
    } else {
        XLOG::d("{} is absent, this is not typical situation",
                source_yaml.u8string());
    }
}
}  // namespace details

// Replaces target with source
// Removes target if source absent
// For non-packaged agents convert ini to bakery.yml
bool ReinstallYaml(const fs::path &bakery_yaml, const fs::path &target_yaml,
                   const fs::path &source_yaml) {
    std::error_code ec;

    XLOG::l.i("This Option/YML installation form MSI is ENABLED");

    // we remove target file always good or bad our
    // This is uninstall process
    details::UninstallYaml(bakery_yaml, target_yaml);

    // In 1.6 target_yml was not presented
    if (fs::exists(bakery_yaml, ec)) {
        XLOG::d.i("Looks as 1.6 installation: remove '{}'", bakery_yaml);
        fs::remove(bakery_yaml, ec);
    }

    try {
        auto yaml = YAML::LoadFile(wtools::ToStr(source_yaml));
        if (!yaml.IsDefined() || !yaml.IsMap()) {
            XLOG::l("Supplied Yaml '{}' is bad", source_yaml);
            return false;
        }

        const auto global = yaml["global"];
        if (!global.IsDefined() || !global.IsMap()) {
            XLOG::l("Supplied Yaml '{}' has bad global section", source_yaml);
            return false;
        }

        const auto install = yml::GetVal(global, vars::kInstall, false);
        XLOG::l.i("Supplied yaml '{}' {}", source_yaml,
                  install ? "to be installed" : "will not be installed");
        if (!install) return false;

    } catch (const std::exception &e) {
        XLOG::l.crit("Exception parsing supplied YAML file '{}' : '{}'",
                     source_yaml, e);
        return false;
    }

    // install process
    // this file may be left after uninstallation of yaml
    RemoveFileWithLog(bakery_yaml);
    details::InstallYaml(bakery_yaml, target_yaml, source_yaml);

    return true;
}

namespace {
bool InstallCapFile() {
    const auto [target_cap, source_cap] = GetInstallPair(files::kCapFile);

    XLOG::l.t("Installing cap file '{}'", source_cap);
    if (NeedReinstall(target_cap, source_cap)) {
        XLOG::l.i("Reinstalling '{}' with '{}'", target_cap, source_cap);
        ReinstallCaps(target_cap, source_cap);
        return true;
    }

    XLOG::l.t("Installing of CAP file is not required");
    return false;
}

void InstallYmlFile() {
    const auto [target_yml, source_yml] =
        GetInstallPair(files::kInstallYmlFileW);

    XLOG::l.t("Installing yml file '{}'", source_yml);
    if (NeedReinstall(target_yml, source_yml)) {
        XLOG::l.i("Reinstalling '{}' with '{}'", target_yml, source_yml);
        fs::path bakery_yml = GetBakeryDir();

        bakery_yml /= files::kBakeryYmlFile;
        ReinstallYaml(bakery_yml, target_yml, source_yml);
        return;
    }

    XLOG::l.t("Installing of YML file is not required");
}

void PrintInstallCopyLog(std::string_view info_on_error,
                         const fs::path &in_file, const fs::path &out_file,
                         const std::error_code &ec) {
    if (ec.value() == 0)
        XLOG::l.i("\tSuccess");
    else
        XLOG::d("\t{} in '{}' out '{}' error [{}] '{}'", info_on_error, in_file,
                out_file, ec.value(), ec.message());
}

std::string KillTrailingCr(std::string &&message) noexcept {
    if (!message.empty() &&
        (message.back() == '\n' || message.back() == '\r')) {
        message.pop_back();
    }
    return std::move(message);
}
}  // namespace

PairOfPath GetInstallPair(std::wstring_view name) {
    fs::path target = GetUserInstallDir();
    target /= name;

    fs::path source = GetRootInstallDir();
    source /= name;

    return {target, source};
}

// true when copy or copy not required
// false on error
bool InstallFileAsCopy(std::wstring_view filename,    // checkmk.dat
                       std::wstring_view target_dir,  // $CUSTOM_PLUGINS_PATH$
                       std::wstring_view source_dir,  // @root/install
                       Mode mode) {
    std::error_code ec;
    fs::path target_file = target_dir;
    if (!fs::is_directory(target_dir, ec)) {
        XLOG::l.i("Target Folder '{}' is suspicious [{}] '{}'", target_file,
                  ec.value(), KillTrailingCr(ec.message()));
        return false;
    }

    target_file /= filename;
    fs::path source_file = source_dir;
    source_file /= filename;

    XLOG::l.t("Copy file '{}' to '{}'", source_file, target_file);

    if (!fs::exists(source_file, ec)) {
        // special case, no source file => remove target file
        fs::remove(target_file, ec);
        PrintInstallCopyLog("Remove failed", source_file, target_file, ec);
        return true;
    }

    if (!tools::IsValidRegularFile(source_file)) {
        XLOG::l.i("File '{}' is bad", source_file);
        return false;
    }

    if (mode == Mode::forced || NeedReinstall(target_file, source_file)) {
        XLOG::l.i("Reinstalling '{}' with '{}'", target_file, source_file);

        fs::copy_file(source_file, target_file,
                      fs::copy_options::overwrite_existing, ec);
        PrintInstallCopyLog("Copy failed", source_file, target_file, ec);
    } else
        XLOG::l.t("Copy is not required, the file is already exists");
    return true;
}

PairOfPath GetExampleYmlNames() {
    fs::path src_example{GetRootInstallDir()};
    src_example /= files::kUserYmlFile;
    fs::path tgt_example{GetUserDir()};
    tgt_example /= files::kUserYmlFile;
    tgt_example.replace_extension(".example.yml");

    return {tgt_example, src_example};
}

constexpr bool g_patch_line_ending =
    false;  // set to true to fix error during checkout git

static void UpdateUserYmlExample(const fs::path &tgt, const fs::path &src) {
    if (!NeedReinstall(tgt, src)) {
        return;
    }

    XLOG::l.i("User Example must be updated");
    std::error_code ec;
    fs::copy(src, tgt, fs::copy_options::overwrite_existing, ec);
    if (!ec) {
        XLOG::l.i("User Example '{}' have been updated successfully from '{}'",
                  tgt, src);
        if constexpr (g_patch_line_ending) {
            wtools::PatchFileLineEnding(tgt);
        }
    } else {
        XLOG::l.i(
            "User Example '{}' have been failed to update with error [{}] from '{}'",
            tgt, ec.value(), src);
    }
}

bool Install() {
    bool installed{false};
    try {
        installed = InstallCapFile();
        InstallYmlFile();
    } catch (const std::exception &e) {
        XLOG::l.crit("Exception '{}'", e.what());
        return installed;
    }

    // DAT
    const auto source = GetRootInstallDir();
    InstallFileAsCopy(files::kDatFile, GetUserInstallDir(), source,
                      Mode::normal);

    // YML
    fs::path target_file = GetUserDir();
    target_file /= files::kUserYmlFile;
    std::error_code ec;
    if (!fs::exists(target_file, ec)) {
        XLOG::l.i("Installing user yml file");
        InstallFileAsCopy(files::kUserYmlFile, GetUserDir(), source,
                          Mode::normal);
    } else {
        XLOG::d.i("Skip installing user yml file");
    }

    const auto [tgt_example, src_example] = GetExampleYmlNames();
    UpdateUserYmlExample(tgt_example, src_example);
    return installed;
}

// Re-install all files as is from the root-install
bool ReInstall() {
    const fs::path root_dir = GetRootInstallDir();
    const fs::path user_dir = GetUserInstallDir();
    const fs::path bakery_dir = GetBakeryDir();

    std::vector<std::pair<const std::wstring_view, const ProcFunc>> data_vector{
        {files::kCapFile, ReinstallCaps},
    };

    try {
        for (const auto &[name, func] : data_vector) {
            auto target = user_dir / name;
            auto source = root_dir / name;

            XLOG::l.i("Forced Reinstalling '{}' with '{}'", target, source);
            func(target, source);
        }

        ReinstallYaml(bakery_dir / files::kBakeryYmlFile,
                      user_dir / files::kInstallYmlFileA,
                      root_dir / files::kInstallYmlFileA);
    } catch (const std::exception &e) {
        XLOG::l.crit("Exception '{}'", e.what());
        return false;
    }

    return InstallFileAsCopy(files::kDatFile, GetUserInstallDir(),
                             GetRootInstallDir(), Mode::forced);
}

}  // namespace cma::cfg::cap
