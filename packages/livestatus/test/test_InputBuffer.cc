// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <sys/socket.h>
#include <sys/types.h>
#include <unistd.h>

#include <array>
#include <chrono>
#include <cstddef>
#include <optional>
#include <string>
#include <vector>

#include "gtest/gtest.h"
#include "livestatus/InputBuffer.h"
#include "livestatus/Logger.h"

using namespace std::chrono_literals;
using strings = std::vector<std::string>;

namespace {
// Mirrors the initial_buffer_size of the implementation: the buffer starts out
// with this many bytes and doubles whenever a single line does not fit.
constexpr size_t initial_buffer_size = 4096;
}  // namespace

class InputBufferTest : public ::testing::Test {
public:
    // Hands `input` to the buffer through a socket pair and closes the writing
    // end, so that the EOF following the data is well-defined. Nobody reads
    // while we write, so the input has to stay well below the socket buffer
    // size.
    void feed(const std::string &input) {
        std::array<int, 2> fds{};
        ASSERT_EQ(0, ::socketpair(AF_UNIX, SOCK_STREAM, 0, fds.data()));
        fd_ = fds[0];
        for (size_t written = 0; written < input.size();) {
            const ssize_t count =
                ::write(fds[1], input.data() + written, input.size() - written);
            ASSERT_GT(count, 0);
            written += static_cast<size_t>(count);
        }
        ASSERT_EQ(0, ::close(fds[1]));
        buffer_.emplace(
            fd_, [] { return false; }, logger_, timeout, timeout);
    }

    InputBuffer &buffer() { return buffer_.value(); }

protected:
    // The buffer logs about e.g. lines it skips, which is not what we are
    // testing here and would only clutter the test output.
    void SetUp() override { logger_->setLevel(LogLevel::error); }

    void TearDown() override {
        buffer_.reset();
        if (fd_ != -1) {
            ::close(fd_);
        }
    }

private:
    // Never fires for data which is already there, but keeps a broken
    // implementation from blocking the whole test run.
    static constexpr auto timeout = 10s;

    Logger *const logger_{Logger::getLogger("test.InputBuffer")};
    int fd_{-1};
    std::optional<InputBuffer> buffer_;
};

TEST_F(InputBufferTest, ReadsASingleRequest) {
    feed("GET hosts\nColumns: name state\n\n");

    EXPECT_EQ(InputBuffer::Result::request_read, buffer().readRequest());
    EXPECT_EQ(strings({"GET hosts", "Columns: name state"}),
              buffer().getLines());
}

TEST_F(InputBufferTest, ReadsTwoRequestsFromTheSameData) {
    feed("GET hosts\n\nGET services\n\n");

    EXPECT_EQ(InputBuffer::Result::request_read, buffer().readRequest());
    EXPECT_EQ(strings({"GET hosts"}), buffer().getLines());
    EXPECT_EQ(InputBuffer::Result::request_read, buffer().readRequest());
    EXPECT_EQ(strings({"GET services"}), buffer().getLines());
}

TEST_F(InputBufferTest, ReportsEofOnAnIdleConnection) {
    feed("");

    EXPECT_EQ(InputBuffer::Result::eof, buffer().readRequest());
}

TEST_F(InputBufferTest, ReportsAnEmptyRequest) {
    feed("\n");

    EXPECT_EQ(InputBuffer::Result::empty_request, buffer().readRequest());
}

TEST_F(InputBufferTest, AcceptsARequestEndedByEofInsteadOfAnEmptyLine) {
    feed("GET hosts\n");

    EXPECT_EQ(InputBuffer::Result::request_read, buffer().readRequest());
    EXPECT_EQ(strings({"GET hosts"}), buffer().getLines());
}

TEST_F(InputBufferTest, RejectsARequestCutOffInTheMiddleOfALine) {
    feed("GET hosts");

    EXPECT_EQ(InputBuffer::Result::unexpected_eof, buffer().readRequest());
}

TEST_F(InputBufferTest, StripsTrailingWhitespace) {
    feed("GET hosts \t\n\n");

    EXPECT_EQ(InputBuffer::Result::request_read, buffer().readRequest());
    EXPECT_EQ(strings({"GET hosts"}), buffer().getLines());
}

TEST_F(InputBufferTest, IgnoresALineOfNothingButWhitespace) {
    feed("GET hosts\n \t \n\n");

    EXPECT_EQ(InputBuffer::Result::request_read, buffer().readRequest());
    EXPECT_EQ(strings({"GET hosts"}), buffer().getLines());
}

TEST_F(InputBufferTest, KeepsALineEndingInANonAsciiUtf8Byte) {
    // "Café", whose trailing byte 0xa9 is negative when char is signed. Such a
    // byte has to be cast before it is handed to isspace(), otherwise the
    // behavior is undefined and the character may be stripped as whitespace.
    const std::string line{"Filter: alias = Caf\xc3\xa9"};
    feed("GET hosts\n" + line + "\n\n");

    EXPECT_EQ(InputBuffer::Result::request_read, buffer().readRequest());
    EXPECT_EQ(strings({"GET hosts", line}), buffer().getLines());
}

TEST_F(InputBufferTest, RejectsInvalidUtf8) {
    feed("GET hosts\nFilter: alias = \xff\xfe\n\n");

    EXPECT_EQ(InputBuffer::Result::invalid_utf8, buffer().readRequest());
}

TEST_F(InputBufferTest, ReadsALineLongerThanTheBuffer) {
    // The first line moves the read position off zero, so completing the second
    // one makes the buffer first shift its unprocessed rest to the front and
    // then grow -- the two spots which used to index past the end.
    const std::string line{"Filter: name = " +
                           std::string(initial_buffer_size + 1000, 'x')};
    feed("GET hosts\n" + line + "\n\n");

    EXPECT_EQ(InputBuffer::Result::request_read, buffer().readRequest());
    EXPECT_EQ(strings({"GET hosts", line}), buffer().getLines());
}
