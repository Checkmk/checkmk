// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//
//
// Support for Zip files
//
//

#pragma once

#include <string>
#include <string_view>
#include <vector>

namespace cma::tools::zip {

// Base functionality(no recursion, only top-level entries)
std::vector<std::wstring> List(std::wstring_view file_src);

// basically error-free
bool Extract(std::wstring_view file_src, std::wstring_view dir_dest);

}  // namespace cma::tools::zip
