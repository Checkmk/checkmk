// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// Configuration Parameters for the engine of the Agent
#pragma once

namespace cma::cfg::logwatch {

// '-1' -> ignore this or infinity
constexpr int64_t kMaxSize = 500'000;   // allowed to send
constexpr int64_t kMaxLineLength = -1;  // max entry length
constexpr int64_t kMaxEntries = -1;     // max entry count
constexpr int32_t kTimeout = -1;        // break on timeout

}  // namespace cma::cfg::logwatch
