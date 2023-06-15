set(unixcat_sources unixcat.cc)

add_executable(unixcat ${unixcat_sources})

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

set(lib_livestatus_include ${root_repo_dir}/packages/livestatus/include)

target_include_directories(unixcat PRIVATE ${lib_livestatus_include}
                                           ${asio_ext_include})

target_link_libraries(unixcat PRIVATE pthread)

target_compile_features(unixcat PUBLIC cxx_std_17)
