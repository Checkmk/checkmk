// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// provides basic api to start and stop service

#pragma once
#ifndef df_h__
#define df_h__

#include <string>

#include "providers/internal.h"
#include "section_header.h"

namespace cma::provider {
constexpr char kDfSeparator = section::kTabSeparator;
constexpr auto kDfSeparatorString = section::kTabSeparatorString;

class Df : public Asynchronous {
public:
    Df() : Asynchronous(cma::section::kDfName, '\t') {}

private:
    std::string makeBody() override;
};

namespace df {
std::pair<std::string, std::string> GetNamesByVolumeId(
    std::string_view volume_id);
std::pair<uint64_t, uint64_t> GetSpacesByVolumeId(std::string_view volume_id);
std::string ProduceFileSystemOutput(std::string_view volume_id);
std::vector<std::string> GetMountPointVector(std::string_view volume_id);
std::string ProduceMountPointsOutput(std::string_view volume_id);
std::vector<std::string> GetDriveVector();
uint64_t CalcUsage(uint64_t avail, uint64_t total);
}  // namespace df

};  // namespace cma::provider

#endif  // df_h__
