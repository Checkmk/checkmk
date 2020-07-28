// Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "CrashReport.h"
#include "DynamicHostFileColumn.cc"
#include "nagios.h"

template class DynamicHostFileColumn<CrashReport>;
template class DynamicHostFileColumn<host>;
