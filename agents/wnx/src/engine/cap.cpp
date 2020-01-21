// Windows Tools

#include "stdafx.h"

#include "cap.h"

#include <yaml-cpp/yaml.h>

#include <cstdint>
#include <filesystem>
#include <string>
#include <string_view>
#include <unordered_set>

#include "cfg.h"
#include "cma_core.h"
#include "common/cma_yml.h"
#include "cvt.h"
#include "logger.h"
#include "tools/_raii.h"
#include "tools/_xlog.h"
#include "upgrade.h"

// returns TRUE only if file have been removed
static std::string ErrorCodeToMessage(std::error_code ec) {
    auto str = fmt::format("failed [{}] {}", ec.value(), ec.message());

    if (!str.empty()) str.pop_back();
    return str;
}

static void CopyFileWithLog(const std::filesystem::path &target,
                            const std::filesystem::path &source) {
    std::error_code ec;
    auto success = std::filesystem::copy_file(source, target, ec);
    if (success)
        XLOG::l.i("Copy file '{}' to '{}' [OK]", source.u8string(),
                  target.u8string());
    else
        XLOG::l("Copy file '{}' to '{}' failed {}", source.u8string(),
                target.u8string(), ErrorCodeToMessage(ec));
}

static bool RemoveFileWithLog(const std::filesystem::path &f) {
    std::error_code ec;
    auto success = std::filesystem::remove(f, ec);
    if (success || ec.value() == 0)
        XLOG::l.i("Remove '{}' [OK]", f.u8string());
    else
        XLOG::l("Remove '{}' {}", f.u8string(), ErrorCodeToMessage(ec));

    //
    return success;
}

