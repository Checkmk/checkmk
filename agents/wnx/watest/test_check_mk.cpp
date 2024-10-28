//
// test-tools.cpp :

#include "pch.h"

#include "providers/check_mk.h"
#include "wnx/cfg.h"
using sys_clock = std::chrono::system_clock;

namespace cma::provider {
namespace {

std::tm get_summer_time() {
    std::tm tm_dst = {
        .tm_sec = 1,
        .tm_min = 2,
        .tm_hour = 3,
        .tm_mday = 2,
        .tm_mon = 7,  // summer
        .tm_year = 124,
    };
    tm_dst.tm_isdst = -1;  // Use DST value from local time zone
    return tm_dst;
}

std::tm get_winter_time() {
    std::tm tm_no_dst = {
        .tm_sec = 1,
        .tm_min = 2,
        .tm_hour = 3,
        .tm_mday = 2,
        .tm_mon = 11,  // winter
        .tm_year = 124,
    };
    tm_no_dst.tm_isdst = -1;  // Use DST value from local time zone
    return tm_no_dst;
}

std::string print_time(std::tm &tm) {
    return fmt::format("{}-{:02}-{:02}T{:02}:{:02}:{:02}", 1900 + tm.tm_year,
                       tm.tm_mon + 1, tm.tm_mday, tm.tm_hour, tm.tm_min,
                       tm.tm_sec);
}

std::chrono::time_point<std::chrono::system_clock> get_winter_tp() {
    auto std_tm = get_winter_time();
    auto tp = sys_clock::from_time_t(std::mktime(&std_tm));
    return tp;
}

std::chrono::time_point<std::chrono::system_clock> get_summer_tp() {
    auto std_tm = get_summer_time();
    auto tp = sys_clock::from_time_t(std::mktime(&std_tm));
    return tp;
}
}  // namespace

TEST(CheckMkHeader, GetTimezoneOffset) {
    EXPECT_EQ("+0100", GetTimezoneOffset(get_winter_tp()));
    EXPECT_EQ("+0200", GetTimezoneOffset(get_summer_tp()));
}

TEST(CheckMkHeader, IsoTime) {
    constexpr sys_clock::time_point tp_1970;
    EXPECT_EQ(PrintIsoTime(tp_1970),
              fmt::format("1970-01-01T01:00:00{}", GetTimezoneOffset(tp_1970)));

    for (auto the_time : {
             get_summer_time(),
             get_winter_time(),
         }) {
        auto tp = sys_clock::from_time_t(std::mktime(&the_time));
        EXPECT_EQ(PrintIsoTime(tp), fmt::format("{}{}", print_time(the_time),
                                                GetTimezoneOffset(tp)));
    }
}

TEST(CheckMkHeader, Convert) {
    EXPECT_EQ(AddressToCheckMkString("127.0.0.1"), "127.0.0.1");
    EXPECT_EQ(AddressToCheckMkString("10.1.2.3"), "10.1.2.3");
    EXPECT_EQ(AddressToCheckMkString("2001:0db8:85a3:0000:0000:8a2e:0370:7334"),
              "2001:0db8:85a3:0000:0000:8a2e:0370:7334");
    EXPECT_EQ(AddressToCheckMkString("10.1.2.3/4"), "10.1.2.3/4");
}

}  // namespace cma::provider
