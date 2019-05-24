
// provides basic api to start and stop service
#include "stdafx.h"

#include "providers/spool.h"

#include <chrono>
#include <filesystem>
#include <regex>
#include <string>
#include <string_view>
#include <tuple>

#include "cfg.h"
#include "cma_core.h"
#include "common/wtools.h"
#include "fmt/format.h"
#include "glob_match.h"
#include "logger.h"
#include "read_file.h"
#include "tools/_raii.h"
#include "tools/_xlog.h"

namespace cma::provider {

void SpoolProvider::loadConfig() {}

void SpoolProvider::updateSectionStatus() {}

bool IsDirectoryValid(const std::filesystem::path &Dir) {
    using namespace cma::cfg;
    namespace fs = std::filesystem;
    std::error_code ec;
    if (!fs::exists(Dir, ec)) {
        XLOG::l.crit(
            "Installation is bad. Spool directory '{}' is absent ec:{}",
            Dir.u8string(), ec.value());
        return false;
    }

    if (!fs::is_directory(Dir, ec)) {
        XLOG::l.crit("Installation is bad. '{}' isn't directory {}",
                     Dir.u8string(), ec.value());
        return false;
    }

    return true;
}

// direct conversion from LWA
bool IsSpoolFileValid(const std::filesystem::path &Path) {
    using namespace std::chrono;
    namespace fs = std::filesystem;

    // Checking the file is good
    std::error_code ec;
    if (!fs::exists(Path, ec)) {
        XLOG::d("File is absent. '{}' ec:{}", Path.u8string(), ec.value());
        return false;
    }

    if (!fs::is_regular_file(Path, ec)) {
        XLOG::d("File is bad. '{}' ec:{}", Path.u8string(), ec.value());
        return false;
    }

    const auto filename = Path.filename().string();
    const int max_age = 0 != isdigit(filename[0]) ? atoi(filename.c_str()) : -1;

    if (max_age >= 0) {
        // extremely stupid
        // different clocks no conversion between clocks
        // only in C++ 20
        auto ftime = fs::last_write_time(Path, ec);
        if (ec.value() != 0) {
            XLOG::l("Crazy file{} gives ec : {}", Path.u8string(), ec.value());
            return false;
        }
        const auto age = duration_cast<seconds>(
                             fs::_File_time_clock::now().time_since_epoch() -
                             ftime.time_since_epoch())
                             .count();
        if (age >= max_age) {
            XLOG::l.t() << "    " << filename
                        << ": skipping outdated file: age is " << age
                        << " sec, "
                        << "max age is " << max_age << " sec.";
            return false;
        }
    }

    return true;
}

std::string SpoolProvider::makeBody() {
    namespace fs = std::filesystem;
    XLOG::t(XLOG_FUNC + " entering");

    fs::path dir = cma::cfg::GetSpoolDir();
    // check presence of the folder
    if (!IsDirectoryValid(dir)) {
        XLOG::d("Spool directory absent. But spool is requested");
        return {};
    }

    std::string out;
    // Look for files in the spool directory and append these files to
    // the agent output. The name of the files may begin with a number
    // of digits. If this is the case then it is interpreted as a time
    // in seconds: the maximum allowed age of the file. Outdated files
    // are simply ignored.

    for (const auto &entry : fs::directory_iterator(dir)) {
        const auto &path = entry.path();
        if (!IsSpoolFileValid(path)) {
            XLOG::d("Strange, but this is not a file {}", path.u8string());
            continue;
        }

        auto data = cma::tools::ReadFileInVector(path);
        if (data) {
            auto add_size = data->size();
            if (0 == add_size) continue;

            auto old_size = out.size();
            try {
                out.resize(add_size + old_size);
                memcpy(out.data() + old_size, data->data(), add_size);
            } catch (const std::exception &e) {
                XLOG::l(XLOG_FLINE + " Out of *memory* {}", e.what());
                continue;
            }
        }
    }

    return out;
}

}  // namespace cma::provider
