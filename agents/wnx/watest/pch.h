// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// ----------------------------------------------
// main PRECOMPILED header file for WATEST
//
// include only massive files which are in use
// ----------------------------------------------
//

#ifndef PCH_H
#define PCH_H

#include "wnx/stdafx_defines.h"  // this is not very nice approach, still we want to test Engine with same definitions.
                                 // --- We just reuse header file

// NOTE: This code block is used to speed compilation.
// Sets usually for msbuild in script using environment variable
// ExternalCompilerOptions.
#ifdef _DECREASE_COMPILE_TIME_
#include <algorithm>
#include <cctype>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <cstring>
#include <cwctype>
#include <filesystem>
#include <fstream>
#include <functional>
#include <future>
#include <iostream>
#include <iterator>
#include <mutex>
#include <optional>
#include <random>
#include <sstream>
#include <string>
#include <string_view>
#include <thread>
#include <tuple>
#include <type_traits>
#include <unordered_map>
#include <vector>
#endif

#include <filesystem>

#include "common/cfg_info.h"

// definitions required for gtest
#define _SILENCE_CXX17_STRSTREAM_DEPRECATION_WARNING  // NOLINT
#include "common/yaml.h"
#include "gtest/gtest.h"
#define ENABLE_WHITE_BOX_TESTING

#endif  // PCH_H
