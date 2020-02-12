// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#include "EventLogBase.h"
#include "EventLog.h"
#include "EventLogVista.h"
#include "Logger.h"

std::unique_ptr<EventLogBase> open_eventlog(const std::wstring &name_or_path,
                                            bool try_vista_api, Logger *logger,
                                            const WinApiInterface &winapi) {
    if (try_vista_api) {
        try {
            return std::unique_ptr<EventLogBase>(
                new EventLogVista(name_or_path, winapi));
        } catch (const UnsupportedException &) {
            Alert(logger) << "vista-style event-log api not available";
        }
    }
    return std::unique_ptr<EventLogBase>(
        new EventLog(name_or_path, logger, winapi));
}
