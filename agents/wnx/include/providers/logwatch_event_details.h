// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#pragma once
#ifndef LOGWATCH_EVENT_DETAILS_H
#define LOGWATCH_EVENT_DETAILS_H

#include <string>

#include "providers/logwatch_event.h"
#include "wnx/cma_core.h"

namespace cma::provider::details {
State ParseStateLine(const std::string &line);
StateVector LoadEventlogOffsets(const PathVector &state_files,
                                bool reset_pos_to_null);
}  // namespace cma::provider::details

#endif  // LOGWATCH_EVENT_DETAILS_H
