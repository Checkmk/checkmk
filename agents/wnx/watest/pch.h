// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
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

#include "../engine/stdafx_defines.h"  // this is not very nice approach, still we want to test Engine with same definitions.
                                       // --- We just reuse header file

#include <filesystem>

#include "common/cfg_info.h"

namespace tst {
extern const std::filesystem::path G_ProjectPath;
extern const std::filesystem::path G_SolutionPath;
extern const std::filesystem::path G_TestPath;
}  // namespace tst

// definitions required for gtest
#define _SILENCE_CXX17_STRSTREAM_DEPRECATION_WARNING
#define _CRT_SECURE_NO_WARNINGS
#include "common/yaml.h"
#include "gtest/gtest.h"

#endif  // PCH_H
