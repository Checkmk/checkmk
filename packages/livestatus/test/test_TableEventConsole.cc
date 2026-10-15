// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <chrono>
#include <cstddef>
#include <filesystem>
#include <functional>
#include <memory>
#include <sstream>
#include <string>
#include <system_error>
#include <thread>
#include <utility>
#include <vector>

#include "DummyMonitoringCore.h"
#include "asio/buffer.hpp"
#include "asio/io_context.hpp"
#include "asio/local/stream_protocol.hpp"
#include "asio/read.hpp"
#include "asio/write.hpp"
#include "gtest/gtest.h"
#include "livestatus/Interface.h"
#include "livestatus/Logger.h"
#include "livestatus/OutputBuffer.h"
#include "livestatus/ParsedQuery.h"
#include "livestatus/Query.h"
#include "livestatus/TableEventConsole.h"
#include "livestatus/TableEventConsoleEvents.h"
#include "livestatus/TableEventConsoleStatus.h"
#include "livestatus/User.h"

using namespace std::chrono_literals;

namespace {
class ECPaths : public IPaths {
public:
    explicit ECPaths(std::filesystem::path event_console_status_socket)
        : event_console_status_socket_{std::move(event_console_status_socket)} {
    }
    [[nodiscard]] std::filesystem::path log_file() const override { return {}; }
    [[nodiscard]] std::filesystem::path crash_reports_directory()
        const override {
        return {};
    }
    [[nodiscard]] std::filesystem::path license_usage_history_file()
        const override {
        return {};
    }
    [[nodiscard]] std::filesystem::path inventory_directory() const override {
        return {};
    }
    [[nodiscard]] std::filesystem::path structured_status_directory()
        const override {
        return {};
    }
    [[nodiscard]] std::filesystem::path robotmk_html_log_directory()
        const override {
        return {};
    }
    [[nodiscard]] std::filesystem::path logwatch_directory() const override {
        return {};
    }
    [[nodiscard]] std::filesystem::path prediction_directory() const override {
        return {};
    }
    [[nodiscard]] std::filesystem::path event_console_status_socket()
        const override {
        return event_console_status_socket_;
    }
    [[nodiscard]] std::filesystem::path livestatus_socket() const override {
        return {};
    }
    [[nodiscard]] std::filesystem::path history_file() const override {
        return {};
    }
    [[nodiscard]] std::filesystem::path history_archive_directory()
        const override {
        return {};
    }
    [[nodiscard]] std::filesystem::path rrd_multiple_directory()
        const override {
        return {};
    }
    [[nodiscard]] std::filesystem::path rrdcached_socket() const override {
        return {};
    }

private:
    std::filesystem::path event_console_status_socket_;
};

class ECCore : public DummyMonitoringCore {
public:
    explicit ECCore(std::filesystem::path event_console_status_socket)
        : event_console_status_socket_{std::move(event_console_status_socket)} {
    }
    [[nodiscard]] bool mkeventdEnabled() const override { return true; }
    [[nodiscard]] std::unique_ptr<const IPaths> paths() const override {
        return std::make_unique<ECPaths>(event_console_status_socket_);
    }
    [[nodiscard]] Logger *loggerLivestatus() const override {
        return Logger::getLogger("test");
    }

private:
    std::filesystem::path event_console_status_socket_;
};

// Records the request of a single client and sends it the given reply.
class FakeEventConsole {
public:
    FakeEventConsole(const std::filesystem::path &socket_path,
                     std::string reply)
        : acceptor_{io_context_,
                    asio::local::stream_protocol::endpoint{
                        socket_path.string()}}
        , reply_{std::move(reply)} {
        acceptor_.async_accept(socket_, [this](const std::error_code &ec) {
            if (ec) {
                return;
            }
            asio::async_read(socket_, asio::dynamic_buffer(request_),
                             [this](const std::error_code & /*ec*/,
                                    std::size_t /*bytes_transferred*/) {
                                 asio::async_write(
                                     socket_, asio::buffer(reply_),
                                     [this](const std::error_code & /*ec*/,
                                            std::size_t /*bytes_transferred*/) {
                                         socket_.close();
                                     });
                             });
        });
        // Don't hang forever when nobody connects.
        thread_ = std::jthread{[this] { io_context_.run_for(10s); }};
    }

