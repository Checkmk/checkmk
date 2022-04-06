// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// Provides basic section formatting
// header with optional separator
// empty header
// local header
// default names
// in the future we will add something here

#pragma once

#ifndef section_header_h__
#define section_header_h__

#include <string>
#include <string_view>

#include "logger.h"

namespace cma::section {

// Usual Section
constexpr std::string_view kLeftBracket{"<<<"};
constexpr std::string_view kRightBracket{">>>"};
constexpr std::string_view kLeftSeparator{":sep("};
constexpr std::string_view kRightSeparator{")"};

// special markers
constexpr std::string_view kFooter4{"<<<<>>>>"};
constexpr std::string_view kFooter4Left{"<<<<"};
constexpr std::string_view kFooter4Right{">>>>"};
constexpr std::string_view kFooterStd{"<<<>>>"};

// Sub Section(as for WMI)
constexpr std::string_view kLeftSubSectionBracket{"["};
constexpr std::string_view kRightSubSectionBracket{"]"};

// section names
// usually also used as a names in makeHeader
// special name: section must use own name
constexpr std::string_view kUseEmbeddedName = {"*"};

constexpr std::string_view kUptimeName{"uptime"};
constexpr std::string_view kDfName{"df"};
constexpr std::string_view kMemName{"mem"};
constexpr std::string_view kSystemTime{"systemtime"};
constexpr std::string_view kServices{"services"};
constexpr std::string_view kCheckMk{"check_mk"};
constexpr std::string_view kCheckMkCtlStatus{"cmk_agent_ctl_status:sep(0)"};
constexpr std::string_view kAgentPlugins{"checkmk_agent_plugins_win:sep(0)"};

constexpr std::string_view kPlugins{"plugins"};  // NOT used in makeHeader
constexpr std::string_view kLocal{"local"};      // NOT used in makeHeader
constexpr std::string_view kLocalHeader{"local:sep(0)"};

constexpr std::string_view kMrpe{"mrpe"};
constexpr std::string_view kOhm{"openhardwaremonitor"};
constexpr std::string_view kSkype{"skype"};
constexpr std::string_view kSpool{"spool"};

constexpr std::string_view kLogWatchEventName{"logwatch"};

constexpr std::string_view kPsName{"ps"};
constexpr std::string_view kFileInfoName{"fileinfo"};

constexpr char kTabSeparator = '\t';
constexpr std::wstring_view kTabSeparatorString = L"\t";

constexpr char kPipeSeparator = '|';
constexpr std::wstring_view kPipeSeparatorString = L"|";

constexpr char kCommaSeparator = ',';
constexpr std::wstring_view kCommaSeparatorString = L",";

// Build standard header with optional Separator
// <<<section_name>>>\n or
// <<<section_name:sep(9)>>>\n
std::string MakeHeader(std::string_view name, char separator) noexcept;
std::string MakeHeader(std::string_view name) noexcept;

// [sub_section_name]
std::string MakeSubSectionHeader(std::string_view name) noexcept;
std::string MakeEmptyHeader();

std::string MakeLocalHeader();

}  // namespace cma::section

namespace cma::provider {

// Special Section
constexpr std::string_view kOhm = "openhardwaremonitor";

// Sections
constexpr std::string_view kDotNetClrMemory = "dotnet_clrmemory";
constexpr std::string_view kWmiWebservices = "wmi_webservices";
constexpr std::string_view kWmiCpuLoad = "wmi_cpuload";

constexpr std::string_view kMsExch = "msexch";

constexpr std::string_view kMsExchActiveSync = "msexch_activesync";
constexpr std::string_view kMsExchAvailability = "msexch_availability";
constexpr std::string_view kMsExchOwa = "msexch_owa";
constexpr std::string_view kMsExchAutoDiscovery = "msexch_autodiscovery";
constexpr std::string_view kMsExchIsClientType = "msexch_isclienttype";
constexpr std::string_view kMsExchIsStore = "msexch_isstore";
constexpr std::string_view kMsExchRpcClientAccess = "msexch_rpcclientaccess";

constexpr std::string_view kBadWmi = "bad_wmi";

constexpr std::string_view kSubSectionSystemPerf = "system_perf";
constexpr std::string_view kSubSectionComputerSystem = "computer_system";
constexpr std::string_view kAgentPlugins = "agent_plugins";

// Path
constexpr const std::wstring_view kWmiPathOhm = L"Root\\OpenHardwareMonitor";
constexpr const std::wstring_view kWmiPathStd = L"Root\\Cimv2";

}  // namespace cma::provider
#endif  // section_header_h__
