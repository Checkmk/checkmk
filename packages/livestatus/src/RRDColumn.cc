// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/RRDColumn.h"

#include <algorithm>
#include <charconv>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <iterator>
#include <memory>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string_view>
#include <system_error>
#include <tuple>

#include "livestatus/ICore.h"
#include "livestatus/Interface.h"
#include "livestatus/Logger.h"
#include "livestatus/Metric.h"
#include "livestatus/PnpUtils.h"
#include "livestatus/RRDConsolidate.h"
#include "livestatus/RRDFetch.h"
#include "livestatus/RRDRPN.h"
#include "livestatus/RRDUDSSocket.h"
#include "livestatus/StringUtils.h"

using namespace std::string_view_literals;
using namespace std::chrono_literals;

RRDColumnArgs::RRDColumnArgs(const std::string &arguments,
                             const std::string &column_name) {
    // We expect the following arguments: RPN:START_TIME:END_TIME:RESOLUTION
    // Example: fs_used,1024,/:1426411073:1426416473:5
    std::string_view args{arguments};
    auto invalid = [&column_name](const std::string &message) {
        throw std::runtime_error("invalid arguments for column '" +
                                 column_name + ": " + message);
    };
    auto next = [&args]() {
        auto field = args.substr(0, args.find(':'));
        args.remove_prefix(std::min(args.size(), field.size() + 1));
        return field;
    };
    auto next_non_empty = [&next, &invalid](const std::string &what) {
        auto field = next();
        if (field.empty()) {
            invalid("missing " + what);
        }
        return field;
    };
    auto parse_number = [&invalid](std::string_view str,
                                   const std::string &what) {
        auto value = 0;
        auto [ptr, ec] = std::from_chars(str.begin(), str.end(), value);
        // TODO(sp) Error handling
        if (ec != std::errc{} || ptr != str.end()) {
            invalid("invalid number for " + what);
        }
        return value;
    };
    auto next_number = [&next_non_empty,
                        &parse_number](const std::string &what) {
        return parse_number(next_non_empty(what), what);
    };

    this->rpn = next_non_empty("RPN expression");
    this->start_time = next_number("start time");
    this->end_time = next_number("end time");
    this->resolution = next_number("resolution");
    auto max_entries = next();
    this->max_entries = max_entries.empty()
                            ? 400
                            : parse_number(max_entries, "maximum entries");
    if (!args.empty()) {
        invalid("too many arguments");
    }
}

std::vector<RRDDataMaker::value_type> RRDDataMaker::operator()(
    const IHost &hst, std::chrono::seconds timezone_offset) const {
    return make(hst.name(), dummy_service_description(), timezone_offset);
}

std::vector<RRDDataMaker::value_type> RRDDataMaker::operator()(
    const IService &svc, std::chrono::seconds timezone_offset) const {
    return make(svc.host().name(), svc.description(), timezone_offset);
}

namespace {
bool isVariableName(std::string_view token) {
    auto is_operator = [](char c) {
        return "+-/*"sv.find_first_of(c) != std::string_view::npos;
    };
    auto is_number_part = [](char c) {
        return "0123456789."sv.find_first_of(c) != std::string_view::npos;
    };

    return !(is_operator(token[0]) ||
             std::ranges::all_of(token, is_number_part));
}

std::string replace_all(const std::string &str, const std::string &chars,
                        char replacement) {
    std::string result(str);
    size_t i = 0;
    while ((i = result.find_first_of(chars, i)) != std::string::npos) {
        result[i++] = replacement;
    }
    return result;
}

std::pair<Metric::Name, std::unique_ptr<CF>> getVarAndCF(std::string_view str) {
    const size_t dot_pos = str.find_last_of('.');
    if (dot_pos != std::string::npos) {
        const Metric::Name head{std::string{str.substr(0, dot_pos)}};
        auto tail = str.substr(dot_pos);
        if (tail == ".max"sv) {
            return std::make_pair(head, std::make_unique<MaxCF>());
        }
        if (tail == ".min"sv) {
            return std::make_pair(head, std::make_unique<MinCF>());
        }
        if (tail == ".average"sv) {
            return std::make_pair(head, std::make_unique<AvgCF>());
        }
    }
    return std::make_pair(Metric::Name{std::string{str}},
                          std::make_unique<MaxCF>());
}

std::vector<double> readData(RRDUDSSocket &sock, std::size_t count) {
    const std::size_t raw_size = count * sizeof(double);
    auto raw = std::string{};
    raw.reserve(raw_size);
    while (raw.size() != raw_size) {
        const auto part = sock.read(raw_size - raw.size());
        if (part.empty()) {
            throw std::runtime_error("invalid payload");
        }
        raw.append(part);
    }
    auto out = std::vector<double>(count);
    std::memcpy(out.data(), raw.data(), raw.size());
    return out;
}

void sendFetchBin(RRDUDSSocket &sock, std::string_view fetchbin,
                  Logger *logger) {
    const auto *it = fetchbin.begin();
    while (it != fetchbin.end()) {
        auto written = sock.write({it, fetchbin.end()}, 200ms);
        if (written <= 0) {
            Warning(logger) << "Error sending RRD data: " << sock.readLine();
            return;
        }
        // NOLINTNEXTLINE(cppcoreguidelines-pro-bounds-pointer-arithmetic)
        it += written;
    }
}

std::tuple<std::string, RRDFetchHeader, std::vector<double>> recvFetchReply(
    RRDUDSSocket &sock) {
    const std::string status = sock.readLine();
    const int retcode = atoi(status.c_str());

    auto rawheader = std::vector<std::string>{};
    if (retcode < 0 || std::size_t(retcode) < RRDFetchHeader::size()) {
        throw std::runtime_error{"invalid header"};
    }
    for (std::size_t ii = 0; ii < RRDFetchHeader::size(); ++ii) {
        auto line = sock.readLine();
        rawheader.emplace_back(line);
    }
    const auto header = RRDFetchHeader::parse(rawheader);
    const auto dsname_line = RRDFetchBinPayloadHeader::parse(sock.readLine());
    const auto payload = readData(sock, dsname_line.value_count);
    return std::make_tuple(status, header, payload);
}

struct Data {
    RRDFetchHeader::time_point start;
    RRDFetchHeader::time_point end;
    unsigned long step{0};
    std::vector<double> values;

