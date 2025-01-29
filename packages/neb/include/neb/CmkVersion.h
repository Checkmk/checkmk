// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef CmkVersion_h
#define CmkVersion_h

#include <string>

namespace cmk {
// Build optimization:  This returns the version (such as 2.3.0p7)
// of the release, which is passed as an argument to the compiler
// and may change every day.  We keep this function isolated so
// as not to invalidate the cache for the rest of the library and
// miminize recompilation.
std::string version();
}  // namespace cmk

#endif  // Comment_h
