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

namespace cma::cfg::cvt {

YAML::Node LoadIni(std::filesystem::path IniFile) {
    namespace fs = std::filesystem;
    if (IniFile.empty()) {
        XLOG::l("Empty file name to load");
        return {};
    }

    std::error_code ec;
    if (!fs::exists(IniFile, ec)) {
        XLOG::l("File '{}' doesn't exist");
        return {};
    }

    return {};
}
}  // namespace cma::cfg::cvt
