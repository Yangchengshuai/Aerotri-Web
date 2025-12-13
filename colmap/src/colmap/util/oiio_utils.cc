#include "colmap/util/oiio_utils.h"

#include <cstdlib>
#include <mutex>

namespace colmap {

static std::once_flag oiio_setup_flag;

void EnsureOpenImageIOInitialized() {
  std::call_once(oiio_setup_flag, []() {
    OIIO::attribute("threads", 1);
    OIIO::attribute("exr_threads", 1);

// OpenImageIO exposes OIIO_VERSION, but some distro versions (e.g. Ubuntu 20.04
// OIIO 2.1.x) do not define OIIO_MAKE_VERSION.
#ifndef OIIO_MAKE_VERSION
#define OIIO_MAKE_VERSION(major, minor, patch) \
  ((major) * 10000 + (minor) * 100 + (patch))
#endif

#if defined(OIIO_VERSION) && OIIO_VERSION >= OIIO_MAKE_VERSION(2, 5, 3)
    std::atexit([]() { OIIO::shutdown(); });
#endif
  });
}

}  // namespace colmap
