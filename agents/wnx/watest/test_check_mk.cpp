//
// test-tools.cpp :

#include "pch.h"

#include "providers/check_mk.h"
#include "wnx/cfg.h"

namespace cma::provider {

namespace {

/// This function is used to calculate the current timezone offset
std::string CalcCurrentOffset() {
    int hours = 0;
    _get_daylight(&hours);
    long tz = 0;
    _get_timezone(&tz);
    return fmt::format("{:+05}", tz * -100 / 60 / 60 + hours * 100);
}

}  // namespace

TEST(CheckMkHeader, IsoTime) {
    constexpr std::chrono::system_clock::time_point tp;
    EXPECT_EQ(PrintIsoTime(tp),
              fmt::format("1970-01-01T01:00:00{}", CalcCurrentOffset()));
}

TEST(CheckMkHeader, Convert) {
    EXPECT_EQ(AddressToCheckMkString("127.0.0.1"), "127.0.0.1");
    EXPECT_EQ(AddressToCheckMkString("10.1.2.3"), "10.1.2.3");
    EXPECT_EQ(AddressToCheckMkString("2001:0db8:85a3:0000:0000:8a2e:0370:7334"),
              "2001:0db8:85a3:0000:0000:8a2e:0370:7334");
    EXPECT_EQ(AddressToCheckMkString("10.1.2.3/4"), "10.1.2.3/4");
}

}  // namespace cma::provider
