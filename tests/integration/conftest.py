"""Integration test fixtures for Kivy app testing.

Boots the full MakeraApp with mocked hardware in a session-scoped
fixture and provides helpers for screenshot capture and comparison.
An autouse fixture restores the app to its as-booted snapshot between
tests, so ``CNC.vars``, screen selection, popups, and gcode state
cannot leak from one test to the next.
"""

import contextlib
import copy
import os
import shutil
import tempfile
import threading
import time

# Isolate Kivy config to a temp directory so tests don't mutate the user's
# real Kivy config. Must be set BEFORE any Kivy import.
_kivy_home = tempfile.mkdtemp(prefix="kivy_test_")
os.environ["KIVY_HOME"] = _kivy_home
os.environ.setdefault("KIVY_NO_FILELOG", "1")
os.environ.setdefault("KIVY_LOG_MODE", "MIXED")
os.environ.setdefault("KIVY_NO_CONSOLELOG", "0")
# SDL2 picks its x11 backend automatically under Xvfb. SDL_VIDEODRIVER
# stays unset so the same conftest works on macOS and in the
# Linux/Xvfb container.
os.environ.setdefault("KIVY_WINDOW", "sdl2")

import pytest
from PIL import Image, ImageChops

from kivy.animation import Animation
from kivy.config import Config

# Matches the reference resolution (also the Xvfb screen geometry in
# the container) so a screenshot is the same size as its baseline.
Config.set("graphics", "width", "1280")
Config.set("graphics", "height", "720")
Config.set("graphics", "fullscreen", "0")
Config.set("kivy", "exit_on_escape", "0")
Config.set("kivy", "pause_on_minimize", "0")
Config.set("input", "mouse", "mouse,multitouch_on_demand")

from kivy.base import EventLoop
from kivy.clock import Clock
from kivy.uix.screenmanager import NoTransition


def install_animation_freeze():
    """Make ``Animation.start`` apply final values immediately.

    Each ``Animation(prop=value).start(widget)`` becomes a direct
    ``widget.prop = value`` followed by a synchronous ``on_complete``
    dispatch. ``ModalView`` open/dismiss rely on ``on_complete`` to
    finalise themselves, so the patched ``start`` must still dispatch
    it — just synchronously, with the final values already applied.
    """

    def _instant_start(self, widget):
        for prop_name, value in self.animated_properties.items():
            with contextlib.suppress(Exception):
                setattr(widget, prop_name, value)
        with contextlib.suppress(Exception):
            self.dispatch("on_complete", widget)

    Animation.start = _instant_start


def install_marquee_freeze():
    """Disable ``ScrollingLabel`` marquee scheduling entirely.

    Without this, ``_marquee_loop`` re-schedules ``_start_marquee``
    every cycle via ``Clock.schedule_once``, leaving the label in a
    non-zero ``scroll_x`` state at the moment of capture.
    """
    from carveracontroller.custom_widgets import ScrollingLabel

    # Each replacement keeps the original ``__name__`` because Kivy's
    # ``WeakMethod`` (used by ``Clock.schedule_once``) looks the method
    # back up by name via ``getattr(instance, name)``.
    for name in ("_start_marquee", "_start_marquee_anim", "_evaluate_fit", "_check_after_shrink"):

        def _noop(self, *a, _n=name, **kw):
            return None

        _noop.__name__ = name
        setattr(ScrollingLabel, name, _noop)


# Must run before any widget is constructed: the marquee freeze has to
# be in place before ``ScrollingLabel`` instances schedule themselves,
# and the ``Animation`` patch has to apply to every ``Animation`` from
# this point on.
install_animation_freeze()
install_marquee_freeze()


REFERENCE_DIR = os.path.join(os.path.dirname(__file__), "reference")
REFERENCE_LOCAL_DIR = os.path.join(os.path.dirname(__file__), "reference.local")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")

_IN_TEST_CONTAINER = os.environ.get("IN_TEST_CONTAINER") == "1"


def pump_frames(count=10, sleep=0):
    """Advance the Kivy event loop by `count` frames.

    This allows Clock.schedule_once callbacks to fire and the UI to settle.
    If `sleep` is given (seconds), sleep that long between frames so that
    Kivy's clock sees real elapsed time — needed for animations and
    interval-scheduled callbacks.
    """
    for _ in range(count):
        if sleep:
            time.sleep(sleep)
        EventLoop.idle()
        Clock.tick()


