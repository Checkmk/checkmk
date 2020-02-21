//
//
// Support for Zip files
//
//

#pragma once

#include <string>
#include <string_view>
#include <vector>

namespace cma::tools::zip {

// Base functionality(no recursion, only top-level entries)
std::vector<std::wstring> List(std::wstring_view file_src);

// basically error-free
bool Extract(std::wstring_view file_src, std::wstring_view dir_dest);

}  // namespace cma::tools::zip
