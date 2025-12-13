# - Try to find OpenImageIO.
#
# COLMAP prefers a CMake package config:
#   OpenImageIOConfig.cmake / openimageio-config.cmake
#
# Some distributions (e.g. Ubuntu 20.04) ship OpenImageIO without CMake config
# files but with pkg-config metadata (OpenImageIO.pc). This module provides a
# fallback so that `find_package(OpenImageIO)` works in module mode.
#
# Result variables:
#   OpenImageIO_FOUND
#   OpenImageIO_INCLUDE_DIRS
#   OpenImageIO_LIBRARIES
#
# Imported targets:
#   OpenImageIO::OpenImageIO

include(FindPackageHandleStandardArgs)

find_package(PkgConfig QUIET)
if(PkgConfig_FOUND)
  pkg_check_modules(PC_OPENIMAGEIO QUIET OpenImageIO)
endif()

# Prefer a path that makes `#include <OpenImageIO/imageio.h>` work, i.e. the
# include directory should be `/usr/include`, not `/usr/include/OpenImageIO`.
find_path(
  OpenImageIO_INCLUDE_DIR
  NAMES OpenImageIO/imageio.h
  HINTS
    ${PC_OPENIMAGEIO_INCLUDEDIR}
    ${PC_OPENIMAGEIO_INCLUDE_DIRS}
)

find_library(
  OpenImageIO_LIBRARY
  NAMES OpenImageIO
  HINTS
    ${PC_OPENIMAGEIO_LIBDIR}
    ${PC_OPENIMAGEIO_LIBRARY_DIRS}
)

set(OpenImageIO_INCLUDE_DIRS "${OpenImageIO_INCLUDE_DIR}")
set(OpenImageIO_LIBRARIES "${OpenImageIO_LIBRARY}")

find_package_handle_standard_args(
  OpenImageIO
  REQUIRED_VARS OpenImageIO_LIBRARY OpenImageIO_INCLUDE_DIR
  VERSION_VAR PC_OPENIMAGEIO_VERSION
)

if(OpenImageIO_FOUND AND NOT TARGET OpenImageIO::OpenImageIO)
  add_library(OpenImageIO::OpenImageIO UNKNOWN IMPORTED)
  set_target_properties(OpenImageIO::OpenImageIO PROPERTIES
    IMPORTED_LOCATION "${OpenImageIO_LIBRARY}"
    INTERFACE_INCLUDE_DIRECTORIES "${OpenImageIO_INCLUDE_DIR}"
  )
endif()

mark_as_advanced(OpenImageIO_INCLUDE_DIR OpenImageIO_LIBRARY)


