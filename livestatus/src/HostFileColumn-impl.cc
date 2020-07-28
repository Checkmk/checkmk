// Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "CrashReport.h"
#include "HostFileColumn.cc"
#include "nagios.h"

template class HostFileColumn<CrashReport>;
template class HostFileColumn<host>;
