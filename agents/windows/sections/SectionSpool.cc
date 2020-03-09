// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#include "SectionSpool.h"
#include <sys/types.h>
#include <chrono>
#include <experimental/filesystem>
#include "Environment.h"
#include "Logger.h"
#include "SectionHeader.h"
#include "types.h"

namespace chrono = std::chrono;
namespace fs = std::experimental::filesystem;

SectionSpool::SectionSpool(const Environment &env, Logger *logger,
                           const WinApiInterface &winapi)
    : Section("spool", env, logger, winapi,
              std::make_unique<HiddenHeader>(logger)) {}

bool SectionSpool::produceOutputInner(std::ostream &out,
                                      const std::optional<std::string> &) {
    Debug(_logger) << "SectionSpool::produceOutputInner";
    // Look for files in the spool directory and append these files to
    // the agent output. The name of the files may begin with a number
    // of digits. If this is the case then it is interpreted as a time
    // in seconds: the maximum allowed age of the file. Outdated files
    // are simply ignored.
    for (const auto &de : fs::directory_iterator(_env.spoolDirectory())) {
        const auto &path = de.path();
        const auto filename = path.filename().string();
        const int max_age = isdigit(filename[0]) ? atoi(filename.c_str()) : -1;

        if (max_age >= 0) {
            const auto age =
                chrono::duration_cast<chrono::seconds>(
                    chrono::system_clock::now() - fs::last_write_time(path))
                    .count();
            if (age > max_age) {
                Informational(_logger)
                    << "    " << filename << ": skipping outdated file: age is "
                    << age << " sec, "
                    << "max age is " << max_age << " sec.";
                continue;
            }
        }
        Debug(_logger) << "    " << filename;

        std::ifstream ifs(path.string());
        if (ifs) {
            out << ifs.rdbuf();
        }
    }

    return true;
}