def apply_machine_state(app):
    """Push current CNC.vars into the UI widgets and let the UI settle.

    Sets config_loaded=True to prevent updateStatus from attempting to
    download config from a non-existent machine when state is "Idle".
    """
    app.root.config_loaded = True
    app.root.updateStatus()
    pump_frames(10)


def load_gcode_file(app, filepath):
    """Load a gcode file into the app, replicating the threaded load flow.

    load_gcode_file must run in a background thread because it blocks on
    load_event.wait() while the UI thread processes scheduled callbacks.
    We pump frames from here to service those callbacks.
    """
    loader = threading.Thread(target=app.root.load_gcode_file, args=(filepath,), daemon=True)
    loader.start()
    # Pump frames while the loader thread runs, so Clock.schedule_once
    # callbacks (load_start, load_page, load_gcodes, load_end) get processed.
    # Short sleep yields to the loader thread without pinning a CPU.
    while loader.is_alive():
        EventLoop.idle()
        Clock.tick()
        time.sleep(0.001)
    # Let the UI fully settle after loading completes
    pump_frames(10)
    # Dismiss any popups that the load process opened (progress, file browser)
    if app.root.progress_popup.parent:
        app.root.progress_popup.dismiss()
    if app.root.file_popup.parent:
        app.root.file_popup.dismiss()
    pump_frames(5)


def pin_time_driven_state(app):
    """Pin wall-time-driven UI fields immediately before a screenshot.

    * Zero the blink flags so ``blink_state`` (if it ever runs again)
      is a no-op and the ``status_data_view`` colour is stable.
    * Refresh ``heartbeat_time`` so the reconnect popup branch in
      ``blink_state`` can never fire mid-test.
    * Pin ``status_index`` to 0 so feed/spindle/tool minor labels
      always show the same alternate.
    * Zero every ``control_list`` slot's update-time so
      ``now - X > threshold`` comparisons have a stable answer.
    * Re-assert ``NoTransition`` on the file popup manager in case a
      handler swapped a fresh ``SlideTransition`` onto it.
    """
    root = app.root
    root.holding = 0
    root.pausing = 0
    root.waiting = 0
    root.tooling = 0
    root.heartbeat_time = time.time()
    root.status_index = 0

    if hasattr(root, "control_list"):
        for slot in root.control_list.values():
            if isinstance(slot, list) and slot:
                slot[0] = 0

    if not isinstance(root.file_popup.popup_manager.transition, NoTransition):
        root.file_popup.popup_manager.transition = NoTransition()


def stop_residual_marquees(app):
    """Zero ``scroll_x`` on every ``ScrollingLabel`` in the tree.

    Companion to ``install_marquee_freeze``: a render frame may have
    left ``scroll_x`` at a non-zero value, or direct property
    assignment may have set it.
    """
    from carveracontroller.custom_widgets import ScrollingLabel

    def _walk(widget):
        if isinstance(widget, ScrollingLabel):
            if widget._marquee_anim is not None:
                with contextlib.suppress(Exception):
                    widget._marquee_anim.cancel(widget)
                widget._marquee_anim = None
            widget.scroll_x = 0
        for child in widget.children:
            _walk(child)

    _walk(app.root)
    # Also walk any open modals / popups parented to Window.
    from kivy.core.window import Window

    for child in list(Window.children):
        _walk(child)


def redraw_gcode_viewer(app):
    """Advance ``GcodeViewer`` to its settled, post-load state.

    With ``_on_frame_tick`` unscheduled by ``freeze_clocks``, the
    viewer's GL canvas instructions never advance: the fly-in
    animation that runs immediately after ``load_gcode_file`` stalls
    part-way and the loaded toolpath never reaches the framebuffer.
    Push the viewer to "everything drawn, no animation in progress"
    and drive a single tick so the new uniforms land on the line mesh
    before the screenshot. Safe no-op when no gcode is loaded.
    """
    gv = getattr(app.root, "gcode_viewer", None)
    if gv is None:
        return
    if gv.lengths is None or len(gv.lengths) <= 1:
        return
    with contextlib.suppress(Exception):
        gv.display_count = gv.get_total_distance()
    gv.dynamic_display = False
    gv._scene_dirty = True
    gv._proj_dirty = True
    with contextlib.suppress(Exception):
        gv._on_frame_tick(None)


