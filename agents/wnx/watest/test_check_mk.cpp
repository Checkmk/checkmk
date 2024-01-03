//
// test-tools.cpp :

#include "pch.h"

#include "providers/check_mk.h"
#include "wnx/cfg.h"

namespace cma::provider {

TEST(CheckMkHeader, GetTimeZone) {
    constexpr std::chrono::system_clock::time_point tp;
    EXPECT_EQ(GetTimezoneOffset(), "+0100");
}

TEST(CheckMkHeader, IsoTime) {
    constexpr std::chrono::system_clock::time_point tp;
    EXPECT_EQ(PrintIsoTime(tp), "1970-01-01T00:00:00+0100");
}

TEST(CheckMkHeader, Convert) {
    EXPECT_EQ(AddressToCheckMkString("127.0.0.1"), "127.0.0.1");
    EXPECT_EQ(AddressToCheckMkString("10.1.2.3"), "10.1.2.3");
    EXPECT_EQ(AddressToCheckMkString("2001:0db8:85a3:0000:0000:8a2e:0370:7334"),
              "2001:0db8:85a3:0000:0000:8a2e:0370:7334");
    EXPECT_EQ(AddressToCheckMkString("10.1.2.3/4"), "10.1.2.3/4");
}

}  // namespace cma::provider
