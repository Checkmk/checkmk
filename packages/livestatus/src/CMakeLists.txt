set(CMAKE_VERBOSE_MAKEFILE ON)

set(HEADER_LIST "${Livestatus_SOURCE_DIR}/include/livestatus/Logger.h")
add_library(livestatus STATIC Logger.cc POSIXUtils.cc ${HEADER_LIST})

include(FetchContent)

FetchContent_Declare(asio-cmake
  GIT_REPOSITORY https://github.com/kingsamchen/asio-cmake.git
  GIT_TAG        origin/master
)

# Specify asio version
set(ASIO_CMAKE_ASIO_TAG asio-1-24-0)
FetchContent_MakeAvailable(asio-cmake)

target_include_directories(livestatus PUBLIC ../include/livestatus )
target_compile_features(livestatus PUBLIC cxx_std_17)
target_compile_options(livestatus PUBLIC -Wall -Wextra -Werror -fPIC -O3 -gdwarf-4 -std=c++17)
target_link_libraries(livestatus PRIVATE pthread asio)

# Black Magic for IDE:
source_group(
  TREE "${PROJECT_SOURCE_DIR}/include"
  PREFIX "Header Files"
  FILES ${HEADER_LIST})
