#ifndef onlyfrom_h__
#define onlyfrom_h__

#include <string>
#include <string_view>

#include "yaml-cpp/yaml.h"

namespace cma::cfg::of {

// wrappers to correctly analyze ip addresses
// we need quite limited functionality, so get it
// we are not going to use manually crafted ip address parsers
// ergo we get everything from the asio

bool IsNetworkV4(std::string_view Str);
bool IsNetworkV6(std::string_view Str);
bool IsNetwork(std::string_view Str);

bool IsAddressV4(std::string_view Str);
bool IsAddressV6(std::string_view Str);
bool IsAddress(std::string_view Str);
bool IsIpV6(std::string_view Str);

bool IsValid(std::string_view Template, std::string_view Address);
std::string MapToV6Address(std::string_view Address);
std::string MapToV6Network(std::string_view Network);

}  // namespace cma::cfg::of

#endif  // onlyfrom_h__
