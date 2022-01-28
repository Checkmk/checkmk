// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

//
//
// Support for Zip files
//
//

#pragma once

#include <filesystem>

namespace cma::tools::zip {
enum class Type { unknown, zip, cab };

bool Extract(const std::filesystem::path &file_src,
             const std::filesystem::path &dir_dest);

}  // namespace cma::tools::zip