    [[nodiscard]] std::string request() {
        thread_.join();
        return request_;
    }

private:
    asio::io_context io_context_;
    asio::local::stream_protocol::acceptor acceptor_;
    asio::local::stream_protocol::socket socket_{io_context_};
    std::string request_;
    std::string reply_;
    std::jthread thread_;
};

std::vector<std::string> filterLines(const std::string &request) {
    std::vector<std::string> result;
    std::istringstream is{request};
    for (std::string line; std::getline(is, line);) {
        if (line.starts_with("Filter: ")) {
            result.push_back(line);
        }
    }
    return result;
}

class TableEventConsoleTest : public ::testing::Test {
protected:
    // Keep this short, the path of a Unix domain socket is limited to 108
    // characters.
    const std::filesystem::path basepath_{
        std::filesystem::temp_directory_path() / "ec_tests"};

    void SetUp() override {
        std::filesystem::remove_all(basepath_);
        std::filesystem::create_directories(basepath_);
    }

    void TearDown() override { std::filesystem::remove_all(basepath_); }

    struct QueryResult {
        std::string error;
        std::vector<std::string> filters_sent_to_ec;
    };

    // By default, the EC replies with an empty table, i.e. only with a header
    // line, so its column names don't matter.
    QueryResult runQuery(TableEventConsole &table,
                         const std::vector<std::string> &query_lines,
                         std::string reply = "event_id\n") {
        const auto socket_path = basepath_ / "status";
        FakeEventConsole event_console{socket_path, std::move(reply)};
        const ECCore core{socket_path};
        OutputBuffer output{-1, [] { return false; }, core.loggerLivestatus()};
        Query query{
            ParsedQuery{query_lines, [&table] { return table.allColumns(); },
                        [&table, &core](const auto &colname) {
                            return table.column(colname, core);
                        }},
            table, core, output};

        table.answerQuery(query, NoAuthUser{}, core);

        return {.error = output.getError(),
                .filters_sent_to_ec = filterLines(event_console.request())};
    }

    std::vector<std::string> filtersSentToEC(
        const std::vector<std::string> &query_lines) {
        TableEventConsoleEvents table;
        auto result = runQuery(table, query_lines);
        EXPECT_EQ(result.error, "");
        return result.filters_sent_to_ec;
    }
};
}  // namespace

TEST_F(TableEventConsoleTest, ForwardsEqualityAndRegexFiltersOnStrings) {
    const std::vector<std::string> filters{
        "Filter: event_text = disk full",   //
        "Filter: event_text != disk",       //
        "Filter: event_text ~ ^disk",       //
        "Filter: event_text !~ ^net",       //
        "Filter: event_text =~ DISK FULL",  //
        "Filter: event_text !=~ DISK",      //
        "Filter: event_text ~~ ^DISK",      //
        "Filter: event_text !~~ ^NET",
    };

    EXPECT_EQ(filtersSentToEC(filters), filters);
}

class OrderingFilterOnStrings
    : public TableEventConsoleTest,
      public ::testing::WithParamInterface<std::string> {};

TEST_P(OrderingFilterOnStrings, IsDropped) {
    EXPECT_EQ(filtersSentToEC({"Filter: event_host " + GetParam() + " m"}),
              std::vector<std::string>{});
}

INSTANTIATE_TEST_SUITE_P(TableEventConsoleTest, OrderingFilterOnStrings,
                         ::testing::Values("<", ">=", ">", "<="));

// The UTF-8 encoding of \u00c5 contains the byte 0x85, but not \u0085.
TEST_F(TableEventConsoleTest, ForwardsNonASCIIValues) {
    const std::vector<std::string> filters{"Filter: event_text = \u00c5rhus"};

    EXPECT_EQ(filtersSentToEC(filters), filters);
}

// The EC would split such a value into several lines, so it could inject header
// lines into the request.
class ValueWithAPythonLineBoundary
    : public TableEventConsoleTest,
      public ::testing::WithParamInterface<std::string> {};

