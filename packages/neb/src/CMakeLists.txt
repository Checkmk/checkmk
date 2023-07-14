set(header_location ${neb_SOURCE_DIR}/include/neb)
set(neb_headers
    ${header_location}/Comment.h
    ${header_location}/Downtime.h
    ${header_location}/MacroExpander.h
    ${header_location}/nagios.h
    ${header_location}/NebComment.h
    ${header_location}/NebContact.h
    ${header_location}/NebContactGroup.h
    ${header_location}/NebCore.h
    ${header_location}/NebDowntime.h
    ${header_location}/NebGlobalFlags.h
    ${header_location}/NebHost.h
    ${header_location}/NebHostGroup.h
    ${header_location}/NebPaths.h
    ${header_location}/NebService.h
    ${header_location}/NebServiceGroup.h
    ${header_location}/NebTimeperiod.h
    ${header_location}/TimeperiodsCache.h)
set(neb_sources MacroExpander.cc module.cc NebCore.cc NebHost.cc NebService.cc
                TimeperiodsCache.cc)

include(FetchContent)
# Forbids option redefine in subproject: in the case to prevent re2::testing
# build
if(POLICY CMP0777)
  cmake_policy(SET CMP0777 NEW)
endif()

FetchContent_Declare(
  asio-omd
  URL ${root_repo_dir}/third_party/asio/asio-1.24.0-patched.tar.gz
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
set(CMAKE_SKIP_BUILD_RPATH TRUE)

include(ExternalProject)

ExternalProject_Add(
  livestatus
  SOURCE_DIR ${root_repo_dir}/packages/livestatus
  BUILD_IN_SOURCE 1 # run is know what to do
  CONFIGURE_COMMAND ""
  BUILD_ALWAYS 1
  BUILD_COMMAND ${root_repo_dir}/packages/livestatus/run --build
  INSTALL_COMMAND "")
set(livestatus_so
    "${root_repo_dir}/packages/livestatus/build/src/liblivestatus.so")

add_library(neb SHARED ${neb_headers} ${neb_sources})
add_dependencies(neb livestatus)

target_include_directories(
  neb PUBLIC ../include ../third_party/include ${asio_ext_include}
             ${root_repo_dir}/packages/livestatus/include)

target_compile_definitions(neb PRIVATE VERSION="${CMAKE_PROJECT_VERSION}")

target_link_libraries(
  neb
  PRIVATE -static-libstdc++ -lpthread
  PUBLIC ${livestatus_so})

target_compile_features(neb PUBLIC cxx_std_17)
set_target_properties(neb PROPERTIES NO_SONAME 1)

# Black Magic for IDE:
source_group(
  TREE "${PROJECT_SOURCE_DIR}/include"
  PREFIX "Header Files"
  FILES ${HEADER_LIST})
