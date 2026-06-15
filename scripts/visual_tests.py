"""Run visual regression tests locally or in a Linux test container."""

from __future__ import annotations

import argparse
import os
import platform as platform_module
import shlex
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VISUAL_TEST_PATH = "tests/integration/test_visual_regression.py"
DEFAULT_IMAGE = "carvera-controller-visual-tests:latest"
CONTAINERFILE_PATH = REPO_ROOT / "tests" / "integration" / "visual" / "Containerfile"


def visual_pytest_command(mode: str, update: bool, target: str, extra_pytest_args: Sequence[str]) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "pytest",
        target,
        "--visual-run",
        f"--visual-reference-mode={mode}",
    ]
    if update:
        command.append("--update-references")
    command.extend(extra_pytest_args)
    return command


def collect_visual_tests_command(mode: str, extra_pytest_args: Sequence[str]) -> list[str]:
    return [
        sys.executable,
        "-m",
        "pytest",
        VISUAL_TEST_PATH,
        "--visual-run",
        f"--visual-reference-mode={mode}",
        "--collect-only",
        "-q",
        *extra_pytest_args,
    ]


def pytest_option_args(extra_pytest_args: Sequence[str]) -> list[str]:
    options: list[str] = []
    value_expected = False
    options_with_values = {
        "-k",
        "-m",
        "-W",
        "--color",
        "--log-level",
        "--maxfail",
        "--tb",
        "--timeout",
    }
    for arg in extra_pytest_args:
        if value_expected:
            options.append(arg)
            value_expected = False
            continue
        if not arg.startswith("-"):
            continue
        options.append(arg)
        if arg in options_with_values:
            value_expected = True
    return options