def force_render_to_backbuffer(app):
    """Render the current widget tree to the GL back buffer, no flip.

    ``Window.screenshot()`` on the SDL2 provider uses ``glReadPixels``
    which reads ``GL_BACK`` by default. After a normal
    ``EventLoop.idle()`` cycle ``on_flip`` has already swapped the
    freshly rendered frame to the front, so the back buffer holds the
    prior frame. This helper re-runs the layout/canvas/draw stages
    that ``EventLoop.idle()`` performs, deliberately omitting
    ``Window.dispatch('on_flip')``, so the back buffer ends up
    holding the current frame for ``glReadPixels``.
    """
    from kivy.core.window import Window
    from kivy.lang import Builder

    Window.canvas.ask_update()
    Builder.sync()
    Clock.tick_draw()
    Builder.sync()
    Window.dispatch("on_draw")


def capture_screenshot(app, name):
    """Capture the full window to a PNG file in the output directory.

    Before calling ``Window.screenshot()``:

    1. ``pin_time_driven_state`` zeros wall-time-driven UI fields.
    2. ``stop_residual_marquees`` zeros ``ScrollingLabel.scroll_x``.
    3. ``redraw_gcode_viewer`` fast-forwards the unscheduled gcode
       viewer so any loaded toolpath reaches GL.
    4. One ``EventLoop.idle()`` so the changes above propagate
       through kv bindings into widget canvases.
    5. ``force_render_to_backbuffer`` re-renders the current frame
       into the GL back buffer without a flip, so
       ``Window.screenshot()`` (which uses ``glReadPixels`` on
       ``GL_BACK``) sees the current frame rather than the prior one.
    """
    from kivy.core.window import Window

    pin_time_driven_state(app)
    stop_residual_marquees(app)
    redraw_gcode_viewer(app)
    EventLoop.idle()
    Clock.tick()
    force_render_to_backbuffer(app)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, f"{name}.png")

    # Window.screenshot inserts a counter: "name.png" -> "name0001.png"
    actual_path = Window.screenshot(name=filepath)

    # Rename the counter-suffixed file to the exact path we want
    if actual_path and actual_path != filepath:
        if os.path.exists(filepath):
            os.remove(filepath)
        os.rename(actual_path, filepath)

    return filepath


# Per-channel delta absorbs small GPU/font-renderer noise; the ratio
# cap stops a sub-pixel anti-aliasing shift from burning hundreds of
# pixels worth of difference.
_DEFAULT_MAX_DELTA = 4
_DEFAULT_MAX_RATIO = 0.001  # 0.1% of pixels


def _resolve_tolerances(max_delta, max_ratio):
    if max_delta is None:
        max_delta = int(os.environ.get("VISUAL_DIFF_MAX_DELTA", _DEFAULT_MAX_DELTA))
    if max_ratio is None:
        max_ratio = float(os.environ.get("VISUAL_DIFF_MAX_RATIO", _DEFAULT_MAX_RATIO))
    return max_delta, max_ratio


def _resolve_reference_path(name):
    """Pick the reference PNG for ``name``, preferring the local one.

    Returns the path, or ``None`` when no reference exists.
    """
    if not _IN_TEST_CONTAINER:
        local_path = os.path.join(REFERENCE_LOCAL_DIR, f"{name}.png")
        if os.path.exists(local_path):
            return local_path

    committed_path = os.path.join(REFERENCE_DIR, f"{name}.png")
    if not os.path.exists(committed_path):
        return None

    return committed_path


