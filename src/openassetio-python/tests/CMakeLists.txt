# SPDX-License-Identifier: Apache-2.0
# Copyright 2013-2022 The Foundry Visionmongers Ltd

#-----------------------------------------------------------------------
# Python/C++ bridge tests

add_subdirectory(bridge)


#-----------------------------------------------------------------------
# Python bindings-specific tests.

add_subdirectory(cmodule)


#-----------------------------------------------------------------------
# Tests of the core Python API.

add_subdirectory(package)


#-----------------------------------------------------------------------
# Test dependencies.

# Install openassetio-specific dependencies that allow us to
# extend PYTHONPATH without needing to pip install to run tests.
openassetio_add_python_environment_dependency(
    openassetio.internal.python.install-deps
    "${PROJECT_SOURCE_DIR}/src/openassetio-python/requirements.txt"
)

# Install test-specific dependencies (e.g. pytest).
openassetio_add_python_environment_dependency(
    openassetio.internal.pytest.install-deps
    "${PROJECT_SOURCE_DIR}/src/openassetio-python/tests/requirements.txt"
)
