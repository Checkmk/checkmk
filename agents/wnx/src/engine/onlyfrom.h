#ifndef onlyfrom_h__
#define onlyfrom_h__

#include <filesystem>
#include <string>
#include <string_view>

#include "common/cfg_info.h"

#include "common/wtools.h"

#include "yaml-cpp/yaml.h"

#include "logger.h"

#include "cfg.h"

namespace cma::cfg::of {

// wrappers to correctly analyze ip addresses
// we need quite limited functionality, so get it
// we are not going to use manually crafted ip address parsers
// ergo we get everything from the asio

bool IsNetworkV4(const std::string_view Str);
bool IsNetworkV6(const std::string_view Str);
bool IsNetwork(const std::string_view Str);

bool IsAddressV4(const std::string_view Str);
bool IsAddressV6(const std::string_view Str);
bool IsAddress(const std::string_view Str);
bool IsIpV6(const std::string_view Str);

bool IsValid(const std::string_view Template, const std::string_view Address);
std::string MapToV6Address(std::string_view Address);
std::string MapToV6Network(std::string_view Network);

}  // namespace cma::cfg::of

#endif  // onlyfrom_h__