def compare_screenshots(name, max_delta=None, max_ratio=None):
    """Compare an output screenshot against its reference baseline.

    Resolution order:

    * ``reference.local/<name>.png`` if present → compare.
    * ``reference/<name>.png`` if present → compare.
    * Otherwise → ``pytest.fail``.

    Tolerances:

    * ``max_delta`` — max per-channel absolute difference any single
      pixel may have. Default 4/255. Env override
      ``VISUAL_DIFF_MAX_DELTA``.
    * ``max_ratio`` — max fraction of pixels that may exceed
      ``max_delta``. Default 0.001. Env override
      ``VISUAL_DIFF_MAX_RATIO``.

    Individual tests may pass tighter or looser values directly. On
    failure a ``*_DIFF.png`` is written and the assertion message
    carries both the mismatched-pixel count and the ratio.
    """
    ref_path = _resolve_reference_path(name)
    out_path = os.path.join(OUTPUT_DIR, f"{name}.png")

    if ref_path is None:
        pytest.fail(f"No reference baseline for '{name}'. " f"Run with --update-references to create one.")

    max_delta, max_ratio = _resolve_tolerances(max_delta, max_ratio)

    ref = Image.open(ref_path).convert("RGB")
    out = Image.open(out_path).convert("RGB")
    assert ref.size == out.size, f"Screenshot size mismatch: reference={ref.size}, actual={out.size}"

    diff = ImageChops.difference(ref, out)
    # Per-pixel max across R/G/B via two ImageChops.lighter calls.
    r, g, b = diff.split()
    per_pixel_max = ImageChops.lighter(ImageChops.lighter(r, g), b)
    # Threshold mask: 255 where any channel exceeds max_delta, else 0.
    mask = per_pixel_max.point(lambda v: 255 if v > max_delta else 0)
    hist = mask.histogram()
    mismatched_count = hist[255] if len(hist) > 255 else 0
    total_pixels = ref.size[0] * ref.size[1]
    mismatched_ratio = mismatched_count / total_pixels if total_pixels else 0.0

    if mismatched_count == 0:
        return  # exact match within delta on every pixel

    if mismatched_ratio <= max_ratio:
        return  # within ratio tolerance

    diff_path = os.path.join(OUTPUT_DIR, f"{name}_DIFF.png")
    diff.save(diff_path)
    pytest.fail(
        f"Visual difference in '{name}': {mismatched_count} of {total_pixels} "
        f"pixels ({mismatched_ratio:.4%}) exceed max channel delta {max_delta}/255 "
        f"(allowed ratio: {max_ratio:.4%}). See {diff_path}"
    )


# Set by ``pytest_configure`` from ``--update-committed-references``.
# Read by ``save_reference`` to decide between the committed
# references and the gitignored local set.
_WRITE_COMMITTED_REFERENCES = False


def save_reference(name):
    """Copy an output screenshot to become the new reference baseline.

    With ``--update-references`` (the default for ``save_reference``)
    the destination is ``reference.local/<name>.png``: a gitignored
    per-host set that ``compare_screenshots`` prefers over the
    committed reference. With ``--update-committed-references`` the
    destination is ``reference/<name>.png``: the committed references
    that CI compares against.
    """
    dst_dir = REFERENCE_DIR if _WRITE_COMMITTED_REFERENCES else REFERENCE_LOCAL_DIR
    os.makedirs(dst_dir, exist_ok=True)
    src = os.path.join(OUTPUT_DIR, f"{name}.png")
    dst = os.path.join(dst_dir, f"{name}.png")
    shutil.copy2(src, dst)


def pytest_addoption(parser):
    parser.addoption(
        "--update-references",
        action="store_true",
        default=False,
        help="Update reference screenshots into the gitignored local set "
        "(tests/integration/reference.local/) instead of comparing.",
    )
    parser.addoption(
        "--update-committed-references",
        action="store_true",
        default=False,
        help="Update the committed reference screenshots "
        "(tests/integration/reference/) instead of comparing. Typically "
        "run inside the container.",
    )


def pytest_configure(config):
    update_local = config.getoption("--update-references")
    update_committed = config.getoption("--update-committed-references")
    if update_local and update_committed:
        raise pytest.UsageError("--update-references and --update-committed-references are mutually " "exclusive.")
    if update_local and _IN_TEST_CONTAINER:
        raise pytest.UsageError(
            "--update-references is disabled in the container; use --update-committed-references instead."
        )
    global _WRITE_COMMITTED_REFERENCES
    _WRITE_COMMITTED_REFERENCES = update_committed


