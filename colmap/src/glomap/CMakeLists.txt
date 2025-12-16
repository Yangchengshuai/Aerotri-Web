if(MSVC)
    set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} /W3")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} /W3")
else()
    set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -Wall")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wno-sign-compare")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wno-unused-variable")
endif()

if(COVERAGE_ENABLED)
    add_compile_options(-coverage -fprofile-update=atomic)
    add_link_options(-coverage)
endif()

# Enable CUDA code paths in GLOMAP only when CUDA is enabled and Ceres itself
# was compiled with CUDA support. Otherwise, we keep the code paths disabled to
# avoid misleading "compiled with CUDA" messages and to ensure consistent
# runtime behavior (GLOMAP falls back to CPU if CUDA is unavailable).
#
# Important: This must happen BEFORE adding subdirectories so that the macro is
# visible in all GLOMAP libraries (estimators, processors, etc.), not only the
# glomap executable.
if(CUDA_ENABLED AND CUDAToolkit_FOUND AND TARGET Ceres::ceres)
    get_target_property(_ceres_defs Ceres::ceres INTERFACE_COMPILE_DEFINITIONS)
    if(NOT _ceres_defs)
        set(_ceres_defs "")
    endif()
    list(JOIN _ceres_defs ";" _ceres_defs_joined)
    if(NOT _ceres_defs_joined MATCHES "(^|;)CERES_NO_CUDA($|;)")
        list(APPEND COLMAP_COMPILE_DEFINITIONS GLOMAP_CUDA_ENABLED)
    endif()
endif()

add_subdirectory(scene)
add_subdirectory(math)
add_subdirectory(io)
add_subdirectory(estimators)
add_subdirectory(processors)
add_subdirectory(controllers)
add_subdirectory(exe)
add_subdirectory(sfm)

COLMAP_ADD_EXECUTABLE(
    NAME glomap_main
    SRCS
        glomap.cc
    LINK_LIBS
        colmap_glomap_exe
)
set_target_properties(glomap_main PROPERTIES OUTPUT_NAME glomap)

# Keep linkage consistent with COLMAP: some dependency stacks (e.g. via
# OpenImageIO/Poppler/NSS) may require NSPR symbols (PR_*). Link explicitly.
#
# NOTE: COLMAP_ADD_EXECUTABLE uses the "plain" target_link_libraries signature,
# so we must use the same signature here (no PUBLIC/PRIVATE keywords).
target_link_libraries(glomap_main nspr4 plc4 plds4)
