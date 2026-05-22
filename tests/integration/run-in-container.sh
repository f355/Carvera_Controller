#!/usr/bin/env bash
# Run the visual integration suite inside the Linux/Xvfb container.
#
# Usage:
#   tests/integration/run-in-container.sh                                  # verify
#   tests/integration/run-in-container.sh --update-committed-references    # regenerate
#   tests/integration/run-in-container.sh -k test_control_page             # filter
#   REBUILD=1 tests/integration/run-in-container.sh                        # force rebuild
#   CONTAINER_CMD=docker tests/integration/run-in-container.sh             # override CLI
#
# The container is the environment that produces and compares the
# committed reference screenshots. The wrapper exits with pytest's
# exit code so CI / scripts can rely on $?.

set -euo pipefail

# Resolve the workspace root from this script's location (works from any cwd).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
IMAGE_NAME="${IMAGE_NAME:-carvera-visual-tests}"
CONTAINERFILE="${SCRIPT_DIR}/Containerfile"

# Pick the container CLI: explicit override > podman > docker.
if [[ -n "${CONTAINER_CMD:-}" ]]; then
    : # honour the override exactly as given
elif command -v podman >/dev/null 2>&1; then
    CONTAINER_CMD=podman
elif command -v docker >/dev/null 2>&1; then
    CONTAINER_CMD=docker
else
    echo "error: neither podman nor docker found on PATH" >&2
    exit 127
fi

# Build the image when missing. REBUILD=1 forces a rebuild (use it
# after touching the Containerfile or pyproject.toml). Keeping the
# trigger explicit avoids subtle date-comparison portability bugs and
# makes "why is this rebuilding?" trivially answerable.
image_needs_build() {
    [[ "${REBUILD:-0}" == "1" ]] && return 0
    ! "${CONTAINER_CMD}" image inspect "${IMAGE_NAME}" >/dev/null 2>&1
}

if image_needs_build; then
    echo ">>> Building ${IMAGE_NAME} via ${CONTAINER_CMD}"
    "${CONTAINER_CMD}" build \
        -t "${IMAGE_NAME}" \
        -f "${CONTAINERFILE}" \
        "${WORKSPACE_ROOT}"
else
    echo ">>> Using cached image ${IMAGE_NAME} (set REBUILD=1 to force)"
fi

# UID/GID-preserving flags so PNGs written by pytest land owned by the
# host user, not by root. podman uses --userns=keep-id; docker on Linux
# needs an explicit --user; docker-desktop on macOS maps automatically
# and accepts the flag harmlessly.
USER_FLAGS=()
if [[ "${CONTAINER_CMD}" == "podman" || "${CONTAINER_CMD}" == *"/podman" ]]; then
    USER_FLAGS+=(--userns=keep-id)
else
    USER_FLAGS+=(--user "$(id -u):$(id -g)" -e HOME=/tmp)
fi

# tty allocation only when stdout is a terminal so CI captures output cleanly.
TTY_FLAGS=()
if [[ -t 1 ]]; then
    TTY_FLAGS+=(-t)
fi

# Hide a host-side in-project venv from poetry inside the container by
# overlaying an empty anonymous volume on top of it. Only attach the mask
# when the host actually has a .venv/ — adding it unconditionally would
# create a root-owned empty directory at /workspace/.venv on systems
# (like CI) that have no host venv, which poetry then sees as a broken
# in-project venv and tries to recreate.
VENV_MASK=()
if [[ -d "${WORKSPACE_ROOT}/.venv" ]]; then
    VENV_MASK+=(-v /workspace/.venv)
fi

echo ">>> Running pytest in ${CONTAINER_CMD} (args: $*)"
# ${arr[@]+"${arr[@]}"} is the bash 3 / `set -u` safe way to expand a
# possibly-empty array. macOS still ships bash 3.2 by default; the
# wrapper has to work there.
exec "${CONTAINER_CMD}" run --rm \
    "${USER_FLAGS[@]+"${USER_FLAGS[@]}"}" \
    "${TTY_FLAGS[@]+"${TTY_FLAGS[@]}"}" \
    -e IN_TEST_CONTAINER=1 \
    -v "${WORKSPACE_ROOT}:/workspace:Z" \
    "${VENV_MASK[@]+"${VENV_MASK[@]}"}" \
    -w /workspace \
    "${IMAGE_NAME}" \
    "$@"