@pytest.fixture(scope="session")
def update_references(request):
    """True when either reference-update flag was passed.

    Tests use this single boolean to decide whether to save a fresh
    screenshot. ``save_reference`` reads ``pytest_configure``-set
    state to pick the destination directory.
    """
    return request.config.getoption("--update-references") or request.config.getoption("--update-committed-references")


def force_no_transition(app):
    """Set every ``ScreenManager`` transition to ``NoTransition``.

    Covers the three managers: ``root.content`` (top-level pages),
    ``root.cmd_manager`` (gcode / manual command sub-pages inside
    FilePage), and ``root.file_popup.popup_manager`` (remote / local
    pages inside FilePopup).
    """
    root = app.root
    root.content.transition = NoTransition()
    root.cmd_manager.transition = NoTransition()
    root.file_popup.popup_manager.transition = NoTransition()


def freeze_clocks(app):
    """Unschedule every time-driven UI source the current tests reach.

    Run once after ``MakeraApp._run_prepare()``.
    """
    root = app.root
    Clock.unschedule(root.blink_state)
    Clock.unschedule(root.switch_status)
    Clock.unschedule(root.check_model_metadata)
    if getattr(root, "gcode_viewer", None) is not None:
        Clock.unschedule(root.gcode_viewer._on_frame_tick)


def prime_settings_panel(app):
    """Pre-register the four Machine panels in the ConfigPopup sidebar.

    ``ConfigPopup`` boots with three panels added by
    ``load_controller_config`` / ``load_gcode_viewer_config`` /
    ``load_pendant_config`` (Controller, G-Code Viewer, Pendant). The
    four Machine panels (Basic, Advanced, Restore, Backup) are only
    added later by ``load_machine_config``, which the connected-state
    tests call but the disconnected-state tests do not.

    ``reset_app_state`` clears ``setting_list`` and per-test mutation
    dicts but never touches ``ConfigPopup.settings_panel.interface``,
    so the panel set leaks from one test to the next: under randomised
    order, whether ``TestConnectedIdleState::test_settings_popup`` had
    run before ``TestDisconnectedState::test_settings_popup``
    determined what the disconnected sidebar looked like. The
    committed disconnected reference was captured with the four
    Machine panels present (the leaked state), so the disconnected
    test fails in isolation and in declaration order.

    Priming runs ``load_machine_config`` once at session boot, before
    the as-booted baseline is captured, so the disconnected baseline
    matches the committed reference. ``load_machine_config`` is
    idempotent: on every subsequent call (e.g. from
    ``TestConnectedIdleState::test_settings_popup``) it sees the
    existing machine-bound panels and updates them in place instead
    of duplicating them.
    """
    import json as _json

    config_c1 = os.path.join(
        os.path.dirname(__file__), "..", "..", "carveracontroller", "config_c1.json"
    )
    with open(config_c1) as fd:
        config_data = _json.load(fd)

    root = app.root
    saved = {
        "model": app.model,
        "config_loaded": root.config_loaded,
        "setting_list": dict(root.setting_list),
    }
    try:
        # ``load_machine_config`` reads ``setting_list`` for every key
        # in the C1 JSON; pre-populate from defaults so the no-panels
        # branch can build all four panels without erroring out.
        for entry in config_data:
            if "key" in entry and entry.get("type") != "title":
                root.setting_list[entry["key"]] = entry.get("default", "0")
        app.model = "C1"
        root.config_loaded = True
        root.load_machine_config()
    finally:
        app.model = saved["model"]
        root.config_loaded = saved["config_loaded"]
        root.setting_list.clear()
        root.setting_list.update(saved["setting_list"])


_TOPBAR_DATAVIEW_IDS = (
    "status_data_view",
    "x_data_view",
    "y_data_view",
    "z_data_view",
    "a_data_view",
    "coord_system_data_view",
    "feed_data_view",
    "spindle_laser_data_view",
    "tool_data_view",
)
_TOPBAR_DATAVIEW_PROPS = (
    "main_text",
    "minr_text",
    "scale",
    "active",
    "disabled",
    "color",
    "data_icon",
    "tooltip_txt",
)

