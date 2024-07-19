// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef NebPaths_h
#define NebPaths_h

#include "livestatus/ICore.h"
#include "livestatus/Interface.h"
#include "neb/NebCore.h"

class NebPaths : public IPaths {
public:
    explicit NebPaths(const NagiosPathConfig &paths) : paths_{paths} {}

    [[nodiscard]] std::filesystem::path log_file() const override {
        return paths_.log_file;
    }

    [[nodiscard]] std::filesystem::path crash_reports_directory()
        const override {
        return paths_.crash_reports_directory;
    }

    [[nodiscard]] std::filesystem::path license_usage_history_file()
        const override {
        return paths_.license_usage_history_file;
    }

    [[nodiscard]] std::filesystem::path inventory_directory() const override {
        return paths_.inventory_directory;
    }

    [[nodiscard]] std::filesystem::path structured_status_directory()
        const override {
        return paths_.structured_status_directory;
    }

    [[nodiscard]] std::filesystem::path robotmk_html_log_directory()
        const override {
        return paths_.robotmk_html_log_directory;
    }

    [[nodiscard]] std::filesystem::path logwatch_directory() const override {
        return paths_.logwatch_directory;
    }

    [[nodiscard]] std::filesystem::path prediction_directory() const override {
        return paths_.prediction_directory;
    }

    [[nodiscard]] std::filesystem::path event_console_status_socket()
        const override {
        return paths_.event_console_status_socket;
    }

    [[nodiscard]] std::filesystem::path livestatus_socket() const override {
        return paths_.livestatus_socket;
    }

    [[nodiscard]] std::filesystem::path history_file() const override {
        return paths_.history_file;
    }

    [[nodiscard]] std::filesystem::path history_archive_directory()
        const override {
        return paths_.history_archive_directory;
    }

    [[nodiscard]] std::filesystem::path rrd_multiple_directory()
        const override {
        return paths_.rrd_multiple_directory;
    }

    [[nodiscard]] std::filesystem::path rrdcached_socket() const override {
        return paths_.rrdcached_socket;
    }

private:
    const NagiosPathConfig &paths_;
};

#endif  // NebPaths_h
