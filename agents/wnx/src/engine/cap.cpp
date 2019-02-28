// Windows Tools
#include <stdafx.h>

#include <cstdint>
#include <filesystem>
#include <string>

#include "tools/_raii.h"
#include "tools/_xlog.h"

#include "logger.h"

#include "cvt.h"

#include "SimpleIni.h"

namespace cma::cfg::cap {

#if 0
const char *integrityErrorMsg =
    "There was an error on unpacking the Check_MK-Agent package: File "
    "integrity is broken.\n"
    "The file might have been installed partially!";

const char *uninstallInfo =
    "REM * If you want to uninstall the plugins which were installed "
    "during the\n"
    "REM * last 'check_mk_agent.exe unpack' command, just execute this "
    "script\n\n";

std::string managePluginPath(const std::string &filePath) {
    namespace fs = std::filesystem;

    // Extract basename and dirname from path
    fs::path fpath = filePath;
    auto name = fpath.filename();
    const std::string dirname = fpath.
        pos == std::string::npos ? "" : filePath.substr(0, pos);
    auto pluginPath = cma::cfg::GetUserPluginsDir();

    if (!dirname.empty()) {
        pluginPath += dirname;
        ::CreateDirectory(pluginPath.c_str(), nullptr);
        pluginPath += "\\";
    }

    pluginPath += basename;

    return pluginPath;
}

template <typename LengthT>
std::vector<BYTE> readData(
    std::ifstream &ifs, bool zeroTerminate,
    const std::function<void(LengthT)> &check = [](LengthT) {}) {
    LengthT length = 0;
    ifs.read(reinterpret_cast<char *>(&length), sizeof(length));
    if (!ifs.good()) {
        return {};
    }
    check(length);
    size_t count = length;
    if (zeroTerminate) {
        count += 1;
    }
    std::vector<BYTE> dataBuffer(count, 0);
    ifs.read(reinterpret_cast<char *>(dataBuffer.data()), length);

    if (!ifs.good()) {
        throw UnpackError(integrityErrorMsg);
    }

    if (zeroTerminate) {
        dataBuffer[length] = '\0';
    }

    return dataBuffer;
}

void extractPlugin(const Environment &env, std::ifstream &ifs,
                   WritableFile &uninstallFile) {
    // Read Filename
    const auto filepath = readData<BYTE>(ifs, true);

    if (!ifs.good()) {
        if (ifs.eof()) {
            return;
        } else {
            throw UnpackError(integrityErrorMsg);
        }
    }
    const std::string filePath(reinterpret_cast<char const *>(filepath.data()));
    const auto checkPluginSize = [&filePath](const int length) {
        // Maximum plugin size is 20 MB
        if (length > 20 * 1024 * 1024) {
            throw UnpackError("Size of plugin '" + filePath +
                              "' exceeds 20 MB");
        }
    };
    const auto content = readData<int>(ifs, false, checkPluginSize);
    if (!ifs.good()) {
        throw UnpackError(integrityErrorMsg);
    }
    const auto pluginPath = managePluginPath(filePath, env);
    uninstallFile << "del \"" << pluginPath << "\"\n";

    // TODO: remove custom dirs on uninstall

    // Write plugin
    WritableFile pluginFile(pluginPath, 0, CREATE_NEW, s_winapi);
    pluginFile << content;
}

void do_unpack_plugins(const char *plugin_filename, const Environment &env) {
    Logger *logger = Logger::getLogger("winagent");
    try {
        std::ifstream ifs(plugin_filename,
                          std::ifstream::in | std::ifstream::binary);
        if (!ifs) {
            throw UnpackError(
                std::string{"Unable to open Check_MK-Agent package "} +
                plugin_filename);
        }

        WritableFile uninstallFile(
            env.agentDirectory() + "\\uninstall_plugins.bat", 0, CREATE_NEW,
            s_winapi);
        uninstallFile << uninstallInfo;

        while (!ifs.eof()) {
            extractPlugin(env, ifs, uninstallFile);
        }

        uninstallFile << "del \"" << env.agentDirectory()
                      << "\\uninstall_plugins.bat\"\n";
    } catch (const std::runtime_error &e) {
        Error(logger) << e.what();
        std::cerr << e.what() << std::endl;
        exit(1);
    }

    try {
        Debug(logger) << "areAllFilesWritable: " << std::boolalpha
                      << areAllFilesWritable(
                             env.agentDirectory(), s_winapi,
                             getDefaultWhitelist(env, s_winapi));
    } catch (const FileError &e) {
        Error(logger) << e.what();
    }
}
#endif

bool InstallCapFile(std::filesystem::path CapFile) { return false; }

}  // namespace cma::cfg::cap
