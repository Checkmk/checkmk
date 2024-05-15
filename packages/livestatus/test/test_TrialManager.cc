// Copyright (C) 2019 Checkmk GmbH - License: Check_MK Enterprise License
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <chrono>
#include <ratio>
#include <stdexcept>
#include <string>

#include "gtest/gtest.h"
#include "livestatus/TrialManager.h"

namespace {
auto recently_from(std::chrono::system_clock::time_point now) {
    return now - TrialManager::trialPeriod() + std::chrono::days{1};
}
auto long_ago_from(std::chrono::system_clock::time_point now) {
    return now - TrialManager::trialPeriod() - std::chrono::days{1};
}
auto few_services() { return TrialManager::maxServicesInTrialPeriod(); }
auto many_services() { return TrialManager::maxServicesInTrialPeriod() + 1; }
}  // namespace

TEST(TrialManager, InTrialUnlicensedFewHosts) {
    auto now = std::chrono::system_clock::now();
    const TrialManager tm{recently_from(now), false};
    // NOLINTNEXTLINE(hicpp-avoid-goto,cppcoreguidelines-avoid-goto)
    EXPECT_NO_THROW(tm.validateServiceCount(now, few_services()));
}

TEST(TrialManager, InTrialUnlicensedManyHosts) {
    auto now = std::chrono::system_clock::now();
    const TrialManager tm{recently_from(now), false};
    // NOLINTNEXTLINE(hicpp-avoid-goto,cppcoreguidelines-avoid-goto)
    EXPECT_NO_THROW(tm.validateServiceCount(now, many_services()));
}

TEST(TrialManager, OutsideTrialUnlicensedFewHosts) {
    auto now = std::chrono::system_clock::now();
    const TrialManager tm{long_ago_from(now), false};
    // NOLINTNEXTLINE(hicpp-avoid-goto,cppcoreguidelines-avoid-goto)
    EXPECT_NO_THROW(tm.validateServiceCount(now, few_services()));
}

TEST(TrialManager, OutsideTrialUnlicensedManyHosts) {
    auto now = std::chrono::system_clock::now();
    const TrialManager tm{long_ago_from(now), false};
    // NOLINTNEXTLINE(hicpp-avoid-goto,cppcoreguidelines-avoid-goto)
    EXPECT_THROW(tm.validateServiceCount(now, many_services()),
                 std::runtime_error);
}

TEST(TrialManager, InTrialLicensedFewHosts) {
    auto now = std::chrono::system_clock::now();
    const TrialManager tm{recently_from(now), true};
    // NOLINTNEXTLINE(hicpp-avoid-goto,cppcoreguidelines-avoid-goto)
    EXPECT_NO_THROW(tm.validateServiceCount(now, few_services()));
}

TEST(TrialManager, InTrialLicensedManyHosts) {
    auto now = std::chrono::system_clock::now();
    const TrialManager tm{recently_from(now), true};
    // NOLINTNEXTLINE(hicpp-avoid-goto,cppcoreguidelines-avoid-goto)
    EXPECT_NO_THROW(tm.validateServiceCount(now, many_services()));
}

TEST(TrialManager, OutsideTrialLicensedFewHosts) {
    auto now = std::chrono::system_clock::now();
    const TrialManager tm{long_ago_from(now), true};
    // NOLINTNEXTLINE(hicpp-avoid-goto,cppcoreguidelines-avoid-goto)
    EXPECT_NO_THROW(tm.validateServiceCount(now, few_services()));
}

TEST(TrialManager, OutsideTrialLicensedManyHosts) {
    auto now = std::chrono::system_clock::now();
    const TrialManager tm{long_ago_from(now), true};
    // NOLINTNEXTLINE(hicpp-avoid-goto,cppcoreguidelines-avoid-goto)
    EXPECT_NO_THROW(tm.validateServiceCount(now, many_services()));
}
