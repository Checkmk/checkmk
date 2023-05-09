// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef RRDColumn_h
#define RRDColumn_h

#include "config.h"  // IWYU pragma: keep

#include <rrd.h>

// We keep <algorithm> for std::transform but IWYU wants it gone.
#include <algorithm>  // IWYU pragma: keep
#include <chrono>
#include <cstdlib>
#include <ctime>
#include <filesystem>
#include <iterator>
#include <optional>
#include <set>
#include <string>
#include <utility>
#include <vector>

#include "DynamicRRDColumn.h"
#include "ListColumn.h"
#include "Logger.h"
#include "Metric.h"
#include "Renderer.h"
#include "Row.h"
// IWYU versionitis?
#include "nagios.h"  // IWYU pragma: keep
#if defined(CMC)
#include "cmc.h"  // IWYU pragma: keep
#endif
#include "MonitoringCore.h"
#include "strutil.h"
class ColumnOffsets;

template <class T>
class RRDColumn : public ListColumn {
public:
    RRDColumn(const std::string &name, const std::string &description,
              const ColumnOffsets &offsets, MonitoringCore *mc,
              RRDColumnArgs args)
        : ListColumn{name, description, offsets}
        , _mc{mc}
        , _args{std::move(args)} {}

    void output(Row row, RowRenderer &r, const contact *auth_user,
                std::chrono::seconds timezone_offset) const override;

    std::vector<std::string> getValue(
        Row row, const contact *auth_user,
        std::chrono::seconds timezone_offset) const override;

private:
    struct Data {
        std::chrono::system_clock::time_point start;
        std::chrono::system_clock::time_point end;
        unsigned long step{};
        std::vector<double> values;
    };

    [[nodiscard]] Data getData(Row row) const;

    MonitoringCore *_mc;
    RRDColumnArgs _args;

    [[nodiscard]] std::optional<std::pair<std::string, std::string>>
    getHostNameServiceDesc(Row row) const;
};

namespace detail {
bool isVariableName(const std::string &token);
std::string replace_all(const std::string &str, const std::string &chars,
                        char replacement);
std::pair<Metric::Name, std::string> getVarAndCF(const std::string &str);
}  // namespace detail

template <class T>
void RRDColumn<T>::output(Row row, RowRenderer &r,
                          const contact * /* auth_user */,
                          std::chrono::seconds /*timezone_offset*/) const {
    // We output meta data as first elements in the list. Note: In Python or
    // JSON we could output nested lists. In CSV mode this is not possible and
    // we rather stay compatible with CSV mode.
    auto data = getData(row);
    ListRenderer l(r);
    l.output(data.start);
    l.output(data.end);
    l.output(data.step);
    for (const auto &value : data.values) {
        l.output(value);
    }
}

template <class T>
std::vector<std::string> RRDColumn<T>::getValue(
    Row row, const contact * /*auth_user*/,
    std::chrono::seconds timezone_offset) const {
    auto data = getData(row);
    std::vector<std::string> strings;
    strings.push_back(std::to_string(
        std::chrono::system_clock::to_time_t(data.start + timezone_offset)));
    strings.push_back(std::to_string(
        std::chrono::system_clock::to_time_t(data.end + timezone_offset)));
    strings.push_back(std::to_string(data.step));
    std::transform(data.values.begin(), data.values.end(),
                   std::back_inserter(strings),
                   [](const auto &value) { return std::to_string(value); });
    return strings;
}