# App-level Kivy properties written by ``updateStatus`` and the
# sibling state-derivation paths (``setUIForModel`` → ``has_atc``;
# ``load_gcode_file`` → ``has_4axis``; config / fw-update flows →
# ``is_community_firmware`` / ``fw_version_digitized`` /
# ``fw_has_update`` / ``ctl_has_update`` / ``model``).
#
# The CNC.vars snapshot alone is not enough to restore them: the reset
# does not re-run ``updateStatus`` (re-running it would overwrite the
# kv-default top-bar widget text the disconnected references capture
# — see ``_snapshot_topbar``). Snapshotting the app properties
# directly also covers tests that mutate them without going through
# ``updateStatus`` (e.g. setting ``has_4axis = True``).
_APP_PROPS_TO_RESET = (
    "playing",
    "has_4axis",
    "has_atc",
    "lasering",
    "tool",
    "show_gcode_ctl_bar",
    "fw_has_update",
    "ctl_has_update",
    "selected_local_filename",
    "selected_remote_filename",
    "curr_page",
    "total_pages",
    "loading_page",
    "is_community_firmware",
    "fw_version_digitized",
)


def _snapshot_topbar(root):
    """Capture text/property state of the top-bar TopDataView widgets.

    ``updateStatus`` is not called during boot (it's edge-triggered by
    machine-status messages, not a Clock interval), so at the as-booted
    baseline these widgets still hold their kv-default text. Connected
    tests call ``updateStatus`` via ``apply_machine_state``, which
    replaces those defaults with ``CNC.vars``-derived values. Restoring
    CNC.vars alone is not enough because no event re-pushes the
    disconnected values back into the widgets — snapshot and restore
    the widget properties directly.
    """
    snap = {}
    for wid in _TOPBAR_DATAVIEW_IDS:
        w = getattr(root, wid, None)
        if w is None:
            continue
        snap[wid] = {p: getattr(w, p) for p in _TOPBAR_DATAVIEW_PROPS if hasattr(w, p)}
        if "color" in snap[wid]:
            # color is an ObservableList; copy so in-place mutation doesn't leak.
            snap[wid]["color"] = list(snap[wid]["color"])
    return snap


_PROGRESS_BAR_IDS = ("wpb_play", "wpb_margin", "wpb_zprobe", "wpb_leveling")


def _snapshot_progress(root):
    """Capture bottom-bar progress widgets and the z/tool drop-down
    value labels that ``updateStatus`` mutates (``wpb_play.value`` ←
    ``playedpercent``; ``z_drop_down.status_max.value`` ← ``max_delta``;
    ``tool_drop_down.status_tlo.value`` ← ``tlo``).
    """
    snap = {}
    for wid in _PROGRESS_BAR_IDS:
        w = getattr(root, wid, None)
        if w is not None and hasattr(w, "value"):
            snap[wid] = w.value
    z_dd = getattr(root, "z_drop_down", None)
    if z_dd is not None and hasattr(z_dd, "status_max"):
        snap["z_drop_down.status_max.value"] = z_dd.status_max.value
    tool_dd = getattr(root, "tool_drop_down", None)
    if tool_dd is not None and hasattr(tool_dd, "status_tlo"):
        snap["tool_drop_down.status_tlo.value"] = tool_dd.status_tlo.value
    return snap


def capture_baseline(app):
    """Snapshot the as-booted app state for the per-test reset.

    Called once after ``_run_prepare()`` and the boot frames. The
    snapshot is stored on ``app._baseline`` so the autouse reset
    fixture can find it without fixture plumbing.

    Snapshot contents:

    * ``cnc_vars`` — deep copy of the disconnected-default ``CNC.vars``.
    * ``content_screen`` / ``cmd_screen`` / ``file_popup_screen`` —
      default ``ScreenManager.current`` for each of the three managers.
    * ``app_model`` / ``app_state`` — ``MakeraApp.model`` / ``app.state``.
    * ``app_props`` — every entry in ``_APP_PROPS_TO_RESET``. Covers
      tests that mutate these directly (e.g. ``app.has_4axis = True``)
      as well as indirectly via ``updateStatus`` / ``setUIForModel`` /
      ``load_gcode_file``.
    * ``topbar`` — see ``_snapshot_topbar``.
    * ``progress`` — see ``_snapshot_progress``.
    """
    from carveracontroller.CNC import CNC

    root = app.root
    return {
        "cnc_vars": copy.deepcopy(CNC.vars),
        "content_screen": root.content.current,
        "cmd_screen": root.cmd_manager.current,
        "file_popup_screen": root.file_popup.popup_manager.current,
        "app_model": app.model,
        "app_state": app.state,
        "app_props": {p: getattr(app, p) for p in _APP_PROPS_TO_RESET},
        "topbar": _snapshot_topbar(root),
        "progress": _snapshot_progress(root),
    }