TEST_P(ValueWithAPythonLineBoundary, IsDropped) {
    EXPECT_EQ(filtersSentToEC({"Filter: event_text != x" + GetParam() +
                               "Columns: event_text"}),
              std::vector<std::string>{});
}

INSTANTIATE_TEST_SUITE_P(TableEventConsoleTest, ValueWithAPythonLineBoundary,
                         ::testing::Values("\r", "\v", "\f", "\x1c", "\x1d",
                                           "\x1e", "\u0085", "\u2028",
                                           "\u2029"));

TEST_F(TableEventConsoleTest, ForwardsEqualityAndOrderingFiltersOnEventId) {
    const std::vector<std::string> filters{
        "Filter: event_id = 42",   //
        "Filter: event_id != 43",  //
        "Filter: event_id < 50",   //
        "Filter: event_id >= 40",  //
        "Filter: event_id > 41",   //
        "Filter: event_id <= 49",
    };

    EXPECT_EQ(filtersSentToEC(filters), filters);
}

TEST_F(TableEventConsoleTest, ForwardsLenientlyParsedEventIdAsPlainInt) {
    EXPECT_EQ(filtersSentToEC({"Filter: event_id >= 5.0"}),
              std::vector<std::string>{"Filter: event_id >= 5"});
}

class BitMaskFilterOnEventId
    : public TableEventConsoleTest,
      public ::testing::WithParamInterface<std::string> {};

TEST_P(BitMaskFilterOnEventId, IsDropped) {
    EXPECT_EQ(filtersSentToEC({"Filter: event_id " + GetParam() + " 4"}),
              std::vector<std::string>{});
}

INSTANTIATE_TEST_SUITE_P(TableEventConsoleTest, BitMaskFilterOnEventId,
                         ::testing::Values("~", "!~", "=~", "!=~", "~~",
                                           "!~~"));

TEST_F(TableEventConsoleTest, ForwardsTheRangeOfADisjunctionOnEventId) {
    EXPECT_EQ(filtersSentToEC({
                  "Filter: event_id = 3",
                  "Filter: event_id = 7",
                  "Filter: event_id = 5",
                  "Or: 3",
              }),
              (std::vector<std::string>{
                  "Filter: event_id >= 3",
                  "Filter: event_id <= 7",
              }));
}

TEST_F(TableEventConsoleTest,
       ForwardsADisjunctionOnASingleEventIdAsAnEquality) {
    EXPECT_EQ(filtersSentToEC({
                  "Filter: event_id = 5",
                  "Filter: event_id >= 5",
                  "Filter: event_id <= 5",
                  "And: 2",
                  "Or: 2",
              }),
              std::vector<std::string>{"Filter: event_id = 5"});
}

TEST_F(TableEventConsoleTest, ForwardsTheCommonValueOfADisjunctionOnStrings) {
    EXPECT_EQ(filtersSentToEC({
                  "Filter: event_host = a",
                  "Filter: event_text ~ disk",
                  "And: 2",
                  "Filter: event_host = a",
                  "Filter: event_state = 2",
                  "And: 2",
                  "Or: 2",
              }),
              std::vector<std::string>{"Filter: event_host = a"});
}

TEST_F(TableEventConsoleTest, DropsDisjunctionsWithoutCommonRestriction) {
    EXPECT_EQ(filtersSentToEC({
                  "Filter: event_id <= 5",
                  "Filter: event_id >= 5",
                  "Or: 2",
              }),
              std::vector<std::string>{});
}

TEST_F(TableEventConsoleTest, ReportsAnECFailingBeforeItReplies) {
    TableEventConsoleEvents table;

    EXPECT_TRUE(runQuery(table, {"Filter: event_text ~ \\p{Lu}"}, "")
                    .error.ends_with("received no reply\n"));
}

TEST_F(TableEventConsoleTest, AnswersQueriesOnTablesWithoutGreppingColumns) {
    TableEventConsoleStatus table;

    // The empty disjunction is a conjunct which doesn't mention any column.
    EXPECT_EQ(runQuery(table, {"Or: 0"}).error, "");
}
