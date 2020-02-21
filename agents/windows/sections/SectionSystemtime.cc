// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#include "SectionSystemtime.h"
#include <iomanip>
#include "Logger.h"
#include "SectionHeader.h"

SectionSystemtime::SectionSystemtime(const Environment &env, Logger *logger,
                                     const WinApiInterface &winapi)
    : Section("systemtime", env, logger, winapi,
              std::make_unique<DefaultHeader>("systemtime", logger)) {}

bool SectionSystemtime::produceOutputInner(std::ostream &out,
                                           const std::optional<std::string> &) {
    Debug(_logger) << "SectionSystemtime::produceOutputInner";
    out << section_helpers::current_time();
    return true;
}
