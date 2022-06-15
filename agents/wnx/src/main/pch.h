// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// THIS is pre-compiled header for Check MK Service
//
#pragma once
#ifndef PCH_H
#define PCH_H

#define FMT_HEADER_ONLY

#define _CRT_SECURE_NO_WARNINGS

#define _SILENCE_CXX17_STRSTREAM_DEPRECATION_WARNING

#define NOMINMAX
#define WIN32_LEAN_AND_MEAN
#include <Windows.h>

#endif  // PCH_H
