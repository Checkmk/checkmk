// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// ----------------------------------------------
// main PRECOMPILED header file for Plugin player
// include only massive files which are in use
// ----------------------------------------------

#pragma once
#ifndef PCH_H
#define PCH_H

#define NOMINMAX
#define _CRT_SECURE_NO_WARNINGS
#define _SILENCE_CXX17_STRSTREAM_DEPRECATION_WARNING
#define FMT_HEADER_ONLY

#include <filesystem>

#define WIN32_LEAN_AND_MEAN
#include "windows.h"

#endif  // PCH_H
