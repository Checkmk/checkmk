set(header_location ${Livestatus_SOURCE_DIR}/include/livestatus)
set(livestatus_headers
    ${header_location}/BitMask.h
    ${header_location}/ChronoUtils.h
    ${header_location}/Logger.h
    ${header_location}/OStreamStateSaver.h
    ${header_location}/POSIXUtils.h
    ${header_location}/Poller.h
    ${header_location}/StringUtils.h
    ${header_location}/strutil.h)
set(livestatus_sources Logger.cc POSIXUtils.cc StringUtils.cc strutil.cc)

add_library(livestatus SHARED ${livestatus_headers} ${livestatus_sources})

include(FetchContent)

FetchContent_Declare(
  asio-omd URL ${CMAKE_SOURCE_DIR}/../../omd/packages/asio/asio-1.24.0.tar.gz
               DOWNLOAD_EXTRACT_TIMESTAMP no)
FetchContent_MakeAvailable(asio-omd)
FetchContent_GetProperties(
  asio-omd
  SOURCE_DIR src_dir
  BINARY_DIR bin_dir
  POPULATED done_var)
set(asio_ext_include ${src_dir}/include)

target_include_directories(livestatus PUBLIC ../include ${asio_ext_include})
target_link_libraries(livestatus PRIVATE pthread ${asio_ext_lib})
target_compile_features(livestatus PUBLIC cxx_std_17)
set_target_properties(livestatus PROPERTIES VERSION ${PROJECT_VERSION}
                                            SOVERSION ${PROJECT_VERSION_MAJOR})

# Black Magic for IDE:
source_group(
  TREE "${PROJECT_SOURCE_DIR}/include"
  PREFIX "Header Files"
  FILES ${HEADER_LIST})