    [[nodiscard]] std::vector<RRDDataMaker::value_type> as_vector(
        std::chrono::seconds timezone_offset) const {
        // We output meta data as first elements in the list. Note: In Python or
        // JSON we could output nested lists. In CSV mode this is not possible
        // and we rather stay compatible with CSV mode.
        std::vector<RRDDataMaker::value_type> result;
        result.reserve(values.size() + 3);
        result.emplace_back(start + timezone_offset);
        result.emplace_back(end + timezone_offset);
        result.emplace_back(step);
        result.insert(result.end(), values.cbegin(), values.cend());
        return result;
    }
};
}  // namespace

// TODO(mk): Convert all of the RPN expressions that are available in RRDTool
// and that have a different syntax then we have in our metrics system.
// >= --> GE. Or should we also go with GE instead of >=?
// Look at http://oss.oetiker.ch/rrdtool/doc/rrdgraph_rpn.en.html for details!
// NOLINTNEXTLINE(readability-function-cognitive-complexity)
std::vector<RRDDataMaker::value_type> RRDDataMaker::make(
    const std::string &host_name, const std::string &service_description,
    std::chrono::seconds timezone_offset) const {
    auto *logger = core_->loggerRRD();

    // We have an RPN like fs_used,1024,*.
    // One difficulty here: we do not know
    // the exact variable names. The filenames of the RRDs have several
    // characters replaced with "_". This is a one-way escaping where we cannot
    // get back the original variable values. So the cleaner (an probably
    // faster) way is to look for the names of variables within our RPN
    // expressions and create DEFs just for them - if the according RRD exists.
    std::string converted_rpn;  // convert foo.max -> foo-max
    MetricLocation location;
    std::string_view rpn{args_.rpn};
    auto next = [&rpn]() {
        auto token = rpn.substr(0, rpn.find(','));
        rpn.remove_prefix(std::min(rpn.size(), token.size() + 1));
        return token;
    };

    // map from RRD variable names to perf variable names. The latter ones
    // can contain several special characters (like @ and -) which the RRD
    // variables cannot. The variable names are constructed with "var_%u"
    unsigned next_variable_number = 0;
    std::set<std::string> touched_rrds;

    // default to MAX
    std::unique_ptr<CF> cf = std::make_unique<MaxCF>();
    while (!rpn.empty()) {
        // That seems unnecessarily complex since AFAIK, we handle
        // one DS at a time and only the simplest consolidation functions.
        auto token = next();
        if (!converted_rpn.empty()) {
            converted_rpn += ",";
        }
        if (!isVariableName(token)) {
            converted_rpn += token;
            continue;
        }

        // If the token looks like a variable name, then check if there is a
        // matching RRD. The token (assumed to be a metrics variable name) can
        // contain a
        // '.' like e.g. in 'user.max', which select the consolidation function
        // MAX.
        auto [var, cf_] = getVarAndCF(token);
        cf.swap(cf_);
        location = core_->metricLocation(host_name, service_description, var);
        // RRDTool does not allow a variable name to contain a '.' but
        // it allows an underscore. Therefore, we replace '.' by '_' here.
        std::string rrd_varname;
        if (location.path_.empty() || location.data_source_name_.empty()) {
            rrd_varname = replace_all(var.string(), ".", '_');
        } else {
            // We only support `var_1` in rpn_solve.
            rrd_varname = "var_" + std::to_string(++next_variable_number);
            touched_rrds.insert(location.path_.string());
        }
        converted_rpn += rrd_varname;
    }

    std::size_t dsname = 0;
    const auto dsname_view = std::string_view{location.data_source_name_};
    auto [ptr, ec] =
        std::from_chars(dsname_view.begin(), dsname_view.end(), dsname);
    if (ec != std::errc{}) {
        Warning(logger) << "Invalid location: " << location.data_source_name_;
        return {};
    }

    const auto rrdcached_socket = core_->paths()->rrdcached_socket();
    auto sock =
        RRDUDSSocket{rrdcached_socket, logger, RRDUDSSocket::verbosity::none};
    sock.connect();

    const auto fetch = std::ostringstream{}
                       << "FETCHBIN " << location.path_.string() << " " << *cf
                       << " " << args_.start_time << " " << args_.end_time
                       << " " << dsname << "\n";
    sendFetchBin(sock, fetch.view(), logger);
    const auto &&[status, header, rawdata] = recvFetchReply(sock);
    std::vector<double> values;
    values.reserve(rawdata.size());
    std::ranges::transform(
        rawdata, std::back_inserter(values), [converted_rpn](auto &&point) {
            return rrd_rpn_solve(mk::split(converted_rpn, ','),
                                 std::make_pair("var_1", point));
        });
    const auto &&[out_values, out_resolution] =
        rrd_consolidate(cf, values, header.step, args_.resolution);
    Data out;
    out.start = header.start;
    out.end = header.end;
    out.step = out_resolution;
    out.values = out_values;
    return out.as_vector(timezone_offset);
}
