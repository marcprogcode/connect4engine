cmake_minimum_required(VERSION 3.10)
project(connect4engine VERSION 1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Common source files
set(CORE_SOURCES
    connect4engine/ia.cpp
    connect4engine/tauler.cpp
    connect4engine/transposition_table.cpp
)

set(CORE_HEADERS
    connect4engine/ia.h
    connect4engine/tauler.h
    connect4engine/transposition_table.h
    connect4engine/search_controller.h
)

# CLI Game executable
add_executable(connect4engine connect4engine/connect4engine.cpp ${CORE_SOURCES} ${CORE_HEADERS})
target_include_directories(connect4engine PRIVATE connect4engine)

# UCI Engine executable
add_executable(uci connect4engine/uci.cpp ${CORE_SOURCES} ${CORE_HEADERS})
target_include_directories(uci PRIVATE connect4engine)

# C++ Unit Tests
enable_testing()
add_executable(unit_tests tests/unit_tests.cpp ${CORE_SOURCES} ${CORE_HEADERS})
target_include_directories(unit_tests PRIVATE connect4engine)
add_test(NAME CoreLogicTests COMMAND unit_tests)

# Target warnings
if(MSVC)
    target_compile_options(connect4engine PRIVATE /W4 /WX-)
    target_compile_options(uci PRIVATE /W4 /WX-)
else()
    target_compile_options(connect4engine PRIVATE -Wall -Wextra -Wpedantic)
    target_compile_options(uci PRIVATE -Wall -Wextra -Wpedantic)
endif()

# Optimization flags for Release build
if(CMAKE_BUILD_TYPE STREQUAL "Release" OR CMAKE_BUILD_TYPE STREQUAL "")
    if(MSVC)
        target_compile_options(connect4engine PRIVATE /O2 /Oi /GL)
        target_compile_options(uci PRIVATE /O2 /Oi /GL)
        set_target_properties(connect4engine PROPERTIES LINK_FLAGS "/LTCG")
        set_target_properties(uci PROPERTIES LINK_FLAGS "/LTCG")
    else()
        target_compile_options(connect4engine PRIVATE -O3 -flto -march=native)
        target_compile_options(uci PRIVATE -O3 -flto -march=native)
    endif()
endif()
