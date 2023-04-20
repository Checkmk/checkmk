// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef mk_logwatch_h
#define mk_logwatch_h

#include <filesystem>
#include <string>
class Logger;

void mk_logwatch_acknowledge(Logger *logger,
                             const std::filesystem::path &logwatch_path,
                             const std::string &host_name,
                             const std::string &file_name);

#endif  // mk_logwatch_h
