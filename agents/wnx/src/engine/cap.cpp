// Windows Tools
#include <stdafx.h>

#include <cstdint>
#include <filesystem>
#include <string>
#include <unordered_set>

#include "tools/_raii.h"
#include "tools/_xlog.h"

#include "logger.h"

#include "cap.h"
#include "cfg.h"
#include "cvt.h"
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

        if (Mode == ProcMode::kInstall) {
            StoreFile(full_path, data);
            std::error_code ec;
            if (fs::exists(full_path, ec)) FilesLeftOnDisk.push_back(full_path);
        } else if ((Mode == ProcMode::kRemove)) {
            std::error_code ec;
            if (fs::remove(full_path, ec))
                FilesLeftOnDisk.push_back(full_path);
            else {
                XLOG::l("Cannot remove '{}' error {}",
                        wtools::ConvertToUTF8(full_path), ec.value());
            }
        } else if ((Mode == ProcMode::kList)) {
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
bool ReinstallCaps(const std::filesystem::path TargetCap,
                   const std::filesystem::path SourceCap) {
    bool changed = false;
    namespace fs = std::filesystem;
    std::error_code ec;
    std::vector<std::wstring> files_left;
    if (fs::exists(TargetCap, ec)) {
        if (true ==
            Process(TargetCap.u8string(), ProcMode::kRemove, files_left)) {
            XLOG::l.t("File '{}' uninstall-ed", TargetCap.u8string());
            fs::remove(TargetCap, ec);
            for (auto &name : files_left)
                XLOG::l.i("\tRemoved '{}'", wtools::ConvertToUTF8(name));
            changed = true;
        }
    } else
        XLOG::l.t("File '{}' is absent, skipping uninstall",
                  TargetCap.u8string());

    files_left.clear();
    if (fs::exists(SourceCap, ec)) {
        if (true ==
            Process(SourceCap.u8string(), ProcMode::kInstall, files_left)) {
            XLOG::l.t("File {} installed", SourceCap.u8string());
            fs::copy_file(SourceCap, TargetCap, ec);
            for (auto &name : files_left)
                XLOG::l.i("\tAdded '{}'", wtools::ConvertToUTF8(name));
            changed = true;
        }
    } else
        XLOG::l.t("File {} is absent, skipping install", SourceCap.u8string());

    return changed;
}

bool ReinstallIni(const std::filesystem::path TargetIni,
                  const std::filesystem::path SourceIni) {
    namespace fs = std::filesystem;
    std::error_code ec;

    // remove old files
    auto bakery_yml = cma::cfg::GetBakeryFile();
    fs::remove(bakery_yml, ec);
    fs::remove(TargetIni, ec);

    // generate new
    if (fs::exists(SourceIni)) {
        cma::cfg::cvt::Parser p;
        p.prepare();
        p.readIni(SourceIni.u8string(), false);
        auto yaml = p.emitYaml();

        std::ofstream ofs(bakery_yml, std::ios::binary);
        if (ofs) {
            ofs << cma::cfg::upgrade::MakeComments(SourceIni, true);
            ofs << yaml;
        }
        ofs.close();
        fs::copy_file(SourceIni, TargetIni, ec);
    }

    return true;
}

void Install() {
    using namespace cma::cfg;
    using namespace cma::cfg::cap;
    namespace fs = std::filesystem;

    fs::path target_cap = cma::cfg::GetUserDir();
    target_cap /= dirs::kCapInstallDir;
    target_cap /= files::kCapFile;
    fs::path source_cap = cma::cfg::GetRootDir();
    source_cap /= dirs::kCapInstallDir;
    source_cap /= files::kCapFile;

    XLOG::l.t("Installing cap file '{}'", source_cap.u8string());
    if (NeedReinstall(target_cap, source_cap)) {
        XLOG::l.i("Reinstalling '{}' with '{}'", target_cap.u8string(),
                  source_cap.u8string());
        ReinstallCaps(target_cap, source_cap);
    } else
        XLOG::l.t(
            "Installing of CAP file is not required, the file is already installed");

    fs::path target_ini = cma::cfg::GetUserDir();
    target_ini /= dirs::kCapInstallDir;
    target_ini /= files::kIniFile;
    fs::path source_ini = cma::cfg::GetRootDir();
    source_ini /= dirs::kCapInstallDir;
    source_ini /= files::kIniFile;

    std::error_code ec;
    XLOG::l.t("Installing ini file '{}'", source_ini.u8string());
    if (NeedReinstall(target_ini, source_ini)) {
        XLOG::l.i("Reinstalling '{}' with '{}'", target_ini.u8string(),
                  source_ini.u8string());
        ReinstallIni(target_ini, source_ini);
    } else
        XLOG::l.t(
            "Installing of INI file is not required, the file is already installed");
}

}  // namespace cma::cfg::cap
