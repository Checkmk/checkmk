#include "stdafx.h"

#include "cma_yml.h"

#include <string>

#include "logger.h"

namespace cma::yml {

void LogException(const std::string &format, std::string_view group,
                  std::string_view name, const std::exception &e) {
    try {
        XLOG::l(format, group, name, e.what());
    } catch (const std::exception &e) {
        try {
            XLOG::l.crit("Cannot print '{}' exception '{}'", format, e);
        } catch (const std::exception &e) {
            XLOG::l.crit("Cannot print, exception '{}'", e);
        }
    }
}

void LogException(const std::string &format, std::string_view name,
                  const std::exception &e) {
    try {
        XLOG::l(format, name, e.what());
    } catch (const std::exception &e) {
        try {
            XLOG::l.crit("Cannot print '{}' exception '{}'", format, e);
        } catch (const std::exception &e) {
            XLOG::l.crit("Cannot print, exception '{}'", e);
        }
    }
}

}  // namespace cma::yml
