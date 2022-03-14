// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// provides basic api to start and stop service

#pragma once
#ifndef ohm_h__
#define ohm_h__

#include <filesystem>
#include <string>
#include <string_view>

#include "cma_core.h"
#include "providers/internal.h"
#include "providers/wmi.h"
#include "section_header.h"

namespace cma::provider {

std::filesystem::path GetOhmCliPath(const std::filesystem::path &dir) noexcept;
std::filesystem::path GetOhmCliPath() noexcept;

namespace ohm {
constexpr std::string_view kExeModule = "OpenHardwareMonitorCLI.exe";
constexpr std::wstring_view kExeModuleWide = L"OpenHardwareMonitorCLI.exe";
constexpr std::wstring_view kDriverNameWide = L"winring0_1_2_0";
constexpr std::wstring_view kResetCommand =
    LR"(-command "Get-WmiObject -query \"Select * From __Namespace Where Name='OpenHardwareMonitor'\" -Namespace \"root\" | Remove-WmiObject")";
};  // namespace ohm

// openhardwaremonitor:
class OhmProvider : public Wmi {
public:
    OhmProvider(const std::string &Name, char Separator)
        : Wmi(Name, Separator) {}

    virtual void loadConfig();

    virtual void updateSectionStatus();

protected:
    std::string makeBody() override;

#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class OhmTest;
    FRIEND_TEST(OhmTest, Base);
#endif
};

}  // namespace cma::provider

#endif  // ohm_h__
