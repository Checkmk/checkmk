// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef Query_h
#define Query_h

#include <bitset>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <list>
#include <map>
#include <memory>
#include <optional>
#include <string>
#include <unordered_set>
#include <utility>
#include <vector>

#include "livestatus/Aggregator.h"  // IWYU pragma: keep
#include "livestatus/Filter.h"
#include "livestatus/Renderer.h"
#include "livestatus/RendererBrokenCSV.h"
#include "livestatus/Row.h"
#include "livestatus/StatsColumn.h"
#include "livestatus/Triggers.h"
#include "livestatus/User.h"
class Column;
class Logger;
class OutputBuffer;
class Table;

class Query {
public:
    Query(const std::list<std::string> &lines, Table &table,
          Encoding data_encoding, size_t max_response_size,
          OutputBuffer &output, Logger *logger);

    bool process();

    // NOTE: We cannot make this 'const' right now, it increments _current_line
    // and calls the non-const getAggregatorsFor() member function.
    bool processDataset(Row row);

    bool timelimitReached() const;
    void invalidRequest(const std::string &message) const;
    void badGateway(const std::string &message) const;

    std::chrono::seconds timezoneOffset() const { return _timezone_offset; }

    std::unique_ptr<Filter> partialFilter(const std::string &message,
                                          columnNamePredicate predicate) const;
    std::optional<std::string> stringValueRestrictionFor(
        const std::string &column_name) const;
    std::optional<int32_t> greatestLowerBoundFor(
        const std::string &column_name) const;
    std::optional<int32_t> leastUpperBoundFor(
        const std::string &column_name) const;
    std::optional<std::bitset<32>> valueSetLeastUpperBoundFor(
        const std::string &column_name) const;

    const std::unordered_set<std::shared_ptr<Column>> &allColumns() const {
        return _all_columns;
    }

private:
    using LogicalConnective =
        std::function<std::unique_ptr<Filter>(Filter::Kind, const Filters &)>;

    const Encoding _data_encoding;
    const size_t _max_response_size;
    OutputBuffer &_output;
    QueryRenderer *_renderer_query;
    Table &_table;
    bool _keepalive;
    using FilterStack = Filters;
    std::unique_ptr<Filter> _filter;
    std::unique_ptr<const User> user_;
    std::unique_ptr<Filter> _wait_condition;
    std::chrono::milliseconds _wait_timeout;
    Triggers::Kind _wait_trigger;
    Row _wait_object;
    CSVSeparators _separators;
    bool _show_column_headers;
    OutputFormat _output_format;
    int _limit;
    std::optional<
        std::pair<std::chrono::seconds, std::chrono::steady_clock::time_point>>
        _time_limit;
    unsigned _current_line;
    std::chrono::seconds _timezone_offset;
    Logger *const _logger;
    std::vector<std::shared_ptr<Column>> _columns;
    using StatsColumns = std::vector<std::unique_ptr<StatsColumn>>;
    StatsColumns _stats_columns;
    std::map<RowFragment, std::vector<std::unique_ptr<Aggregator>>>
        _stats_groups;
    using ColumnSet = std::unordered_set<std::shared_ptr<Column>>;
    ColumnSet _all_columns;

    bool doStats() const;
    void doWait();
    void parseFilterLine(char *line, FilterStack &filters,
                         ColumnSet &all_columnsa);
    void parseStatsLine(char *line, StatsColumns &stats_columns,
                        ColumnSet &all_columns);
    static void parseAndOrLine(char *line, Filter::Kind kind,
                               const LogicalConnective &connective,
                               FilterStack &filters);
    static void parseNegateLine(char *line, FilterStack &filters);
    static void parseStatsAndOrLine(char *line,
                                    const LogicalConnective &connective,
                                    StatsColumns &stats_columns);
    static void parseStatsNegateLine(char *line, StatsColumns &stats_columns);
    void parseColumnsLine(const char *line, ColumnSet &all_columns);
    void parseColumnHeadersLine(char *line);
    void parseLimitLine(char *line);
    void parseTimelimitLine(char *line);
    void parseSeparatorsLine(char *line);
    void parseOutputFormatLine(const char *line);
    void parseKeepAliveLine(char *line);
    void parseResponseHeaderLine(char *line);
    void parseAuthUserHeader(const char *line);
    void parseWaitTimeoutLine(char *line);
    void parseWaitTriggerLine(char *line);
    void parseWaitObjectLine(const char *line);
    void parseLocaltimeLine(char *line);
    void start(QueryRenderer &q);
    void finish(QueryRenderer &q);

    // NOTE: We cannot make this 'const' right now, it adds entries into
    // _stats_groups.
    const std::vector<std::unique_ptr<Aggregator>> &getAggregatorsFor(
        const RowFragment &groupspec);
};

#endif  // Query_h
