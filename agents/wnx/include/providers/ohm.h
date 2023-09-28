// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#pragma once
#ifndef OHM_H
#define OHM_H

#include <filesystem>
#include <string>
#include <string_view>

#include "wnx/cma_core.h"
#include "providers/internal.h"
#include "providers/wmi.h"
#include "wnx/section_header.h"

namespace cma::provider {

std::filesystem::path GetOhmCliPath(const std::filesystem::path &dir) noexcept;
std::filesystem::path GetOhmCliPath() noexcept;

namespace ohm {
constexpr char kSepChar = ',';
constexpr std::string_view kExeModule = "OpenHardwareMonitorCLI.exe";
constexpr std::wstring_view kExeModuleWide = L"OpenHardwareMonitorCLI.exe";
constexpr std::wstring_view kDriverNameWide = L"winring0_1_2_0";
constexpr std::wstring_view kResetCommand =
    LR"(-command "Get-WmiObject -query \"Select * From __Namespace Where Name='OpenHardwareMonitor'\" -Namespace \"root\" | Remove-WmiObject")";
}  // namespace ohm

class OhmProvider final : public WmiBase {
public:
    OhmProvider(std::string_view name, char separator)
        : WmiBase(name, separator) {}
    void updateSectionStatus() override;

protected:
    std::string makeBody() override;
};

}  // namespace cma::provider

#endif  // OHM_H
