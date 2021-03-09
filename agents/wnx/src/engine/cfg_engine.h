// Configuration Parameters for the engine of the Agent
#pragma once

namespace cma::cfg {

// SECTIONS SPECIFIC DEFAULT

// Default max size of logwatch
namespace logwatch {

// '-1' -> ignore this or infinity
constexpr int64_t kMaxSize = 500'000;   // allowed to send
constexpr int64_t kMaxLineLength = -1;  // max entry length
constexpr int64_t kMaxEntries = -1;     // max entry count
constexpr int32_t kTimeout = -1;        // break on timeout

}  // namespace logwatch

}  // namespace cma::cfg
