cmake_minimum_required(VERSION 3.16)
project(cobra_vendor NONE)

find_package(ament_cmake REQUIRED)

set(extra_cmake_args)

if(DEFINED CMAKE_BUILD_TYPE)
  list(APPEND extra_cmake_args "-DCMAKE_BUILD_TYPE=${CMAKE_BUILD_TYPE}")
endif()

# The Cobra source code version/revision numbers
set(VER "4.8")
set(REV "0047c6d416821c6258635e530a736a48844f63e6")

include(ExternalProject)
ExternalProject_Add(cobra-${VER}
  PREFIX cobra-${VER}
  GIT_REPOSITORY https://github.com/nimble-code/cobra
  GIT_TAG ${REV}
  INSTALL_DIR "${CMAKE_CURRENT_BINARY_DIR}/cobra_install"
  BUILD_IN_SOURCE TRUE
  CONFIGURE_COMMAND ""
  BUILD_COMMAND
  ${CMAKE_COMMAND} -E chdir <SOURCE_DIR>/src make linux && ${CMAKE_COMMAND} -E chdir <SOURCE_DIR>/src_app make all LDFLAGS=-Wl,c.ar\ -pthread
  INSTALL_COMMAND
  ${CMAKE_COMMAND} -E chdir <SOURCE_DIR>/src make install_linux MAN=<SOURCE_DIR>/src_app LDFLAGS=-Wl,c.ar\ -pthread && ${CMAKE_COMMAND} -E chdir <SOURCE_DIR>/src_app make install_linux LDFLAGS=-Wl,c.ar\ -pthread
)

install(PROGRAMS
  ${CMAKE_CURRENT_BINARY_DIR}/cobra-${VER}/src/cobra-${VER}/bin_linux/cobra
  ${CMAKE_CURRENT_BINARY_DIR}/cobra-${VER}/src/cobra-${VER}/bin_linux/cwe
  ${CMAKE_CURRENT_BINARY_DIR}/cobra-${VER}/src/cobra-${VER}/bin_linux/json_convert
  ${CMAKE_CURRENT_BINARY_DIR}/cobra-${VER}/src/cobra-${VER}/bin_linux/scope_check
  ${CMAKE_CURRENT_BINARY_DIR}/cobra-${VER}/src/cobra-${VER}/bin_linux/find_taint
  ${CMAKE_CURRENT_BINARY_DIR}/cobra-${VER}/src/cobra-${VER}/bin_linux/window.tcl
  DESTINATION bin)

install(DIRECTORY 
  ${CMAKE_CURRENT_BINARY_DIR}/cobra-${VER}/src/cobra-${VER}/rules
  DESTINATION share/${PROJECT_NAME}
)

ament_environment_hooks(env_hook/cobra_vendor_base.dsv.in)

ament_package()
