set(CMAKE_VERBOSE_MAKEFILE ON)

set(HEADER_LIST "${Livestatus_SOURCE_DIR}/include/livestatus/Logger.h")
add_library(livestatus STATIC Logger.cc POSIXUtils.cc ${HEADER_LIST})

include(FetchContent)

set(USE_ASIO_OMD true) # set to false to use a fallback
set(USE_ASIO_VERSION asio-1.24.0)

if(${USE_ASIO_OMD})
  FetchContent_Declare(
    asio-omd
    URL ${CMAKE_SOURCE_DIR}/../../omd/packages/asio/${USE_ASIO_VERSION}.tar.gz)
  FetchContent_MakeAvailable(asio-omd)
  FetchContent_GetProperties(
    asio-omd
    SOURCE_DIR src_dir
    BINARY_DIR bin_dir
    POPULATED done_var)
  message("asio src: " ${src_dir})
  message("asio bin: " ${bin_dir})
  set(asio_ext_include ${src_dir}/include)
else()
  # Fallback to asio-cmake wrapper. To be removed after OMD version will be
  # proven as working.
  FetchContent_Declare(
    asio-cmake
    GIT_REPOSITORY https://github.com/kingsamchen/asio-cmake.git
    GIT_TAG origin/master)

  # This wrapper requires us to specify asio version to correctly call
  # `FetchContent_MakeAvailable`
  set(ASIO_CMAKE_ASIO_TAG ${USE_ASIO_VERSION})
  FetchContent_MakeAvailable(asio-cmake)
  set(asio_ext_lib asio)
endif()

target_include_directories(livestatus PUBLIC ../include/livestatus
                                             ${asio_ext_include})
target_link_libraries(livestatus PRIVATE pthread ${asio_ext_lib})
target_compile_features(livestatus PUBLIC cxx_std_17)
target_compile_options(
  livestatus
  PUBLIC -Wall
         -Wextra
         -Werror
         -fPIC
         -O3
         -gdwarf-4
         -std=c++17)

# Black Magic for IDE:
source_group(
  TREE "${PROJECT_SOURCE_DIR}/include"
  PREFIX "Header Files"
  FILES ${HEADER_LIST})