def collect_visual_nodeids(mode: str, extra_pytest_args: Sequence[str]) -> tuple[int, list[str]]:
    result = subprocess.run(
        collect_visual_tests_command(mode=mode, extra_pytest_args=extra_pytest_args),
        cwd=REPO_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        print(result.stdout, end="")
        return result.returncode, []
    nodeids = [line.strip() for line in result.stdout.splitlines() if "::" in line]
    return 0, nodeids


def default_container_platform() -> str | None:
    machine = platform_module.machine().lower()
    if machine in {"arm64", "aarch64"}:
        return "linux/arm64"
    if machine in {"x86_64", "amd64"}:
        return "linux/amd64"
    return None


def container_build_command(engine: str, image: str, platform: str | None) -> list[str]:
    command = [
        engine,
        "build",
    ]
    if platform:
        command.extend(["--platform", platform])
    command.extend(["-f", str(CONTAINERFILE_PATH), "-t", image, str(REPO_ROOT)])
    return command


def container_run_command(
    engine: str,
    image: str,
    repo_root: Path,
    platform: str | None,
    update: bool,
    extra_pytest_args: Sequence[str],
    use_host_user: bool,
) -> list[str]:
    script_args = [
        "poetry",
        "run",
        "python3",
        "scripts/visual_tests.py",
        "_container-update" if update else "_container-compare",
    ]
    script_args.extend(extra_pytest_args)
    pytest_command = shlex.join(script_args)
    xvfb_command = (
        "xvfb_log=/tmp/carvera-xvfb.log; "
        'rm -f "$xvfb_log"; '
        'Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp >"$xvfb_log" 2>&1 & '
        "xvfb_pid=$!; "
        'trap "kill $xvfb_pid" EXIT; '
        "for i in $(seq 1 50); do [ -e /tmp/.X11-unix/X99 ] && break; sleep 0.1; done; "
        '[ -e /tmp/.X11-unix/X99 ] || { cat "$xvfb_log"; exit 1; }; '
        f"DISPLAY=:99 {pytest_command}"
    )

    command = [
        engine,
        "run",
        "--rm",
        "-e",
        "HOME=/tmp",
    ]
    if platform:
        command.extend(["--platform", platform])
    command.extend(["-v", f"{repo_root}:/workspace", "-w", "/workspace"])
    if use_host_user and hasattr(os, "getuid") and hasattr(os, "getgid"):
        command.extend(["--user", f"{os.getuid()}:{os.getgid()}"])
    command.append(image)
    command.extend(["sh", "-lc", xvfb_command])
    return command


def detect_engine(explicit_engine: str | None) -> str:
    if explicit_engine:
        return explicit_engine
    env_engine = os.environ.get("VISUAL_TEST_ENGINE")
    if env_engine:
        return env_engine
    for candidate in ("podman", "docker"):
        if shutil.which(candidate):
            return candidate
    raise SystemExit("No container engine found. Install Docker or Podman, or set VISUAL_TEST_ENGINE.")


def split_pytest_args(argv: Sequence[str]) -> tuple[list[str], list[str]]:
    if "--" not in argv:
        return list(argv), []
    separator = argv.index("--")
    return list(argv[:separator]), list(argv[separator + 1 :])


def run_command(command: Sequence[str]) -> int:
    return subprocess.run(command, cwd=REPO_ROOT, check=False).returncode


def run_isolated_visual_tests(mode: str, update: bool, pytest_args: Sequence[str]) -> int:
    collect_result, nodeids = collect_visual_nodeids(mode=mode, extra_pytest_args=pytest_args)
    if collect_result != 0:
        return collect_result
    if not nodeids:
        print("No visual regression tests selected.")
        return 5

    per_test_options = pytest_option_args(pytest_args)
    for nodeid in nodeids:
        print(f"\n===== {nodeid} =====", flush=True)
        result = run_command(
            visual_pytest_command(
                mode=mode,
                update=update,
                target=nodeid,
                extra_pytest_args=per_test_options,
            )
        )
        if result != 0:
            return result
    return 0


def run_container(args: argparse.Namespace, update: bool) -> int:
    engine = detect_engine(args.engine)
    image = args.image or os.environ.get("VISUAL_TEST_IMAGE", DEFAULT_IMAGE)
    platform = args.platform or os.environ.get("VISUAL_TEST_PLATFORM") or default_container_platform()
    if not args.no_build:
        build_result = run_command(container_build_command(engine=engine, image=image, platform=platform))
        if build_result != 0:
            return build_result
    command = container_run_command(
        engine=engine,
        image=image,
        repo_root=REPO_ROOT,
        platform=platform,
        update=update,
        extra_pytest_args=args.pytest_args,
        use_host_user=os.name != "nt",
    )
    return run_command(command)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("local-update", help="Generate ignored host-local references.")

    subparsers.add_parser("local-compare", help="Compare against ignored host-local references.")

    subparsers.add_parser("_container-update", help=argparse.SUPPRESS)
    subparsers.add_parser("_container-compare", help=argparse.SUPPRESS)

    for name, help_text in (
        ("container-update", "Generate committed Linux references in Podman or Docker."),
        ("container-compare", "Compare against committed Linux references in Podman or Docker."),
    ):
        container = subparsers.add_parser(name, help=help_text)
        container.add_argument("--engine", choices=("docker", "podman"), default=None)
        container.add_argument("--image", default=None)
        container.add_argument("--platform", default=None, help="Container platform, for example linux/arm64.")
        container.add_argument("--no-build", action="store_true", help="Reuse an already-built visual test image.")

    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    parser_args, pytest_args = split_pytest_args(raw_argv)
    args, unknown_args = build_parser().parse_known_args(parser_args)
    args.pytest_args = pytest_args + unknown_args
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    pytest_args = args.pytest_args
    if args.command == "local-update":
        return run_isolated_visual_tests(mode="local", update=True, pytest_args=pytest_args)
    if args.command == "local-compare":
        return run_isolated_visual_tests(mode="local", update=False, pytest_args=pytest_args)
    if args.command == "_container-update":
        return run_isolated_visual_tests(mode="committed", update=True, pytest_args=pytest_args)
    if args.command == "_container-compare":
        return run_isolated_visual_tests(mode="committed", update=False, pytest_args=pytest_args)
    if args.command == "container-update":
        return run_container(args, update=True)
    if args.command == "container-compare":
        return run_container(args, update=False)
    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
