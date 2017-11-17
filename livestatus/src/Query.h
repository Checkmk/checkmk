// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#ifndef Query_h
#define Query_h

#include "config.h"  // IWYU pragma: keep
#include <chrono>
#include <cstdint>
#include <ctime>
#include <list>
#include <map>
#include <memory>
#include <string>
#include <unordered_set>
#include <vector>
#include "AndingFilter.h"
#include "Renderer.h"
#include "RendererBrokenCSV.h"
#include "Row.h"
#include "StatsColumn.h"
#include "Triggers.h"
#include "contact_fwd.h"
#include "data_encoding.h"
class Aggregator;
class Column;
class Filter;
class Logger;
class OutputBuffer;
class Table;

class Query {
public:
    Query(const std::list<std::string> &lines, Table *, Encoding data_encoding,
          size_t max_response_size, OutputBuffer &output);

    bool process();

    // NOTE: We cannot make this 'const' right now, it increments _current_line
    // and calls the non-const getAggregatorsFor() member function.
    bool processDataset(Row row);

    bool timelimitReached() const;
    void invalidRequest(const std::string &message) const;

    const contact *authUser() const { return _auth_user; }
    std::chrono::seconds timezoneOffset() const { return _timezone_offset; }

    const std::string *findValueForIndexing(
        const std::string &column_name) const;
    void findIntLimits(const std::string &column_name, int *lower,
                       int *upper) const;
    void optimizeBitmask(const std::string &column_name,
                         uint32_t *bitmask) const;
    const AndingFilter *filter() const { return _filter.get(); }
    const std::unordered_set<std::shared_ptr<Column>> &allColumns() const {
        return _all_columns;
    }

    enum class LogicalOperator { and_, or_ };

private:
    const Encoding _data_encoding;
    const size_t _max_response_size;
    OutputBuffer &_output;
    QueryRenderer *_renderer_query;
    Table *_table;
    bool _keepalive;
    using FilterStack = std::vector<std::unique_ptr<Filter>>;
    std::unique_ptr<AndingFilter> _filter;
    contact *_auth_user;
    std::unique_ptr<AndingFilter> _wait_condition;
    std::chrono::milliseconds _wait_timeout;
    Triggers::Kind _wait_trigger;
    Row _wait_object;
    CSVSeparators _separators;
    bool _show_column_headers;
    OutputFormat _output_format;
    int _limit;
    int _time_limit;
    time_t _time_limit_timeout;
    unsigned _current_line;
    std::chrono::seconds _timezone_offset;
    Logger *const _logger;
    std::vector<std::shared_ptr<Column>> _columns;
    std::vector<std::unique_ptr<StatsColumn>> _stats_columns;
    std::map<RowFragment, std::vector<std::unique_ptr<Aggregator>>>
        _stats_groups;
    std::unordered_set<std::shared_ptr<Column>> _all_columns;

    bool doStats() const;
    void doWait();
    void parseFilterLine(char *line, FilterStack &filters);
    void parseStatsLine(char *line);
    void parseStatsGroupLine(char *line);
    void parseAndOrLine(char *line, LogicalOperator op, FilterStack &filters);
    void parseNegateLine(char *line, FilterStack &filters);
    void parseStatsAndOrLine(char *line, LogicalOperator op);
    void parseStatsNegateLine(char *line);
    void parseColumnsLine(char *line);
    void parseColumnHeadersLine(char *line);
    void parseLimitLine(char *line);
    void parseTimelimitLine(char *line);
    void parseSeparatorsLine(char *line);
    void parseOutputFormatLine(char *line);
    void parseKeepAliveLine(char *line);
    void parseResponseHeaderLine(char *line);
    void parseAuthUserHeader(char *line);
    void parseWaitTimeoutLine(char *line);
    void parseWaitTriggerLine(char *line);
    void parseWaitObjectLine(char *line);
    void parseLocaltimeLine(char *line);
    void start(QueryRenderer &q);
    void finish(QueryRenderer &q);

    std::unique_ptr<Aggregator> createAggregator(const StatsColumn &sc) const;

    // NOTE: We cannot make this 'const' right now, it adds entries into
    // _stats_groups.
    const std::vector<std::unique_ptr<Aggregator>> &getAggregatorsFor(
        const RowFragment &groupspec);
};

#endif  // Query_h
