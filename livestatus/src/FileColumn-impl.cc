// Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <memory>

#include "FileColumn.cc"
#include "FileColumn.h"
#include "nagios.h"
class CrashReport;
class TableStatus;

template class FileColumn<CrashReport>;
template class FileColumn<host>;
template class FileColumn<TableStatus>;
