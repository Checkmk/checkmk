// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/ICore.h"

#include <filesystem>

#include "livestatus/Interface.h"
#include "livestatus/Logger.h"

void ICore::dumpPaths(Logger *logger) const {
    auto p{paths()};
    Notice(logger) << "log file = " << p->log_file();
    Notice(logger) << "crash reports directory = "
                   << p->crash_reports_directory();
    Notice(logger) << "license usage history file = "
                   << p->license_usage_history_file();
    Notice(logger) << "inventory directory = " << p->inventory_directory();
    Notice(logger) << "structured status directory = "
                   << p->structured_status_directory();
    Notice(logger) << "Robotmk HTML log directory = "
                   << p->robotmk_html_log_directory();
    Notice(logger) << "logwatch directory = " << p->logwatch_directory();
    Notice(logger) << "prediction directory = " << p->prediction_directory();
    Notice(logger) << "event console status socket = "
                   << p->event_console_status_socket();
    Notice(logger) << "Livestatus socket = " << p->livestatus_socket();
    Notice(logger) << "history file = " << p->history_file();
    Notice(logger) << "history archive directory = "
                   << p->history_archive_directory();
    Notice(logger) << "RRD multiple directory = "
                   << p->rrd_multiple_directory();
    Notice(logger) << "rrdcached socket = " << p->rrdcached_socket();
}
