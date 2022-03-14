// Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <filesystem>
#include <memory>
#include <sstream>
#include <string>

#include "DynamicFileColumn.cc"  // NOLINT(bugprone-suspicious-include)
#include "DynamicFileColumn.h"
#include "nagios.h"
class CrashReport;

template class DynamicFileColumn<CrashReport>;
template class DynamicFileColumn<host>;