namespace cma::cfg::cap {

// calculate valid path and create folder
// returns path
std::wstring ProcessPluginPath(const std::string &File) {
    namespace fs = std::filesystem;

    // Extract basename and dirname from path
    fs::path fpath(File);
    fs::path plugin_folder = cma::cfg::GetUserDir();

    plugin_folder /= fpath;

    return plugin_folder.lexically_normal().wstring();
}

// -1 means FAILURE
// 0 means end of file
// all other name should be read
uint32_t ReadFileNameLength(std::ifstream &CapFile) {
    uint8_t length = 0;
    CapFile.read(reinterpret_cast<char *>(&length), sizeof(length));
    if (CapFile.good()) return length;

    if (CapFile.eof()) {
        XLOG::l.t("End of CAP-file. OK!");
        return 0;
    }

    XLOG::l("Unexpected problems with CAP-file name header");
    return -1;
}

// File format
// [BYTE][variable][INT32][variable]
std::string ReadFileName(std::ifstream &CapFile, uint32_t Length) {
    size_t buffer_length = Length;
    ++buffer_length;

    std::vector<char> dataBuffer(buffer_length, 0);
    CapFile.read(dataBuffer.data(), Length);

    if (!CapFile.good()) {
        XLOG::l("Unexpected problems with CAP-file name body");
        return {};
    }

    dataBuffer[Length] = '\0';

    XLOG::d.t("Processing file '{}'", dataBuffer.data());

    return std::string(dataBuffer.data());
}

// skips too big files or invalid data
std::optional<std::vector<char>> ReadFileData(std::ifstream &CapFile) {
    // read 32-bit length
    int32_t length = 0;
    CapFile.read(reinterpret_cast<char *>(&length), sizeof(length));
    if (!CapFile.good()) {
        XLOG::l("Unexpected problems with CAP-file data header");
        return {};
    }
    XLOG::d.t("Processing {} bytes of data", length);
    constexpr uint32_t kMaxSizeSupported = 20 * 1024 * 1024;
    if (length > kMaxSizeSupported) {
        XLOG::l.crit("Size of data is too big {} ", length);
        return {};
    }

    // read content
    size_t buffer_length = length;

    std::vector<char> dataBuffer(buffer_length, 0);
    CapFile.read(dataBuffer.data(), length);

    if (!CapFile.good()) {
        XLOG::l("Unexpected problems with CAP-file data body");
        return {};
    }
    return dataBuffer;
}

// reads name and data
// writes file
// if problems or end return false
FileInfo ExtractFile(std::ifstream &cap_file) {
    // Read Filename
    auto l = ReadFileNameLength(cap_file);
    if (l == 0) {
        XLOG::l.t("File CAP end!");
        return {{}, {}, true};
    }

    constexpr uint32_t kInternalNax = 256;
    if (l > kInternalNax) return {{}, {}, false};

    const auto name = ReadFileName(cap_file, l);

    if (name.empty() || !cap_file.good()) {
        if (cap_file.eof()) return {{}, {}, false};

        XLOG::l.crit("Invalid cap file, [name]");
        return {{}, {}, false};
    }

    const auto content = ReadFileData(cap_file);
    if (content.has_value() && cap_file.good())
        return {name, content.value(), false};

    XLOG::l.crit("Invalid cap file, [name] {}", name);
    return {{}, {}, false};
}

// may create dirs too
// may create empty file
bool StoreFile(const std::wstring &Name, const std::vector<char> &Data) {
    namespace fs = std::filesystem;
    fs::path fpath = Name;
    std::error_code ec;
    if (!fs::create_directories(fpath.parent_path(), ec) && ec.value() != 0) {
        XLOG::l.crit("Cannot create path to '{}', status = {}",
                     fpath.parent_path().u8string(), ec.value());
        return false;
    }

    // Write plugin
    try {
        std::ofstream ofs(Name, std::ios::binary | std::ios::trunc);
        if (ofs.good()) {
            ofs.write(Data.data(), Data.size());
            return true;
        }

    } catch (const std::exception &e) {
        XLOG::l("Exception on create/write file '{}',  '{}'", fpath.u8string(),
                e.what());
    }
    XLOG::l.crit("Cannot create file to '{}', status = {}", fpath.u8string(),
                 GetLastError());
    return false;
}

bool CheckAllFilesWritable(const std::string &Directory) {
    namespace fs = std::filesystem;
    bool all_writable = true;
    for (auto &p : fs::recursive_directory_iterator(Directory)) {
        std::error_code ec;
        auto const &path = p.path();
        if (fs::is_directory(path, ec)) continue;
        if (!fs::is_regular_file(path, ec)) continue;

        auto path_string = path.wstring();
        if (path_string.empty()) continue;

        auto handle = ::CreateFile(path_string.c_str(),  // file to open
                                   GENERIC_WRITE,        // open for write
                                   FILE_SHARE_READ | FILE_SHARE_WRITE,
                                   nullptr,  // default security
                                   OPEN_EXISTING,
                                   FILE_ATTRIBUTE_NORMAL,  // normal file
                                   nullptr);
        if (handle != nullptr && handle != INVALID_HANDLE_VALUE) {
            ::CloseHandle(handle);
        } else {
            XLOG::d("file '{}' is not writable, error {}", path.u8string(),
                    GetLastError());
            all_writable = false;
            break;
        }
    }
    return all_writable;
}

// internal or advanced usage
bool ExtractAll(const std::string &cap_name, const std::filesystem::path &to) {
    std::ifstream ifs(cap_name, std::ifstream::in | std::ifstream::binary);
    if (!ifs) {
        XLOG::l.crit("Unable to open Check_MK-Agent package {} ", cap_name);
        return false;
    }

    while (!ifs.eof()) {
        auto [name, data, eof] = ExtractFile(ifs);
        if (eof) return true;

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

bool Process(const std::string &cap_name, ProcMode Mode,
             std::vector<std::wstring> &FilesLeftOnDisk) {
    namespace fs = std::filesystem;
    std::ifstream ifs(cap_name, std::ifstream::in | std::ifstream::binary);
    if (!ifs) {
        XLOG::l.crit("Unable to open Check_MK-Agent package {} ", cap_name);
        return false;
    }

    while (!ifs.eof()) {
        auto [name, data, eof] = ExtractFile(ifs);
        if (eof) return true;

        if (name.empty()) {
            XLOG::l("CAP file {} looks as bad", cap_name);
            return false;
        }
        if (data.empty()) {
            XLOG::l("CAP file {} looks as bad for file {}", cap_name, name);
            return false;
        }
        const auto full_path = ProcessPluginPath(name);

        if (Mode == ProcMode::install) {
            StoreFile(full_path, data);
            std::error_code ec;
            if (fs::exists(full_path, ec)) FilesLeftOnDisk.push_back(full_path);
        } else if (Mode == ProcMode::remove) {
            std::error_code ec;
            auto removed = fs::remove(full_path, ec);
            if (removed || ec.value() == 0)
                FilesLeftOnDisk.push_back(full_path);
            else {
                XLOG::l("Cannot remove '{}' error {}",
                        wtools::ConvertToUTF8(full_path), ec.value());
            }
        } else if (Mode == ProcMode::list) {
            FilesLeftOnDisk.push_back(full_path);
        }
    }

    // CheckAllFilesWritable(wtools::ConvertToUTF8(cma::cfg::GetUserPluginsDir()));
    // CheckAllFilesWritable(wtools::ConvertToUTF8(cma::cfg::GetLocalDir()));

    XLOG::l("CAP file {} looks as bad with unexpected eof", cap_name);
    return false;
}

bool AreFilesSame(const std::filesystem::path &Target,
                  const std::filesystem::path &Src) {
    try {
        std::ifstream f1(Target, std::ifstream::binary | std::ifstream::ate);
        std::ifstream f2(Src, std::ifstream::binary | std::ifstream::ate);

        if (f1.fail() || f2.fail()) {
            return false;  // file problem
        }

        if (f1.tellg() != f2.tellg()) {
            return false;  // size mismatch
        }

        // seek back to beginning and use std::equal to compare contents
        f1.seekg(0, std::ifstream::beg);
        f2.seekg(0, std::ifstream::beg);
        return std::equal(std::istreambuf_iterator<char>(f1.rdbuf()),
                          std::istreambuf_iterator<char>(),
                          std::istreambuf_iterator<char>(f2.rdbuf()));
    } catch (const std::exception &e) {
        XLOG::l(XLOG_FUNC + " exception '{}'", e.what());
        return false;
    }
}

bool NeedReinstall(const std::filesystem::path &Target,
                   const std::filesystem::path &Src) {
    namespace fs = std::filesystem;
    std::error_code ec;

    if (!fs::exists(Src, ec)) {
        XLOG::d.w("Source File '{}' is absent, reinstall not possible",
                  Src.u8string());
        return false;
    }

    if (!fs::exists(Target, ec)) {
        XLOG::d.i("Target File '{}' is absent, reinstall is mandatory",
                  Target.u8string());
        return true;
    }

    // now both file are present
    auto target_time = fs::last_write_time(Target, ec);
    auto src_time = fs::last_write_time(Src, ec);
    if (src_time > target_time) return true;
    XLOG::d.i("Timestamp OK, checking file content...");
    return !AreFilesSame(Target, Src);
}

// returns true when changes had been done
bool ReinstallCaps(const std::filesystem::path &target_cap,
                   const std::filesystem::path &source_cap) {
    bool changed = false;
    namespace fs = std::filesystem;
    std::error_code ec;
    std::vector<std::wstring> files_left;
    if (fs::exists(target_cap, ec)) {
        if (Process(target_cap.u8string(), ProcMode::remove, files_left)) {
            XLOG::l.t("File '{}' uninstall-ed", target_cap.u8string());
            fs::remove(target_cap, ec);
            for (auto &name : files_left)
                XLOG::l.i("\tRemoved '{}'", wtools::ConvertToUTF8(name));
            changed = true;
        }
    } else
        XLOG::l.t("File '{}' is absent, skipping uninstall",
                  target_cap.u8string());

    files_left.clear();
    if (fs::exists(source_cap, ec)) {
        if (Process(source_cap.u8string(), ProcMode::install, files_left)) {
            XLOG::l.t("File '{}' installed", source_cap.u8string());
            fs::copy_file(source_cap, target_cap, ec);
            for (auto &name : files_left)
                XLOG::l.i("\tAdded '{}'", wtools::ConvertToUTF8(name));
            changed = true;
        }
    } else
        XLOG::l.t("File '{}' is absent, skipping install",
                  source_cap.u8string());

    return changed;
}

static void ConvertIniToBakery(const std::filesystem::path &bakery_yml,
                               const std::filesystem::path &source_ini) {
    auto yaml = upgrade::LoadIni(source_ini);

    if (!yaml.has_value()) return;  // bad ini

    XLOG::l.i("Creating Bakery file '{}'", bakery_yml.u8string());
    std::ofstream ofs(bakery_yml);
    if (ofs) {
        ofs << cma::cfg::upgrade::MakeComments(source_ini, true);
        ofs << *yaml;
    }
    XLOG::l.i("Creating Bakery file SUCCESS");
}

// Replaces target with source
// Removes target if source absent
// For non-packaged agents convert ini to bakery.yml
bool ReinstallIni(const std::filesystem::path &target_ini,
                  const std::filesystem::path &source_ini) {
    namespace fs = std::filesystem;
    std::error_code ec;

    auto packaged_agent = IsIniFileFromInstaller(source_ini);
    if (packaged_agent)
        XLOG::l.i(
            "This is PACKAGED AGENT,"
            "upgrading ini file to the bakery.yml will be skipped");

    // remove old files
    auto bakery_yml = cma::cfg::GetBakeryFile();
    if (!packaged_agent) {
        XLOG::l.i("Removing '{}'", bakery_yml.u8string());
        fs::remove(bakery_yml, ec);
    }

    XLOG::l.i("Removing '{}'", target_ini.u8string());
    fs::remove(target_ini, ec);

    // if file doesn't exists we will leave
    if (!fs::exists(source_ini, ec)) {
        XLOG::l.i("No source ini, leaving");
        return true;
    }

    if (!packaged_agent) ConvertIniToBakery(bakery_yml, source_ini);

    XLOG::l.i("Copy init");
    fs::copy_file(source_ini, target_ini, ec);

    return true;
}

namespace details {
void UninstallYaml(const std::filesystem::path &bakery_yaml,
                   const std::filesystem::path &target_yaml) {
    if (RemoveFileWithLog(target_yaml)) RemoveFileWithLog(bakery_yaml);
}

void InstallYaml(const std::filesystem::path &bakery_yaml,
                 const std::filesystem::path &target_yaml,
                 const std::filesystem::path &source_yaml) {
    std::error_code ec;
    if (std::filesystem::exists(source_yaml, ec)) {
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
bool ReinstallYaml(const std::filesystem::path &bakery_yaml,
                   const std::filesystem::path &target_yaml,
                   const std::filesystem::path &source_yaml) {
    std::error_code ec;

    XLOG::l.i("This Option/YML installation form MSI is ENABLED");

    // we remove target file always good or bad our
    // This is uninstall process
    details::UninstallYaml(bakery_yaml, target_yaml);

    try {
        auto yaml = YAML::LoadFile(source_yaml.u8string());
        if (!yaml.IsDefined() || !yaml.IsMap()) {
            XLOG::l("Supplied Yaml '{}' is bad", source_yaml.u8string());
            return false;
        }

        auto global = yaml["global"];
        if (!global.IsDefined() || !global.IsMap()) {
            XLOG::l("Supplied Yaml '{}' has bad global section",
                    source_yaml.u8string());
            return false;
        }

        auto install =
            cma::yml::GetVal(global, cma::cfg::vars::kInstall, false);
        XLOG::l.i("Supplied yaml '{}' {}", source_yaml.u8string(),
                  install ? "to be installed" : "will not be installed");
        if (!install) return false;

    } catch (const std::exception &e) {
        XLOG::l.crit("Exception parsing supplied YAML file '{}' : '{}'",
                     source_yaml.u8string(), e.what());
        return false;
    }

    // install process
    // this file may be left after uninstallation of yaml
    RemoveFileWithLog(bakery_yaml);
    details::InstallYaml(bakery_yaml, target_yaml, source_yaml);

    return true;
}

PairOfPath GetInstallPair(std::wstring_view name) {
    namespace fs = std::filesystem;
    fs::path target = cma::cfg::GetUserInstallDir();
    target /= name;

    fs::path source = cma::cfg::GetRootInstallDir();
    source /= name;

    return {target, source};
}

static void InstallCapFile() {
    auto [target_cap, source_cap] = GetInstallPair(files::kCapFile);

    XLOG::l.t("Installing cap file '{}'", source_cap.u8string());
    if (NeedReinstall(target_cap, source_cap)) {
        XLOG::l.i("Reinstalling '{}' with '{}'", target_cap.u8string(),
                  source_cap.u8string());
        ReinstallCaps(target_cap, source_cap);
        return;
    }

    XLOG::l.t("Installing of CAP file is not required");
}

static void InstallIniFile() {
    auto [target_ini, source_ini] = GetInstallPair(files::kIniFile);

    XLOG::l.t("Installing ini file '{}'", source_ini.u8string());
    if (NeedReinstall(target_ini, source_ini)) {
        XLOG::l.i("Reinstalling '{}' with '{}'", target_ini.u8string(),
                  source_ini.u8string());
        ReinstallIni(target_ini, source_ini);
        return;
    }

    XLOG::l.t("Installing of INI file is not required");
}

static void InstallYmlFile() {
    auto [target_yml, source_yml] = GetInstallPair(files::kInstallYmlFileW);

    XLOG::l.t("Installing yml file '{}'", source_yml.u8string());
    if (NeedReinstall(target_yml, source_yml)) {
        XLOG::l.i("Reinstalling '{}' with '{}'", target_yml.u8string(),
                  source_yml.u8string());
        std::filesystem::path bakery_yml = cma::cfg::GetBakeryDir();

        bakery_yml /= files::kBakeryYmlFile;
        ReinstallYaml(bakery_yml, target_yml, source_yml);
        return;
    }

    XLOG::l.t("Installing of YML file is not required");
}

static void PrintInstallCopyLog(std::string_view info_on_error,
                                const std::filesystem::path &in_file,
                                const std::filesystem::path &out_file,
                                const std::error_code &ec) noexcept {
    if (ec.value() == 0)
        XLOG::l.i("\tSuccess");
    else
        XLOG::d("\t{} in '{}' out '{}' error [{}] '{}'", info_on_error,
                in_file.u8string(), out_file.u8string(), ec.value(),
                ec.message());
}

static std::string KillTrailingCR(std::string &&message) {
    if (!message.empty() && message.back() == '\n') message.pop_back();
    if (!message.empty() && message.back() == '\r') message.pop_back();  // win
    return std::move(message);
}

// true when copy or copy not required
// false on error
bool InstallFileAsCopy(std::wstring_view filename,    // checkmk.dat
                       std::wstring_view target_dir,  // $CUSTOM_PLUGINS_PATH$
                       std::wstring_view source_dir,  // @root/install
                       Mode mode) noexcept {
    namespace fs = std::filesystem;

    std::error_code ec;
    fs::path target_file = target_dir;
    if (!fs::is_directory(target_dir, ec)) {
        XLOG::l.i("Target Folder '{}' is suspicious [{}] '{}'",
                  target_file.u8string(), ec.value(),
                  KillTrailingCR(ec.message()));
        return false;
    }

    target_file /= filename;
    fs::path source_file = source_dir;
    source_file /= filename;

    XLOG::l.t("Copy file '{}' to '{}'", source_file.u8string(),
              target_file.u8string());

    if (!fs::exists(source_file, ec)) {
        // special case, no source file => remove target file
        fs::remove(target_file, ec);
        PrintInstallCopyLog("Remove failed", source_file, target_file, ec);
        return true;
    }

    if (!cma::tools::IsValidRegularFile(source_file)) {
        XLOG::l.i("File '{}' is bad", source_file.u8string());
        return false;
    }

    if (mode == Mode::forced || NeedReinstall(target_file, source_file)) {
        XLOG::l.i("Reinstalling '{}' with '{}'", target_file.u8string(),
                  source_file.u8string());

        fs::copy_file(source_file, target_file,
                      fs::copy_options::overwrite_existing, ec);
        PrintInstallCopyLog("Copy failed", source_file, target_file, ec);
    } else
        XLOG::l.t("Copy is not required, the file is already exists");
    return true;
}

PairOfPath GetExampleYmlNames() {
    using namespace cma::cfg;
    namespace fs = std::filesystem;
    fs::path src_example = GetRootInstallDir();

    src_example /= files::kUserYmlFile;
    fs::path tgt_example = GetUserDir();
    tgt_example /= files::kUserYmlFile;
    tgt_example.replace_extension(".example.yml");
    return {tgt_example, src_example};
}

constexpr bool G_PatchLineEnding =
    false;  // set to true to fix error during checkout git

static void UpdateUserYmlExample(const std::filesystem::path &tgt,
                                 const std::filesystem::path &src) {
    namespace fs = std::filesystem;
    if (!NeedReinstall(tgt, src)) return;

    XLOG::l.i("User Example must be updated");
    std::error_code ec;
    fs::copy(src, tgt, fs::copy_options::overwrite_existing, ec);
    if (ec.value() == 0) {
        XLOG::l.i("User Example '{}' have been updated successfully from '{}'",
                  tgt.u8string(), src.u8string());
        // #PROPERTY:
        if (G_PatchLineEnding) wtools::PatchFileLineEnding(tgt);
    } else
        XLOG::l.i(
            "User Example '{}' have been failed to update with error [{}] from '{}'",
            tgt.u8string(), ec.value(), src.u8string());
}

void Install() {
    using namespace cma::cfg;
    using namespace cma::cfg::cap;
    namespace fs = std::filesystem;

    try {
        InstallCapFile();
        InstallIniFile();
        InstallYmlFile();
    } catch (const std::exception &e) {
        XLOG::l.crit("Exception '{}'", e.what());
        return;
    }

    // DAT
    auto source = GetRootInstallDir();

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

    {
        auto [tgt_example, src_example] = GetExampleYmlNames();
        UpdateUserYmlExample(tgt_example, src_example);
    }
}

// Re-install all files as is from the root-install
void ReInstall() {
    using namespace cma::cfg;

    namespace fs = std::filesystem;
    fs::path root_dir = GetRootInstallDir();
    fs::path user_dir = GetUserInstallDir();
    fs::path bakery_dir = GetBakeryDir();

    std::vector<std::pair<const std::wstring_view, const ProcFunc>> data_vector{
        {files::kCapFile, ReinstallCaps},
        {files::kIniFile, ReinstallIni},
    };

    try {
        for (const auto [name, func] : data_vector) {
            auto target = user_dir / name;
            auto source = root_dir / name;

            XLOG::l.i("Forced Reinstalling '{}' with '{}'", target.u8string(),
                      source.u8string());
            func(target, source);
        }

        ReinstallYaml(bakery_dir / files::kBakeryYmlFile,
                      user_dir / files::kInstallYmlFileA,
                      root_dir / files::kInstallYmlFileA);
    } catch (const std::exception &e) {
        XLOG::l.crit("Exception '{}'", e.what());
        return;
    }

    auto source = GetRootInstallDir();

    InstallFileAsCopy(files::kDatFile, GetUserInstallDir(), source,
                      Mode::forced);
}

}  // namespace cma::cfg::cap
