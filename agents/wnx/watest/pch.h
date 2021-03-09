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
inline const std::filesystem::path G_ProjectPath = PROJECT_DIR;
inline const std::filesystem::path G_SolutionPath = SOLUTION_DIR;
inline const std::filesystem::path G_TestPath =
    cma::cfg::MakePathToUnitTestFiles(G_SolutionPath);

// definitions required for gtest
#define _SILENCE_CXX17_STRSTREAM_DEPRECATION_WARNING
#define _CRT_SECURE_NO_WARNINGS
#include "gtest/gtest.h"
#include "yaml-cpp/yaml.h"

#endif  // PCH_H
