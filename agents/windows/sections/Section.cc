// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#include "Section.h"
#include <sstream>
#include "Environment.h"
#include "Logger.h"
#include "SectionHeader.h"

Section::Section(const std::string &configName, const Environment &env,
                 Logger *logger, const WinApiInterface &winapi,
                 std::unique_ptr<SectionHeaderBase> header)
    : _configName(configName)
    , _env(env)
    , _logger(logger)
    , _winapi(winapi)
    , _header(std::move(header)) {}

Section::~Section() {}  // Allow member type fwd declarations in header

bool Section::produceOutput(std::ostream &out,
                            const std::optional<std::string> &remoteIP) {
    std::string output;
    bool res = generateOutput(output, remoteIP);

    if (res && !output.empty()) {
        out << *_header << output;

        if (*output.rbegin() != '\n') {
            out << '\n';
        }
    }

    return res;
}

bool Section::generateOutput(std::string &buffer,
                             const std::optional<std::string> &remoteIP) {
    std::ostringstream inner;
    bool res = produceOutputInner(inner, remoteIP);
    buffer = inner.str();
    return res;
}
