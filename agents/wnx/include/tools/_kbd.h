#pragma once

#if defined(_WIN32)
#include <conio.h>
#else
#include "curses.h"
#endif

namespace cma::tools {
inline int GetKeyPress() {
#if defined(_WIN32)
    return _getch();
#else
    return getch();
#endif
}
}  // namespace cma::tools
