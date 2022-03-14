// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// provides basic api to start and stop service

#pragma once
#ifndef fileinfo_details_h__
#define logwatch_event_details_h__

#include <filesystem>
#include <regex>
#include <string>

#include "cma_core.h"
#include "providers/internal.h"
#include "providers/logwatch_event.h"
#include "section_header.h"

namespace cma::provider::details {
State ParseStateLine(const std::string &line);
StateVector LoadEventlogOffsets(const PathVector &state_files,
                                bool reset_pos_to_null);
}  // namespace cma::provider::details

#endif  // logwatch_event_details_h__
