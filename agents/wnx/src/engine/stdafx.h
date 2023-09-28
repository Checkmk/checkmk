// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

//
// THIS is pre-compiled header for Engine Project
//
#pragma once
#ifndef ENGINE_STDAFX_H
#define ENGINE_STDAFX_H

#if defined(_MSC_VER)
// more aggressive warning
#pragma warning(3 : 4062)
#endif

#include "wnx/stdafx_defines.h"  // shared use, watest!

// settings for the LWA
#define _SILENCE_CXX17_CODECVT_HEADER_DEPRECATION_WARNING  // NOLINT
#define SI_SUPPORT_IOSTREAMS

#include "common/cfg_info.h"
#include "tools/_raii.h"  // ON_OUT_OF_SCOPE and other extremely useful staff

// NOTE: This code block is used to speed compilation in production.
// Sets usually for msbuild in script using environment variable
// ExternalCompilerOptions.
#ifdef DECREASE_COMPILE_TIME
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

#endif  // ENGINE_STDAFX_H#include <mutex>
