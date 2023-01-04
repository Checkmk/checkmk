set(header_location ${Livestatus_SOURCE_DIR}/include/livestatus)
set(livestatus_headers
    ${header_location}/Aggregator.h
    ${header_location}/AndingFilter.h
    ${header_location}/Average.h
    ${header_location}/BitMask.h
    ${header_location}/ChronoUtils.h
    ${header_location}/CountAggregator.h
    ${header_location}/CrashReport.h
    ${header_location}/data_encoding.h
    ${header_location}/LogEntry.h
    ${header_location}/data_encoding.h
    ${header_location}/FileSystemHelper.h
    ${header_location}/Filter.h
    ${header_location}/global_counters.h
    ${header_location}/InputBuffer.h
    ${header_location}/Logger.h
    ${header_location}/MapUtils.h
    ${header_location}/mk_inventory.h
    ${header_location}/OringFilter.h
    ${header_location}/OStreamStateSaver.h
    ${header_location}/OutputBuffer.h
    ${header_location}/overload.h
    ${header_location}/Poller.h
    ${header_location}/POSIXUtils.h
    ${header_location}/Renderer.h
    ${header_location}/RendererBrokenCSV.h
    ${header_location}/RendererCSV.h
    ${header_location}/RendererJSON.h
    ${header_location}/RendererPython3.h
    ${header_location}/Row.h
    ${header_location}/StringUtils.h
    ${header_location}/strutil.h
    ${header_location}/Triggers.h)
set(livestatus_sources
    AndingFilter.cc
    Average.cc
    CrashReport.cc
    CountAggregator.cc
    FileSystemHelper.cc
    Filter.cc
    global_counters.cc
    InputBuffer.cc
    LogEntry.cc
    Logger.cc
    mk_inventory.cc
    OringFilter.cc
    OutputBuffer.cc
    POSIXUtils.cc
    Renderer.cc
    RendererBrokenCSV.cc
    RendererCSV.cc
    RendererJSON.cc
    RendererPython3.cc
    StringUtils.cc
    strutil.cc
    Triggers.cc)

add_library(livestatus SHARED ${livestatus_headers} ${livestatus_sources})

include(FetchContent)

FetchContent_Declare(
  asio-omd
  URL ${CMAKE_SOURCE_DIR}/../../omd/packages/asio/asio-1.24.0-patched.tar.gz
  URL_HASH
    SHA256=09b9fe5c670c7bd47c7ee957cd9c184b4c8f0620d5b08b38ce837a24df971bca
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
