set(header_location ${Livestatus_SOURCE_DIR}/include/livestatus)
set(livestatus_headers
    ${header_location}/BitMask.h ${header_location}/ChronoUtils.h
    ${header_location}/Logger.h ${header_location}/POSIXUtils.h
    ${header_location}/Poller.h)
set(livestatus_sources Logger.cc POSIXUtils.cc)

add_library(livestatus SHARED ${livestatus_headers} ${livestatus_sources})

include(FetchContent)

set(USE_ASIO_OMD true) # set to false to use a fallback
set(USE_ASIO_VERSION asio-1.24.0)

if(${USE_ASIO_OMD})
  FetchContent_Declare(
    asio-omd
    URL ${CMAKE_SOURCE_DIR}/../../omd/packages/asio/${USE_ASIO_VERSION}.tar.gz
    DOWNLOAD_EXTRACT_TIMESTAMP no)
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
set_target_properties(
  livestatus PROPERTIES VERSION ${CMAKE_PROJECT_VERSION}
                        SOVERSION ${CMAKE_PROJECT_VERSION_MAJOR})

if(iwyu_tool_path)
  add_custom_target(
    iwyu
    COMMAND
      "${Python3_EXECUTABLE}" "${iwyu_tool_path}" -j4 --output-format=clang -p
      "${CMAKE_BINARY_DIR}" -- ${IWYU_EXTRA_ARGS} -Xiwyu
      --mapping_file=${root_repo_dir}/livestatus/iwyu-mappings/check_mk.imp
    COMMENT "Running include-what-you-use tool"
    VERBATIM)
endif()

if(run_clang_tidy_path)
  if(${CLANG_VERSION})
    message("CLANG_VERSION is set to ${CLANG_VERSION}")
  else()
    message("CLANG_VERSION is not set, falling back to 14")
    set(CLANG_VERSION 14)
  endif()

  add_custom_target(
    tidy
    COMMAND
      "${Python3_EXECUTABLE}" "${run_clang_tidy_path}"
      -clang-tidy-binary=clang-tidy-${CLANG_VERSION}
      -clang-apply-replacements-binary=clang-apply-replacements-${CLANG_VERSION}
      $(CLANG_TIDY_EXTRA_ARGS) -quiet -j6 -p=${CMAKE_BINARY_DIR}
      ${livestatus_sources}
    COMMENT "Running clang-tidy tool"
    VERBATIM)
endif()

# Black Magic for IDE:
source_group(
  TREE "${PROJECT_SOURCE_DIR}/include"
  PREFIX "Header Files"
  FILES ${HEADER_LIST})
