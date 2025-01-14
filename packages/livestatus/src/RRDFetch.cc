// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/RRDFetch.h"

#include <iostream>

std::ostream &operator<<(std::ostream &os, const RRDFetchHeader &h) {
    return os << "FlushVersion: " << h.flush_version() << "\n"
              << "Start: " << std::chrono::system_clock::to_time_t(h.start())
              << "\n"
              << "End: " << std::chrono::system_clock::to_time_t(h.end())
              << "\n"
              << "Step: " << h.step() << "\n"
              << "DSCount: " << h.dscount() << "\n";
}
