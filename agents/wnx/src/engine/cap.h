#ifndef cap_h__
#define cap_h__

#pragma once

#include <filesystem>
#include <string>
#include <string_view>

#include "common/cfg_info.h"

#include "common/wtools.h"

#include "logger.h"

namespace cma::cfg::cap {
bool InstallCapFile(std::filesystem::path CapFile);

}  // namespace cma::cfg::cap

#endif  // cap_h__
