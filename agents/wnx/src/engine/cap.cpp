// Windows Tools

#include "stdafx.h"

#include "cap.h"

#include <cstdint>
#include <filesystem>
#include <string>
#include <string_view>
#include <unordered_set>

#include "cfg.h"
#include "cvt.h"
#include "logger.h"
#include "tools/_raii.h"
#include "tools/_xlog.h"
#include "upgrade.h"

namespace cma::cfg::cap {

// calculate valid path and create folder
// returns path
std::wstring ProcessPluginPath(const std::string &File) {
    namespace fs = std::filesystem;

    // Extract basename and dirname from path
    fs::path fpath = File;
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
    size_t buffer_length = Length + 1;

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

// must be successful!
std::vector<char> ReadFileData(std::ifstream &CapFile) {
    // read 32-bit length
    int32_t length = 0;
    CapFile.read(reinterpret_cast<char *>(&length), sizeof(length));
    if (!CapFile.good()) {
        XLOG::l("Unexpected problems with CAP-file data header");
        return {};
    }
    XLOG::d.t("Processing {} bytes of data", length);
    if (length > 20 * 1024 * 1024) {
        XLOG::l.crit("Size of data is too big {} ", length);
        return {};
    }

    // read content
    size_t buffer_length = length;

    std::vector<char> dataBuffer(buffer_length, 0);
    CapFile.read(dataBuffer.data(), length);

    if (!CapFile.good()) {
        XLOG::l("Unexpected problems with CAP-file adat body");
        return {};
    }
    return dataBuffer;
}

// reads name and data
// writes file
// if problems or end return false
FileInfo ExtractFile(std::ifstream &CapFile) {
    // Read Filename
    auto l = ReadFileNameLength(CapFile);
    if (l == 0) {
        XLOG::l.t("File CAP end!");
        return {{}, {}, true};
    }

    if (l > 256) return {{}, {}, false};

    const auto name = ReadFileName(CapFile, l);

    if (name.empty() || !CapFile.good()) {
        if (CapFile.eof()) return {{}, {}, false};

        XLOG::l.crit("Invalid cap file, [name]");
        return {{}, {}, false};
    }

    const auto content = ReadFileData(CapFile);
    if (content.empty() || !CapFile.good()) {
        XLOG::l.crit("Invalid cap file, [name] {}", name);
        return {{}, {}, false};
    }

    return {name, content, false};
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
        auto path = p.path();
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
        if (handle && handle != INVALID_HANDLE_VALUE) {
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

bool Process(const std::string CapFileName, ProcMode Mode,
             std::vector<std::wstring> &FilesLeftOnDisk) {
    namespace fs = std::filesystem;
    std::ifstream ifs(CapFileName, std::ifstream::in | std::ifstream::binary);
    if (!ifs) {
        XLOG::l.crit("Unable to open Check_MK-Agent package {} ", CapFileName);
        return false;
    }

    while (!ifs.eof()) {
        auto [name, data, eof] = ExtractFile(ifs);
        if (eof) return true;

        if (name.empty()) {
            XLOG::l("CAP file {} looks as bad", CapFileName);
            return false;
        }
        if (data.empty()) {
            XLOG::l("CAP file {} looks as bad for file {}", CapFileName, name);
            return false;
        }
        const auto full_path = ProcessPluginPath(name);

        if (Mode == ProcMode::install) {
            StoreFile(full_path, data);
            std::error_code ec;
            if (fs::exists(full_path, ec)) FilesLeftOnDisk.push_back(full_path);
        } else if ((Mode == ProcMode::remove)) {
            std::error_code ec;
            if (fs::remove(full_path, ec))
                FilesLeftOnDisk.push_back(full_path);
            else {
                XLOG::l("Cannot remove '{}' error {}",
                        wtools::ConvertToUTF8(full_path), ec.value());
            }
        } else if ((Mode == ProcMode::list)) {
            FilesLeftOnDisk.push_back(full_path);
        }
    }

    // CheckAllFilesWritable(wtools::ConvertToUTF8(cma::cfg::GetUserPluginsDir()));
    // CheckAllFilesWritable(wtools::ConvertToUTF8(cma::cfg::GetLocalDir()));

    XLOG::l("CAP file {} looks as bad with unexpected eof", CapFileName);
    return false;
}

bool NeedReinstall(const std::filesystem::path Target,
                   const std::filesystem::path Src) {
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
    return src_time > target_time;
}

// returns true when changes had been done
bool ReinstallCaps(const std::filesystem::path target_cap,
                   const std::filesystem::path source_cap) {
    bool changed = false;
    namespace fs = std::filesystem;
    std::error_code ec;
    std::vector<std::wstring> files_left;
    if (fs::exists(target_cap, ec)) {
        if (true ==
            Process(target_cap.u8string(), ProcMode::remove, files_left)) {
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
        if (true ==
            Process(source_cap.u8string(), ProcMode::install, files_left)) {
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

bool ReinstallIni(const std::filesystem::path target_ini,
                  const std::filesystem::path source_ini) {
    namespace fs = std::filesystem;
    std::error_code ec;

    auto packaged_agent = IsIniFileFromInstaller(source_ini);
    if (packaged_agent)
        XLOG::l.i(
            "This is PACKAGED AGENT,"
            "upgrading ini to the bakery.yml skipped");

    // remove old files
    auto bakery_yml = cma::cfg::GetBakeryFile();
    if (!packaged_agent) fs::remove(bakery_yml, ec);
    fs::remove(target_ini, ec);

    // generate new
    if (!fs::exists(source_ini, ec)) return true;

    if (!packaged_agent) {
        cma::cfg::cvt::Parser p;
        p.prepare();
        p.readIni(source_ini.u8string(), false);
        auto yaml = p.emitYaml();

        std::ofstream ofs(bakery_yml, std::ios::binary);
        if (ofs) {
            ofs << cma::cfg::upgrade::MakeComments(source_ini, true);
            ofs << yaml;
        }
        ofs.close();
    }
    fs::copy_file(source_ini, target_ini, ec);

    return true;
}

static void InstallCapFile() {
    namespace fs = std::filesystem;
    fs::path target_cap = cma::cfg::GetUserInstallDir();
    target_cap /= files::kCapFile;

    fs::path source_cap = cma::cfg::GetFileInstallDir();
    source_cap /= files::kCapFile;

    XLOG::l.t("Installing cap file '{}'", source_cap.u8string());
    if (NeedReinstall(target_cap, source_cap)) {
        XLOG::l.i("Reinstalling '{}' with '{}'", target_cap.u8string(),
                  source_cap.u8string());
        ReinstallCaps(target_cap, source_cap);
    } else
        XLOG::l.t(
            "Installing of CAP file is not required, the file is already installed");
}

static void InstallIniFile() {
    namespace fs = std::filesystem;

    fs::path target_ini = cma::cfg::GetUserInstallDir();
    target_ini /= files::kIniFile;
    fs::path source_ini = cma::cfg::GetFileInstallDir();
    source_ini /= files::kIniFile;

    XLOG::l.t("Installing ini file '{}'", source_ini.u8string());
    if (NeedReinstall(target_ini, source_ini)) {
        XLOG::l.i("Reinstalling '{}' with '{}'", target_ini.u8string(),
                  source_ini.u8string());
        ReinstallIni(target_ini, source_ini);
    } else
        XLOG::l.t(
            "Installing of INI file is not required, the file is already installed");
}

static void PrintInstallCopyLog(std::string_view info_on_error,
                                std::filesystem::path in_file,
                                std::filesystem::path out_file,
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
                       std::wstring_view target_dir,  // @user
                       std::wstring_view source_dir)  // @root/install
    noexcept {
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

    if (NeedReinstall(target_file, source_file)) {
        XLOG::l.i("Reinstalling '{}' with '{}'", target_file.u8string(),
                  source_file.u8string());

        fs::copy_file(source_file, target_file,
                      fs::copy_options::overwrite_existing, ec);
        PrintInstallCopyLog("Copy failed", source_file, target_file, ec);
    } else
        XLOG::l.t("Copy is not required, the file is already exists");
    return true;
}

void Install() {
    using namespace cma::cfg;
    using namespace cma::cfg::cap;

    InstallCapFile();
    InstallIniFile();

    auto source = GetFileInstallDir();

    InstallFileAsCopy(files::kDatFile, GetUserInstallDir(), source);
    InstallFileAsCopy(files::kUserYmlFile, GetUserDir(), source);
}

}  // namespace cma::cfg::cap