def reset_app_state(app):
    """Restore ``app`` to its baseline snapshot. Runs after every test.

    Each step is wrapped in try/except so a single failing reset step
    does not block the rest — an exception during teardown would
    otherwise mask the original test result.
    """
    from kivy.core.window import Window
    from kivy.uix.modalview import ModalView
    from kivy.uix.popup import Popup
    from carveracontroller.CNC import CNC

    baseline = getattr(app, "_baseline", None)
    if baseline is None:
        return
    root = app.root

    # 1. Dismiss every popup currently parented to Window.
    for child in list(Window.children):
        if isinstance(child, (ModalView, Popup)):
            with contextlib.suppress(Exception):
                child.dismiss()

    # 2. Reset CNC.vars from snapshot.
    CNC.vars.clear()
    CNC.vars.update(copy.deepcopy(baseline["cnc_vars"]))

    # 3. Reset screen managers. Re-assert NoTransition on
    # file_popup.popup_manager because individual handlers reassign
    # SlideTransition direction.
    with contextlib.suppress(Exception):
        root.content.current = baseline["content_screen"]
    with contextlib.suppress(Exception):
        root.cmd_manager.current = baseline["cmd_screen"]
    if root.file_popup is not None:
        try:
            root.file_popup.popup_manager.transition = NoTransition()
            root.file_popup.popup_manager.current = baseline["file_popup_screen"]
        except Exception:
            pass

    # 4. App-level properties (see _APP_PROPS_TO_RESET).
    with contextlib.suppress(Exception):
        app.model = baseline["app_model"]
    for prop, value in baseline.get("app_props", {}).items():
        with contextlib.suppress(Exception):
            setattr(app, prop, value)

    # 5. Config / settings flags.
    root.config_loaded = False
    root.config_loading = False
    try:
        root.setting_list.clear()
        root.setting_change_list.clear()
        root.controller_setting_change_list.clear()
    except Exception:
        pass

    # 6. Gcode load state (load_gcode_file flow).
    root.gcode_playing = False
    root.gcode_cannot_visualise = False
    root.progress_info = ""
    root.selected_file_line_count = 0
    root._last_loaded_file_key = None
    root._selected_file_machine_key = None
    root.lines = []

    gv = getattr(root, "gcode_viewer", None)
    if gv is not None:
        with contextlib.suppress(Exception):
            gv.clearDisplay()

    gcode_rv = getattr(root, "gcode_rv", None)
    if gcode_rv is not None:
        try:
            gcode_rv.data = []
            gcode_rv.data_length = 0
        except Exception:
            pass

    slider = getattr(root, "gcode_play_slider", None)
    if slider is not None:
        with contextlib.suppress(Exception):
            slider.value = 0

    # 7. Blink / time-driven flags.
    root.holding = 0
    root.pausing = 0
    root.waiting = 0
    root.tooling = 0
    root.status_index = 0
    root.file_just_loaded = False
    root.uploading = False
    root.downloading = False
    root.alarm_triggered = False
    root.tool_triggered = False
    root.heartbeat_time = time.time()

    if hasattr(root, "control_list"):
        for slot in root.control_list.values():
            if isinstance(slot, list) and slot:
                slot[0] = 0.0

    # 8. Restore ``app.state`` so kv bindings like
    # ``disabled: app.state == 'N/A'`` re-evaluate against the baseline.
    with contextlib.suppress(Exception):
        app.state = baseline["app_state"]

    # 9. Restore widget text/property snapshot. Calling
    # ``root.updateStatus()`` here would not work: at boot
    # updateStatus has never run, so the kv-default toolbar text is
    # what the disconnected reference captures; updateStatus would
    # replace those with CNC.vars-derived values and the post-reset
    # image would diverge from the reference.
    for wid, props in baseline.get("topbar", {}).items():
        w = getattr(root, wid, None)
        if w is None:
            continue
        for prop, val in props.items():
            try:
                if prop == "color":
                    setattr(w, prop, list(val))
                else:
                    setattr(w, prop, val)
            except Exception:
                pass

    # 10. Restore progress bars + drop-down value labels.
    progress = baseline.get("progress", {})
    for wid in _PROGRESS_BAR_IDS:
        if wid in progress:
            w = getattr(root, wid, None)
            if w is not None:
                with contextlib.suppress(Exception):
                    w.value = progress[wid]
    if "z_drop_down.status_max.value" in progress:
        with contextlib.suppress(Exception):
            root.z_drop_down.status_max.value = progress["z_drop_down.status_max.value"]
    if "tool_drop_down.status_tlo.value" in progress:
        with contextlib.suppress(Exception):
            root.tool_drop_down.status_tlo.value = progress["tool_drop_down.status_tlo.value"]

    # 11. Stop any residual marquees.
    with contextlib.suppress(Exception):
        stop_residual_marquees(app)


