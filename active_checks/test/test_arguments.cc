// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <cstdint>
#include <optional>
#include <string>
#include <utility>

#include "active_checks/arguments.h"
#include "gtest/gtest.h"

using check_mkevents::parse_number;
using check_mkevents::parse_port;
using check_mkevents::parse_remote;

namespace {

// The parsed remote address as "ADDRESS PORT", or "invalid".
std::string describe(
    const std::optional<std::pair<std::string, uint16_t>> &remote) {
    return remote ? remote->first + " " + std::to_string(remote->second)
                  : "invalid";
}

// A remote address and how it's parsed with the default port 6558
using RemoteAndParsed = std::pair<std::string, std::string>;

}  // namespace

TEST(ParseNumber, MaximumIsAccepted) {
    const auto number = parse_number("3600", 3600);

    EXPECT_EQ(number, std::optional<unsigned long>{3600});
}

TEST(ParseNumber, LeadingZerosDontCountEvenBeyondTheDigitsOfTheMaximum) {
    const auto number = parse_number("00001", 3600);

    EXPECT_EQ(number, std::optional<unsigned long>{1});
}

class InvalidNumber : public testing::TestWithParam<std::string> {};

TEST_P(InvalidNumber, IsRejected) {
    const auto number = parse_number(GetParam(), 3600);

    EXPECT_EQ(number, std::nullopt);
}

INSTANTIATE_TEST_SUITE_P(ParseNumber, InvalidNumber,
                         testing::Values("", "0", "abc", "+2", " 2", "2 ", "-1",
                                         "3601"));

TEST(ParsePort, HighestPortIsAccepted) {
    const auto port = parse_port("65535");

    EXPECT_EQ(port, std::optional<uint16_t>{65535});
}

TEST(ParsePort, PortAbove65535IsRejected) {
    const auto port = parse_port("65536");

    EXPECT_EQ(port, std::nullopt);
}

TEST(ParseRemote, HostWithoutAPortGetsTheDefaultOne) {
    const auto remote = parse_remote("myhost", 6559);

    EXPECT_EQ(describe(remote), "myhost 6559");
}

TEST(ParseRemote, PortOfTheHostOverridesTheDefaultOne) {
    const auto remote = parse_remote("myhost:6560", 6559);

    EXPECT_EQ(describe(remote), "myhost 6560");
}

TEST(ParseRemote, EmptyPortMeansTheDefaultOne) {
    const auto remote = parse_remote("myhost:", 6559);

    EXPECT_EQ(describe(remote), "myhost 6559");
}

TEST(ParseRemote, LeadingZerosOfThePortDontCount) {
    const auto remote = parse_remote("myhost:0006560", 6558);

    EXPECT_EQ(describe(remote), "myhost 6560");
}

class FurtherColonsAroundThePort
    : public testing::TestWithParam<RemoteAndParsed> {};

TEST_P(FurtherColonsAroundThePort, DontCount) {
    const auto &[argument, parsed] = GetParam();

    const auto remote = parse_remote(argument, 6558);

    EXPECT_EQ(describe(remote), parsed);
}

INSTANTIATE_TEST_SUITE_P(
    ParseRemote, FurtherColonsAroundThePort,
    testing::Values(RemoteAndParsed{"myhost::6560", "myhost 6560"},
                    RemoteAndParsed{"myhost:6560::", "myhost 6560"},
                    RemoteAndParsed{"myhost::", "myhost 6558"},
                    RemoteAndParsed{"[2001:db8::1]::6560",
                                    "2001:db8::1 6560"}));

// Even if the last group looks like a port
class IPv6AddressWithoutBrackets : public testing::TestWithParam<std::string> {
};

TEST_P(IPv6AddressWithoutBrackets, GetsTheDefaultPort) {
    const auto remote = parse_remote(GetParam(), 6558);

    EXPECT_EQ(describe(remote), GetParam() + " 6558");
}

INSTANTIATE_TEST_SUITE_P(ParseRemote, IPv6AddressWithoutBrackets,
                         testing::Values("2001:db8::1", "fe80::1%eth0",
                                         "cafe::6558"));

class IPv6AddressInBrackets : public testing::TestWithParam<RemoteAndParsed> {};

TEST_P(IPv6AddressInBrackets, MayHaveAPort) {
    const auto &[argument, parsed] = GetParam();

    const auto remote = parse_remote(argument, 6558);

    EXPECT_EQ(describe(remote), parsed);
}

INSTANTIATE_TEST_SUITE_P(
    ParseRemote, IPv6AddressInBrackets,
    testing::Values(RemoteAndParsed{"[2001:db8::1]:6560", "2001:db8::1 6560"},
                    RemoteAndParsed{"[2001:db8::1]", "2001:db8::1 6558"},
                    RemoteAndParsed{"[2001:db8::1]:", "2001:db8::1 6558"},
                    RemoteAndParsed{"[fe80::1%eth0]:6560",
                                    "fe80::1%eth0 6560"}));

// A zone can't contain a colon (RFC 6874), so the port needs no brackets.
class ColonAfterTheZoneOfAnIPv6Address
    : public testing::TestWithParam<RemoteAndParsed> {};

TEST_P(ColonAfterTheZoneOfAnIPv6Address, StartsThePort) {
    const auto &[argument, parsed] = GetParam();

    const auto remote = parse_remote(argument, 6558);

    EXPECT_EQ(describe(remote), parsed);
}

INSTANTIATE_TEST_SUITE_P(
    ParseRemote, ColonAfterTheZoneOfAnIPv6Address,
    testing::Values(RemoteAndParsed{"fe80::1%eth0:6560", "fe80::1%eth0 6560"},
                    RemoteAndParsed{"fe80::1%eth0:", "fe80::1%eth0 6558"}));

class ColonsAfterAnIPv6AddressWithoutBrackets
    : public testing::TestWithParam<RemoteAndParsed> {};

TEST_P(ColonsAfterAnIPv6AddressWithoutBrackets, MeanTheDefaultPort) {
    const auto &[argument, parsed] = GetParam();

    const auto remote = parse_remote(argument, 6558);

    EXPECT_EQ(describe(remote), parsed);
}

INSTANTIATE_TEST_SUITE_P(
    ParseRemote, ColonsAfterAnIPv6AddressWithoutBrackets,
    testing::Values(RemoteAndParsed{"2001:db8::1:", "2001:db8::1 6558"},
                    RemoteAndParsed{"2001:db8::1::", "2001:db8::1 6558"},
                    RemoteAndParsed{"2001:db8:::", "2001:db8:: 6558"}));

class InvalidRemoteAddress : public testing::TestWithParam<std::string> {};

TEST_P(InvalidRemoteAddress, IsRejected) {
    const auto remote = parse_remote(GetParam(), 6558);

    EXPECT_EQ(describe(remote), "invalid");
}

INSTANTIATE_TEST_SUITE_P(
    ParseRemote, InvalidRemoteAddress,
    testing::Values("", ":6558", "localhost:abc", "localhost:70000",
                    "localhost:+80", "localhost: 80", "localhost:0",
                    "localhost:6558:x", "[::1", "[]:6558", "[::1]6558",
                    "[::1]:abc", "[localhost]:6558", "[127.0.0.1]:6558",
                    "[::1%]:6558", "[fe80::1%eth0:6558]", "fe80::1%eth0]:6558",
                    "fe80::1%:6558"));