// TODO(mk): Convert all of the RPN expressions that are available in RRDTool
// and that have a different syntax then we have in our metrics system.
// >= --> GE. Or should we also go with GE instead of >=?
// Look at http://oss.oetiker.ch/rrdtool/doc/rrdgraph_rpn.en.html for details!
template <class T>
typename RRDColumn<T>::Data RRDColumn<T>::getData(Row row) const {
    auto host_name_service_description = getHostNameServiceDesc(row);
    if (!host_name_service_description) {
        return {};
    }

    // Prepare the arguments for rrdtool xport in a dynamic array of strings.
    // Note: The actual step might be different!
    std::vector<std::string> argv_s{
        "rrdtool xport",  // name of program (ignored)
        "-s",
        std::to_string(_args.start_time),
        "-e",
        std::to_string(_args.end_time),
        "--step",
        std::to_string(_args.resolution)};

    if (_args.max_entries > 0) {
        argv_s.emplace_back("-m");
        argv_s.emplace_back(std::to_string(_args.max_entries));
    }

    // We have an RPN like fs_used,1024,*. In order for that to work, we need to
    // create DEFs for all RRDs of the service first. The we create a CDEF with
    // our RPN and finally do the export. One difficulty here: we do not know
    // the exact variable names. The filenames of the RRDs have several
    // characters replaced with "_". This is a one-way escaping where we cannot
    // get back the original variable values. So the cleaner (an probably
    // faster) way is to look for the names of variables within our RPN
    // expressions and create DEFs just for them - if the according RRD exists.
    std::string converted_rpn;  // convert foo.max -> foo-max
    std::vector<char> rpn_copy(_args.rpn.begin(), _args.rpn.end());
    rpn_copy.push_back('\0');
    char *scan = &rpn_copy[0];

    // map from RRD variable names to perf variable names. The latter ones
    // can contain several special characters (like @ and -) which the RRD
    // variables cannot. The variable names are constructed with "var_%u"
    unsigned next_variable_number = 0;
    std::set<std::string> touched_rrds;

    while (const char *tok = next_token(&scan, ',')) {
        std::string token = tok;
        if (!converted_rpn.empty()) {
            converted_rpn += ",";
        }
        if (!detail::isVariableName(token)) {
            converted_rpn += token;
            continue;
        }

        // If the token looks like a variable name, then check if there is a
        // matching RRD and create a matching DEF: command if that is the
        // case. The token (assumed to be a metrics variable name) can contain a
        // '.' like e.g. in 'user.max', which select the consolidation function
        // MAX. RRDTool does not allow a variable name to contain a '.', but
        // strangely enough, it allows an underscore. Therefore, we replace '.'
        // by '_' here.
        auto [var, cf] = detail::getVarAndCF(token);
        auto location =
            _mc->metricLocation(host_name_service_description->first,
                                host_name_service_description->second, var);
        std::string rrd_varname;
        if (location.path_.empty() || location.data_source_name_.empty()) {
            rrd_varname = detail::replace_all(var.string(), ".", '_');
        } else {
            rrd_varname = "var_" + std::to_string(++next_variable_number);
            argv_s.push_back(std::string("DEF:")
                                 .append(rrd_varname)
                                 .append("=")
                                 .append(location.path_.string())
                                 .append(":")
                                 .append(location.data_source_name_)
                                 .append(":")
                                 .append(cf));
            touched_rrds.insert(location.path_.string());
        }
        converted_rpn += rrd_varname;
    }

    // Add the two commands for the actual export.
    argv_s.push_back("CDEF:xxx=" + converted_rpn);
    argv_s.emplace_back("XPORT:xxx:");

    // Make RRDTool flush the rrdcached if neccessary

    // The cache deamon experiences long delays when queries extend over a
    // large time range and the underlying RRA are in high resolution.

    // For performance reasons the xport tool will not connect to the daemon
    // client to flush the data but will be done in 2 separate steps. First data
    // will be flush only. Then the xport tool will directly read the RRD file.

    // The performance issues with the cache daemon have been reported to
    // RRDTool on the issue
    // https://github.com/oetiker/rrdtool-1.x/issues/1062

    auto *logger = _mc->loggerRRD();
    if (_mc->pnp4nagiosEnabled() && !_mc->rrdcachedSocketPath().empty()) {
        std::vector<std::string> daemon_argv_s{
            "rrdtool flushcached",  // name of program (ignored)
            "--daemon", _mc->rrdcachedSocketPath()};

        for (const auto &rrdfile : touched_rrds) {
            daemon_argv_s.push_back(rrdfile);
        }

        // Convert our dynamic C++ string array to a C-style argv array
        std::vector<const char *> daemon_argv;
        daemon_argv.reserve(daemon_argv_s.size());
        for (const auto &arg : daemon_argv_s) {
            daemon_argv.push_back(arg.c_str());
        }
        daemon_argv.push_back(nullptr);

        if (logger->isLoggable(LogLevel::debug)) {
            Debug debug(logger);
            debug << "flush RRD data:";
            for (const auto &arg : daemon_argv_s) {
                debug << " " << arg;
            }
        }

        if (rrd_flushcached(static_cast<int>(daemon_argv_s.size()),
                            const_cast<char **>(&daemon_argv[0])) != 0) {
            Warning(logger) << "Error flushing RRD: " << rrd_get_error();
        }
    }

    // Convert our dynamic C++ string array to a C-style argv array
    std::vector<const char *> argv;
    argv.reserve(argv_s.size());
    for (const auto &arg : argv_s) {
        argv.push_back(arg.c_str());
    }
    argv.push_back(nullptr);

    if (logger->isLoggable(LogLevel::debug)) {
        Debug debug(logger);
        debug << "retrieving RRD data:";
        for (const auto &arg : argv_s) {
            debug << " " << arg;
        }
    }

    // Now do the actual export. The library function rrd_xport mimicks the
    // command line API of rrd xport, but - fortunately - we get direct access
    // to a binary buffer with doubles. No parsing is required.
    int xxsize = 0;
    time_t start = 0;
    time_t end = 0;
    unsigned long step = 0;
    unsigned long col_cnt = 0;
    char **legend_v = nullptr;
    rrd_value_t *rrd_data = nullptr;

    // Clear the RRD error float. RRDTool will not do this and immediately fail
    // if an error already occurred.
    rrd_clear_error();

    if (rrd_xport(static_cast<int>(argv_s.size()),
                  const_cast<char **>(&argv[0]), &xxsize, &start, &end, &step,
                  &col_cnt, &legend_v, &rrd_data) != 0) {
        Warning(logger) << "Error accessing RRD: " << rrd_get_error();
        return {};
    }

    // Since we have exactly one XPORT command, we expect exactly one column
    Data data;
    if (col_cnt != 1) {
        Error(logger) << "rrd_xport returned " << col_cnt
                      << " columns, but exactly one was expected.";
    } else {
        // XPORT takes a closed timewindow in its query and returns the
        // timestamped values that represent an intersection with the query
        // window. The returned interval description is right closed.

        // The timestamps associated with a value in RRDtool ALWAYS
        // represent the time the sample was taken. Since any value you
        // sample will represent some sort of past state your sampling
        // apparatus has gathered, the timestamp will always be at the end
        // of the sampling period

        // LEGEND
        // O timestamps of measurements
        // | query values, _start_time and _end_time
        // x returned start, no data contained
        // v returned data rows, includes end y

        // --O---O---O---O---O---O---O---O
        //         |---------------|
        //       x---v---v---v---v---y

        // Exact start time of the represented interval(x). This is <= our
        // _start_time(|), but no value is associated to this time.
        data.start = std::chrono::system_clock::from_time_t(start);
        // Time closing time of the interval(y). This is >= our _end_time, and
        // holds the last data value.
        data.end = std::chrono::system_clock::from_time_t(end);
        // Actual resolution in seconds. This is >= our _resolution
        data.step = step;
        // Now the actual data - double for double
        // Data rows represent past values, thus loop starts with step shift.
        // Interval is right closed, thus iterate until end inclusive.
        rrd_value_t *ptr = rrd_data;
        for (time_t ti = start + step; ti <= end; ti += step) {
            data.values.push_back(*ptr++);
        }
    }

    // rrd_xport uses malloc, so we *have* to use free.
    for (unsigned long j = 0; j < col_cnt; j++) {
        free(legend_v[j]);  // NOLINT
    }
    free(legend_v);  // NOLINT
    free(rrd_data);  // NOLINT
    return data;
}
#endif  // RRDColumn_h
