// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "stdafx.h"

#include "providers/spool.h"

#include <chrono>
#include <filesystem>
#include <string>
#include <string_view>

#include "cfg.h"
#include "cma_core.h"
#include "common/wtools.h"
#include "logger.h"
#include "tools/_raii.h"

namespace cma::provider {

void SpoolProvider::loadConfig() {}

void SpoolProvider::updateSectionStatus() {}

bool IsDirectoryValid(const std::filesystem::path &dir) {
    namespace fs = std::filesystem;

    std::error_code ec;
    if (!fs::exists(dir, ec)) {
        XLOG::l("Spool directory '{}' is absent error [{}]", dir, ec.value());
        return false;
    }

    if (!fs::is_directory(dir, ec)) {
        XLOG::l("'{}' isn't directory, error [{}]", dir, ec.value());
        return false;
    }

    return true;
}

// direct conversion from LWA
bool IsSpoolFileValid(const std::filesystem::path &path) {
    namespace fs = std::filesystem;

    // Checking the file is good
    std::error_code ec;
    if (!fs::exists(path, ec)) {
        XLOG::d("File is absent. '{}' ec:{}", path, ec.value());
        return false;
    }

    if (!fs::is_regular_file(path, ec)) {
        XLOG::d("File is bad. '{}' ec:{}", path, ec.value());
        return false;
    }

    const auto filename = path.filename().string();
    const int max_age = isdigit(filename[0]) != 0 ? atoi(filename.c_str()) : -1;

    if (max_age < 0) {
        return true;
    }

    // Name of the file contains age
    // extremely stupid
    // different clocks no conversion between clocks
    // only in C++ 20
    auto ftime = fs::last_write_time(path, ec);
    if (ec.value() != 0) {
        XLOG::l("Crazy file{} gives ec : {}", path, ec.value());
        return false;
    }
    const auto age = std::chrono::duration_cast<std::chrono::seconds>(
                         fs::_File_time_clock::now().time_since_epoch() -
                         ftime.time_since_epoch())
                         .count();
    if (age < max_age) {
        return true;
    }

    XLOG::d.t() << "    " << filename << ": skipping outdated file: age is "
                << age << " sec, "
                << "max age is " << max_age << " sec.";
    return false;
}

std::string SpoolProvider::makeBody() {
    namespace fs = std::filesystem;

    fs::path dir = cma::cfg::GetSpoolDir();

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
            XLOG::d("Strange, but this is not a file {}", path);
            continue;
        }

        auto data = cma::tools::ReadFileInVector(path);
        if (data) {
            auto add_size = data->size();
            if (add_size == 0) continue;

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
