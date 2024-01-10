// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef PerformanceData_h
#define PerformanceData_h

#include <string>
#include <vector>

#include "livestatus/Metric.h"

// Parse performance data according to
//    https://nagios-plugins.org/doc/guidelines.html#AEN200
//    https://icinga.com/docs/icinga1/latest/de/perfdata.html#perfdata-format
class PerformanceData {
public:
    PerformanceData(const std::string &perf_data,
                    const std::string &default_check_command_name);

    [[nodiscard]] bool empty() const { return _metrics.empty(); }
    [[nodiscard]] auto size() const { return _metrics.size(); }
    [[nodiscard]] auto begin() const { return _metrics.cbegin(); }
    [[nodiscard]] auto end() const { return _metrics.cend(); }
    [[nodiscard]] std::string checkCommandName() const {
        return _check_command_name;
    }

private:
    std::vector<Metric> _metrics;
    std::string _check_command_name;

    void addMetric(const std::string &label, const std::string &value,
                   const std::string &uom, const std::string &warn,
                   const std::string &crit, const std::string &min,
                   const std::string &max);
};

#endif  // PerformanceData_h
