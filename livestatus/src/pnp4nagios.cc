// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "pnp4nagios.h"

#include <cstddef>

#ifndef CMC
#include <filesystem>
#include <system_error>

#include "MonitoringCore.h"
#endif

namespace {

// TODO(sp): Move this to some kind of C++ string utility file.
std::string replace_all(const std::string &str, const std::string &chars,
                        char replacement) {
    std::string result(str);
    size_t i = 0;
    while ((i = result.find_first_of(chars, i)) != std::string::npos) {
        result[i++] = replacement;
    }
    return result;
}
}  // namespace

std::string pnp_cleanup(const std::string &name) {
    return replace_all(name, R"( /\:)", '_');
}

#ifndef CMC
// TODO(sp) Merge this with Perfdatabase::getPNPXMLPath
int pnpgraph_present(MonitoringCore *mc, const std::string &host,
                     const std::string &service) {
    std::filesystem::path pnp_path = mc->pnpPath();
    if (pnp_path.empty()) {
        return -1;
    }
    std::filesystem::path path =
        pnp_path / pnp_cleanup(host) / (pnp_cleanup(service) + ".xml");
    std::error_code ec;
    std::filesystem::status(path, ec);
    return ec ? 0 : 1;
}
#endif
