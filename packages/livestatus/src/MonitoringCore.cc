// Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/MonitoringCore.h"

#include <sstream>

#include "livestatus/Logger.h"

void Paths::dump(Logger *logger) const {
    Notice(logger) << "log file = " << log_file;
    Notice(logger) << "crash reports directory = " << crash_reports_directory;
    Notice(logger) << "license usage history file = "
                   << license_usage_history_file;
    Notice(logger) << "inventory directory = " << inventory_directory;
    Notice(logger) << "structured status directory = "
                   << structured_status_directory;
    Notice(logger) << "Robotmk HTML log directory = "
                   << robotmk_html_log_directory;
    Notice(logger) << "logwatch directory = " << logwatch_directory;
    Notice(logger) << "event console status socket = "
                   << event_console_status_socket;
    Notice(logger) << "Livestatus socket = " << livestatus_socket;
    Notice(logger) << "history file = " << history_file;
    Notice(logger) << "history archive directory = "
                   << history_archive_directory;
    Notice(logger) << "RRD multiple directory = " << rrd_multiple_directory;
    Notice(logger) << "rrdcached socket = " << rrdcached_socket;
}
