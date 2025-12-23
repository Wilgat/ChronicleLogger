#!/bin/sh
set -eu

# =============================================
# ChronicleLogger build script — adapted from logged-example by Wong Chun Fai (wilgat)
# Pure POSIX sh, egg-info fully obliterated
# Added Cython-specific commands for cy-master and dependency-merge integration
# =============================================

PROJECT="ChronicleLogger"
KG_NAME="chronicle_logger"

# Get version from class (fallback to unknown)
VERSION=$(python3 - <<'PY'
import os
import sys

# Add src/chronicle_logger to path temporarily
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

try:
    import ChronicleLogger
    print(ChronicleLogger.__version__)
except Exception:
    print("unknown")
PY
) || VERSION="unknown"
echo "ChronicleLogger build tool (v$VERSION)"
echo "========================================"

show_help() {
    cat << EOF
Usage: $0 <command> [options]

Commands:
  setup      Install/update build + twine
  clean      Remove ALL build artifacts, caches, and egg-info
  build      Build sdist + wheel
  upload     Upload to PyPI
  git        git add . -> commit -> push
  tag        Create and push git tag v$VERSION
  release    clean -> build -> upload -> tag (full release!)
  all        Same as release
  test       Run the test suite (pytest)
             Optional arguments are passed directly to pytest.
             Examples:
               ./build.sh test
               ./build.sh test -k test_logname
               ./build.sh test test/test_chronicle_logger.py::test_logname_becomes_kebab_case

  cython            Run './cy-master build' to build the Cython .so
  install-cython    Run './cy-master install-all' to install the .so to global dynload (e.g., /usr/lib/python3.12/lib-dynload)
  generate-cython   Run './dependency-merge' non-interactively to generate src/ChronicleLogger.pyx from src/chronicle_logger/*

Example:
  ./build.sh release
  ./build.sh test -v
  ./build.sh generate-cython
  ./build.sh cython
  ./build.sh install-cython
EOF
}

do_setup() {
    echo "Installing/upgrading build tools..."
    pip3 install --upgrade build twine pytest
}

do_clean() {
    echo "Cleaning project (including all egg-info)..."
    rm -rf build dist .eggs .pytest_cache
    rm -rf ChronicleLogger.egg-info src/ChronicleLogger.egg-info src/ChronicleLogger.*.egg-info 2>/dev/null || true
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "._*" -delete 2>/dev/null || true
    echo "Clean complete — all egg-info destroyed"
}

do_build() {
    echo "Building package..."
    python3 -m build --sdist --wheel --outdir dist/
    echo "Build complete -> dist/"
    ls -lh dist/
}

do_upload() {
    echo "Uploading to PyPI..."
    twine upload dist/*
    echo ""
    echo "SUCCESS: $PROJECT v$VERSION is now live on PyPI!"
    echo "-> https://pypi.org/project/$PROJECT/$VERSION/"
}

do_git() {
    git add .
    echo "Enter commit message:"
    read -r message
    git commit -m "$message"
    git push
    echo "Pushed: $message"
}

do_tag() {
    if [ "$VERSION" = "unknown" ]; then
        echo "ERROR: Cannot determine version. Is version set in src/chronicle_logger/ChronicleLogger.py?"
        exit 1
    fi

    TAG="v$VERSION"
    echo "Creating and pushing tag: $TAG"
    git tag -a "$TAG" -m "Release $TAG"
    git push origin "$TAG"
    echo "Tag $TAG created and pushed successfully!"
    echo "-> https://github.com/cloudgen/ChronicleLogger/releases/tag/$TAG"  # Adjust repo URL as needed
}

# Run tests
do_test() {
    echo "Running test suite (pytest)..."
    # Ensure pytest is available
    if ! command -v pytest >/dev/null 2>&1; then
        echo "pytest not found – installing it temporarily..."
        python3 -m pip install --quiet pytest
    fi

    # If the package is already importable from src, add it to PYTHONPATH
    export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/src"

    # Run pytest on the test/ directory and pass through any extra args
    python3 -m pytest test/* "$@"
    echo "Tests finished."
}

# New: Run cy-master build
do_cython() {
    echo "Building Cython .so..."
    ./cy-master build
    echo "Cython build complete."
}

# New: Run cy-master install-all to copy .so to global dynload
do_install_cython() {
    echo "Installing Cython .so to global dynload (e.g., /usr/lib/python3.12/lib-dynload)..."
    ./cy-master install-all
    echo "Cython installation complete."
}

# New: Run dependency-merge non-interactively to generate src/ChronicleLogger.pyx
do_generate_cython() {
    echo "Generating src/ChronicleLogger.pyx from src/chronicle_logger/*..."
    # Non-interactively accept defaults: empty input for dir, empty for output, 'y' for proceed
    echo -e "\n\ny\n" | ./dependency-merge
    echo "Generation complete: src/ChronicleLogger.pyx"
}

# POSIX case
case "${1:-}" in
    setup)          do_setup ;;
    clean)          do_clean ;;
    build)          do_build ;;
    upload)         do_upload ;;
    git)            do_git ;;
    tag)            do_tag ;;
    test)           shift; do_test "$@" ;;
    release|all)
                    do_clean
                    do_build
                    do_upload
                    do_tag
                    ;;
    cython)         do_cython ;;
    install-cython) do_install_cython ;;
    generate-cython) do_generate_cython ;;
    -h|--help|"")  show_help ;;
    *)              echo "Unknown command: $1"; show_help; exit 1 ;;
esac

echo "Done."