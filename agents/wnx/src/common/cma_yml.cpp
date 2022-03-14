#include "stdafx.h"

#include "cma_yml.h"

#include <fmt/format.h>

#include <string>
#include <string_view>

#include "logger.h"

namespace cma::yml {
// NOTE: Extreme defensive programming to prevent a crash and deliver data in
// log. Format string may be invalidated with easy during refactoring and it may
// be not found during testing. Also with easy.
void LogException(const std::string &format, std::string_view group,
                  std::string_view name, const std::exception &e) {
    try {
        XLOG::l(format, group, name, e.what());
    } catch (const std::exception &e) {
        try {
            XLOG::l.crit("Cannot print '{}' exception '{}'", format, e.what());
        } catch (const std::exception &e) {
            XLOG::l.crit("Cannot print, exception '{}'", e.what());
        }
    }
}

// NOTE: Extreme defensive programming to prevent a crash(see above)
void LogException(const std::string &format, std::string_view name,
                  const std::exception &e) {
    try {
        XLOG::l(format, name, e.what());
    } catch (const std::exception &e) {
        try {
            XLOG::l.crit("Cannot print '{}' exception '{}'", format, e.what());
        } catch (const std::exception &e) {
            XLOG::l.crit("Cannot print, exception '{}'", e.what());
        }
    }
}

}  // namespace cma::yml
