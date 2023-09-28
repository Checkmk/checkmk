#include "stdafx.h"

#include "common/cma_yml.h"

#include <string>

#include "wnx/logger.h"

namespace cma::yml {

void LogException(const std::string &format, std::string_view group,
                  std::string_view name, const std::exception &e) {
    try {
        XLOG::l(format, group, name, e.what());
    } catch (const std::exception &bad_exception) {
        try {
            XLOG::l.crit("Cannot print '{}' exception '{}'", format,
                         bad_exception);
        } catch (const std::exception &more_bad_exception) {
            XLOG::l.crit("Cannot print, exception '{}'", more_bad_exception);
        }
    }
}

void LogException(const std::string &format, std::string_view name,
                  const std::exception &e) {
    try {
        XLOG::l(format, name, e.what());
    } catch (const std::exception &bad_exception) {
        try {
            XLOG::l.crit("Cannot print '{}' exception '{}'", format,
                         bad_exception);
        } catch (const std::exception &more_bad_exception) {
            XLOG::l.crit("Cannot print, exception '{}'", more_bad_exception);
        }
    }
}

}  // namespace cma::yml
