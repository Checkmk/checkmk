// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#include "MockWinApi.h"

// See
// https://github.com/google/googletest/blob/master/googlemock/docs/CookBook.md#making-the-compilation-faster.
// Defining mock class constructor and destructor in source file should speed up
// compilation.
MockWinApi::MockWinApi() {}
MockWinApi::~MockWinApi() {}
