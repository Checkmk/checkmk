// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/RRDFetch.h"

#include <iostream>

std::ostream &operator<<(std::ostream &os, const RRDFetchHeader &h) {
    auto epoch = [](auto &&t) {
        return std::chrono::duration_cast<std::chrono::seconds>(
                   t.time_since_epoch())
            .count();
    };
    return os << "FlushVersion: " << h.flush_version() << "\n"
              << "Start: " << epoch(h.start()) << "\n"
              << "End: " << epoch(h.end()) << "\n"
              << "Step: " << h.step() << "\n"
              << "DSCount: " << h.dscount() << "\n"
              << h.dsname() << "\n";
}