@pytest.fixture(scope="session")
def kivy_app():
    """Boot the full MakeraApp with mocked hardware.

    This mirrors the startup sequence in main.py:main() but avoids calling
    app.run(), which would block forever in the Kivy event loop. Instead we
    use _run_prepare() to build the widget tree and manually pump frames.
    """
    from carveracontroller import translation
    from carveracontroller.main import (
        MakeraApp,
        load_constants,
        set_config_defaults,
        load_app_configs,
        load_halt_translations,
        app_base_path,
        register_fonts,
        register_images,
    )
    from carveracontroller.translation import tr
    import carveracontroller.main as main_module

    # Replicate the main() startup sequence.
    translation.init(None)
    load_constants()
    set_config_defaults(tr.lang)
    load_app_configs()

    # Suppress hardware access and network requests AFTER config sections exist
    Config.set("carvera", "show_update", "0")
    Config.set("carvera", "address", "")
    Config.set("carvera", "pendant_type", "None")

    main_module.HALT_REASON = load_halt_translations(tr)

    base_path = app_base_path()
    register_fonts(base_path)
    register_images(base_path)

    # Create the app and build its widget tree without entering the event loop
    EventLoop.ensure_window()
    app = MakeraApp()
    app._run_prepare()

    # NoTransition on every ScreenManager: root.content, root.cmd_manager,
    # and root.file_popup.popup_manager.
    force_no_transition(app)

    # Unschedule the time-driven UI sources reachable from the current
    # tests (blink_state, switch_status, check_model_metadata,
    # GcodeViewer._on_frame_tick).
    freeze_clocks(app)

    # Let the UI settle. With the frame tick + blink + switch_status
    # all unscheduled, only one-shot schedule_once callbacks from boot
    # and the 0.25s update_viewport ticks (which unschedule themselves
    # once viewport is initialised) remain.
    pump_frames(10)

    # Register the four Machine panels in ConfigPopup. The committed
    # disconnected-settings-popup reference includes them (see
    # ``prime_settings_panel``); without priming, the disconnected
    # test only matches the reference when a predecessor test has
    # already called ``load_machine_config``.
    prime_settings_panel(app)
    pump_frames(5)

    # Capture the as-booted state AFTER the boot frames so the snapshot
    # reflects the steady-state CNC.vars / screen selection that every
    # subsequent test should be returned to.
    app._baseline = capture_baseline(app)

    yield app

    # Teardown: stop background threads and close the event loop
    app.root.stop.set()  # signals monitorSerial to exit
    app.stop()
    EventLoop.close()

    # Clean up temp Kivy home
    shutil.rmtree(_kivy_home, ignore_errors=True)


@pytest.fixture(autouse=True)
def _reset_app_state_after_each_test(kivy_app):
    """Restore the app to its baseline snapshot after every test.

    Function-scoped autouse fixture covering every test in
    ``tests/integration``. The reset runs on teardown (after
    ``yield``) so the next test starts from a known clean state. The
    first test of the run is implicitly clean because the snapshot
    captures the as-booted state.
    """
    yield
    reset_app_state(kivy_app)
    # A handful of frame ticks is enough to flush kv bindings and any
    # schedule_once callbacks triggered by the reset.
    pump_frames(5)
