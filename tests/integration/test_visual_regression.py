"""Visual regression tests for the Carvera Controller UI.

These tests capture screenshots of the app in various states and compare them
against reference baselines. Any pixel difference indicates the refactor
changed something visible.

Usage:
    # First run: capture reference baselines
    poetry run python -m pytest tests/integration/test_visual_regression.py --update-references

    # Subsequent runs: compare against baselines
    poetry run python -m pytest tests/integration/test_visual_regression.py
"""

import json
import os

from kivy.app import App

from tests.integration.conftest import (
    apply_machine_state,
    capture_screenshot,
    compare_screenshots,
    load_gcode_file,
    pump_frames,
    save_reference,
)

_TESTS_DIR = os.path.join(os.path.dirname(__file__), "..")
GCODE_FILE = os.path.join(_TESTS_DIR, "resources", "Face 4x4 stock.cnc")
CONFIG_C1_PATH = os.path.join(_TESTS_DIR, "..", "carveracontroller", "config_c1.json")


class TestDisconnectedState:
    """Screenshots of the app with no machine connected (default boot state)."""

    def test_control_page(self, kivy_app, update_references):
        name = "disconnected_control_page"
        kivy_app.root.content.current = "Control"
        pump_frames(10)
        capture_screenshot(kivy_app, name)
        if update_references:
            save_reference(name)
        else:
            compare_screenshots(name)

    def test_file_page(self, kivy_app, update_references):
        name = "disconnected_file_page"
        kivy_app.root.content.current = "File"
        pump_frames(10)
        capture_screenshot(kivy_app, name)
        if update_references:
            save_reference(name)
        else:
            compare_screenshots(name)

    def test_settings_popup(self, kivy_app, update_references):
        name = "disconnected_settings_popup"
        kivy_app.root.content.current = "Control"
        kivy_app.root.config_popup.open()
        pump_frames(20, sleep=0.05)
        capture_screenshot(kivy_app, name)
        kivy_app.root.config_popup.dismiss()
        pump_frames(10, sleep=0.05)
        if update_references:
            save_reference(name)
        else:
            compare_screenshots(name)


class TestConnectedIdleState:
    """Screenshots with a simulated connected, idle machine."""

    def test_control_page(self, kivy_app, connected_idle_state, update_references):
        name = "connected_idle_control_page"
        kivy_app.root.content.current = "Control"
        apply_machine_state(kivy_app)
        capture_screenshot(kivy_app, name)
        if update_references:
            save_reference(name)
        else:
            compare_screenshots(name)

    def test_file_page(self, kivy_app, connected_idle_state, update_references):
        name = "connected_idle_file_page"
        kivy_app.root.content.current = "File"
        apply_machine_state(kivy_app)
        capture_screenshot(kivy_app, name)
        if update_references:
            save_reference(name)
        else:
            compare_screenshots(name)

    def test_gcode_loaded(self, kivy_app, connected_idle_state, update_references):
        name = "connected_idle_gcode_loaded"
        apply_machine_state(kivy_app)
        load_gcode_file(kivy_app, GCODE_FILE)
        kivy_app.root.content.current = "File"
        kivy_app.root.cmd_manager.current = "gcode_cmd_page"
        pump_frames(10, sleep=0.05)
        capture_screenshot(kivy_app, name)
        if update_references:
            save_reference(name)
        else:
            compare_screenshots(name)

    def test_settings_popup(self, kivy_app, connected_idle_state, update_references):
        name = "connected_idle_settings_popup"
        kivy_app.root.content.current = "Control"
        App.get_running_app().model = "C1"
        kivy_app.root.config_loaded = True
        # Pre-populate setting_list with defaults from config JSON so
        # load_machine_config doesn't fail on missing keys
        with open(CONFIG_C1_PATH) as f:
            config_data = json.load(f)
        for entry in config_data:
            if "key" in entry and entry.get("type") != "title":
                kivy_app.root.setting_list[entry["key"]] = entry.get("default", "0")
        kivy_app.root.load_machine_config()
        apply_machine_state(kivy_app)
        kivy_app.root.config_popup.open()
        pump_frames(20, sleep=0.05)
        capture_screenshot(kivy_app, name)
        kivy_app.root.config_popup.dismiss()
        pump_frames(10, sleep=0.05)
        if update_references:
            save_reference(name)
        else:
            compare_screenshots(name)

    def test_control_page_laser_mode(self, kivy_app, connected_idle_state, update_references):
        from carveracontroller.CNC import CNC

        name = "connected_idle_control_page_laser_mode"
        # ``CNC.vars["lasermode"] = 1`` flips ``app.lasering = True``
        # inside ``updateStatus``; kv bindings downstream switch the
        # spindle button to the laser icon and show the laser slider.
        # The autouse reset restores ``lasering`` so this does not
        # leak under randomized order.
        CNC.vars["lasermode"] = 1
        kivy_app.root.content.current = "Control"
        apply_machine_state(kivy_app)
        capture_screenshot(kivy_app, name)
        if update_references:
            save_reference(name)
        else:
            compare_screenshots(name)

    def test_gcode_loaded_on_control(self, kivy_app, connected_idle_state, update_references):
        name = "connected_idle_gcode_loaded_on_control"
        # Companion to ``test_gcode_loaded`` (which captures the File
        # page). Loads the same gcode then switches to Control so the
        # 3D gcode viewer renders on the Control page;
        # ``redraw_gcode_viewer`` in ``capture_screenshot`` settles the
        # unscheduled viewer before the screenshot.
        apply_machine_state(kivy_app)
        load_gcode_file(kivy_app, GCODE_FILE)
        kivy_app.root.content.current = "Control"
        pump_frames(10, sleep=0.05)
        capture_screenshot(kivy_app, name)
        if update_references:
            save_reference(name)
        else:
            compare_screenshots(name)

    def test_coord_popup(self, kivy_app, connected_idle_state, update_references):
        name = "connected_idle_coord_popup"
        # CoordPopup is the origin/zprobe/leveling tab container,
        # opened from the path-area "Coord" button. ``load_config()``
        # pushes ``Makera.coord_config`` into the popup's child
        # widgets including ``CNCWorkspace``; without it the
        # workspace's class-default ``config = {}`` trips a
        # ``KeyError: 'origin'`` inside ``draw()`` the moment the
        # popup is laid out.
        kivy_app.root.content.current = "Control"
        apply_machine_state(kivy_app)
        # ``Makera.coord_config`` is a plain dict and is not in the
        # autouse reset's tracked properties; ``load_end`` mutates
        # ``origin.anchor`` and the lasermode branch of
        # ``updateStatus`` flips ``margin``/``zprobe``/``leveling``
        # ``active``. Re-seed to kv-default values so this snapshot
        # does not depend on which other test ran first.
        coord_config = kivy_app.root.coord_config
        coord_config["origin"]["anchor"] = 1
        coord_config["origin"]["x_offset"] = 0.0
        coord_config["origin"]["y_offset"] = 0.0
        coord_config["margin"]["active"] = False
        coord_config["zprobe"]["active"] = False
        coord_config["leveling"]["active"] = False
        kivy_app.root.coord_popup.load_config()
        kivy_app.root.coord_popup.open()
        pump_frames(20, sleep=0.05)
        capture_screenshot(kivy_app, name)
        kivy_app.root.coord_popup.dismiss()
        pump_frames(10, sleep=0.05)
        if update_references:
            save_reference(name)
        else:
            compare_screenshots(name)

    def test_diagnose_popup(self, kivy_app, connected_idle_state, update_references):
        name = "connected_idle_diagnose_popup"
        # DiagnosePopup is the sensor/switch matrix. Same open /
        # capture / dismiss flow as ``test_coord_popup`` to keep the
        # popup state contained even under randomized order.
        kivy_app.root.content.current = "Control"
        apply_machine_state(kivy_app)
        kivy_app.root.diagnose_popup.open()
        pump_frames(20, sleep=0.05)
        capture_screenshot(kivy_app, name)
        kivy_app.root.diagnose_popup.dismiss()
        pump_frames(10, sleep=0.05)
        if update_references:
            save_reference(name)
        else:
            compare_screenshots(name)


class TestAlarmState:
    """Screenshots with the machine in alarm state (red status bar)."""

    def test_alarm_control_page(self, kivy_app, alarm_state, update_references):
        name = "alarm_control_page"
        kivy_app.root.content.current = "Control"
        # ``updateStatus`` opens the halt/unlock popup the first time
        # it sees ``app.state == 'Alarm'``. Pre-arming
        # ``alarm_triggered`` short-circuits that branch so the
        # screenshot captures the red status bar instead of the modal
        # overlay; the autouse reset restores it before the next test.
        kivy_app.root.alarm_triggered = True
        apply_machine_state(kivy_app)
        capture_screenshot(kivy_app, name)
        if update_references:
            save_reference(name)
        else:
            compare_screenshots(name)


class TestRunningState:
    """Screenshots with the machine actively playing a job."""

    def test_running_control_page(self, kivy_app, connected_idle_state, update_references):
        from carveracontroller.CNC import CNC

        name = "running_control_page"
        # The stock-firmware path keys playback off ``playedlines > 0``;
        # ``is_playing`` is set too for the community-firmware branch
        # in case ``is_community_firmware`` is ever toggled.
        CNC.vars["state"] = "Run"
        CNC.vars["is_playing"] = 1
        CNC.vars["playedlines"] = 100
        CNC.vars["playedpercent"] = 42
        CNC.vars["playedseconds"] = 120
        kivy_app.root.content.current = "Control"
        apply_machine_state(kivy_app)
        capture_screenshot(kivy_app, name)
        if update_references:
            save_reference(name)
        else:
            compare_screenshots(name)


class TestHoldState:
    """Screenshots with the machine in Hold / Pause / Wait / Tool states.

    These four states share the same ``updateStatus`` Idle→<state>
    transition path that sets ``status_data_view.color =
    STATECOLOR[<state>]`` and arms the matching blink flag
    (``holding`` / ``pausing`` / ``waiting`` / ``tooling``).
    ``freeze_clocks`` unschedules ``blink_state`` and
    ``pin_time_driven_state`` zeros the blink flags before the
    screenshot, so the colour is captured at its non-blinked-out
    value every time.
    """

    def test_hold_control_page(self, kivy_app, connected_idle_state, update_references):
        from carveracontroller.CNC import CNC

        name = "hold_control_page"
        CNC.vars["state"] = "Hold"
        kivy_app.root.content.current = "Control"
        apply_machine_state(kivy_app)
        capture_screenshot(kivy_app, name)
        if update_references:
            save_reference(name)
        else:
            compare_screenshots(name)

    def test_pause_control_page(self, kivy_app, connected_idle_state, update_references):
        from carveracontroller.CNC import CNC

        name = "pause_control_page"
        CNC.vars["state"] = "Pause"
        kivy_app.root.content.current = "Control"
        apply_machine_state(kivy_app)
        capture_screenshot(kivy_app, name)
        if update_references:
            save_reference(name)
        else:
            compare_screenshots(name)

    def test_wait_control_page(self, kivy_app, connected_idle_state, update_references):
        from carveracontroller.CNC import CNC

        name = "wait_control_page"
        CNC.vars["state"] = "Wait"
        kivy_app.root.content.current = "Control"
        apply_machine_state(kivy_app)
        capture_screenshot(kivy_app, name)
        if update_references:
            save_reference(name)
        else:
            compare_screenshots(name)

    def test_tool_change_control_page(self, kivy_app, connected_idle_state, update_references):
        from carveracontroller.CNC import CNC

        name = "tool_change_control_page"
        # ``updateStatus`` opens the tool-change confirm popup the
        # first time it sees ``app.state == 'Tool'``; pre-arming
        # ``tool_triggered`` short-circuits that branch (mirrors the
        # ``alarm_triggered`` trick in ``test_alarm_control_page``).
        # The autouse reset restores ``tool_triggered`` before the
        # next test.
        CNC.vars["state"] = "Tool"
        kivy_app.root.content.current = "Control"
        kivy_app.root.tool_triggered = True
        apply_machine_state(kivy_app)
        capture_screenshot(kivy_app, name)
        if update_references:
            save_reference(name)
        else:
            compare_screenshots(name)


class TestProbing:
    """Screenshots of the probing UI surface.

    Covers the nine tabs of ``root.probing_popup`` (Outside Corners,
    Inside Corners, Single Axis, Bore/Pocket, Boss/Block, Angle,
    ProbeTip, Calibration, 4th Axis), the gcode preview confirmation
    popup, the wrong-tool selector (``root.select_probe_popup``,
    reached via ``open_probing_popup`` when the spindle holds a
    regular tool), and the manual XYZ block probe
    (``root.xyz_probe_popup``).

    The probing popup is created once at boot and reused. Its
    ``delayed_bind`` is a ``Clock.schedule_once(..., 0.1)`` that
    wires the per-tab settings widgets, so each test pumps 10 frames
    at sleep=0.05 (5x the delay) after opening to guarantee that
    callback has fired. The autouse ``reset_app_state`` walks
    ``Window.children`` and dismisses every ``ModalView`` / ``Popup``,
    so leaked probing popups (including the ad-hoc
    ``SelectAndCalibrateProbePopup`` re-created in
    ``open_probing_popup``) are cleaned up between tests.
    """

    def _open_probing_tab(self, kivy_app, tab_index):
        """Open ``root.probing_popup`` and switch to the indexed tab.

        ``TabbedPanel.tab_list`` is in reverse-of-definition order
        (Kivy quirk), so it's reversed back to get definition order:
        0=Outside Corners, 1=Inside Corners, 2=Single Axis,
        3=Bore/Pocket, 4=Boss/Block, 5=Angle, 6=ProbeTip,
        7=Calibration, 8=4th Axis.

        The popup is session-scoped (created once at boot, reused).
        Its TabbedPanel retains ``current_tab`` across open/dismiss
        cycles, so every test must switch explicitly — even for the
        default Outside Corners tab — or a previous test's selection
        bleeds in under randomized order.
        """
        kivy_app.root.probing_popup.open()
        pump_frames(10, sleep=0.05)
        panel = kivy_app.root.probing_popup.ids.tabbedpanelid
        tabs = list(reversed(panel.tab_list))
        panel.switch_to(tabs[tab_index])
        pump_frames(5, sleep=0.05)

    def _close_probing_popup(self, kivy_app):
        kivy_app.root.probing_popup.dismiss()
        pump_frames(5, sleep=0.05)

    def test_probing_popup_outside_corners(self, kivy_app, connected_idle_state, update_references):
        name = "probing_popup_outside_corners"
        kivy_app.root.content.current = "Control"
        apply_machine_state(kivy_app)
        self._open_probing_tab(kivy_app, 0)
        capture_screenshot(kivy_app, name)
        self._close_probing_popup(kivy_app)
        if update_references:
            save_reference(name)
        else:
            compare_screenshots(name)

    def test_probing_popup_inside_corners(self, kivy_app, connected_idle_state, update_references):
        name = "probing_popup_inside_corners"
        kivy_app.root.content.current = "Control"
        apply_machine_state(kivy_app)
        self._open_probing_tab(kivy_app, 1)
        capture_screenshot(kivy_app, name)
        self._close_probing_popup(kivy_app)
        if update_references:
            save_reference(name)
        else:
            compare_screenshots(name)

    def test_probing_popup_single_axis(self, kivy_app, connected_idle_state, update_references):
        name = "probing_popup_single_axis"
        kivy_app.root.content.current = "Control"
        apply_machine_state(kivy_app)
        self._open_probing_tab(kivy_app, 2)
        capture_screenshot(kivy_app, name)
        self._close_probing_popup(kivy_app)
        if update_references:
            save_reference(name)
        else:
            compare_screenshots(name)

    def test_probing_popup_bore(self, kivy_app, connected_idle_state, update_references):
        name = "probing_popup_bore"
        kivy_app.root.content.current = "Control"
        apply_machine_state(kivy_app)
        self._open_probing_tab(kivy_app, 3)
        capture_screenshot(kivy_app, name)
        self._close_probing_popup(kivy_app)
        if update_references:
            save_reference(name)
        else:
            compare_screenshots(name)

    def test_probing_popup_boss_block(self, kivy_app, connected_idle_state, update_references):
        name = "probing_popup_boss_block"
        kivy_app.root.content.current = "Control"
        apply_machine_state(kivy_app)
        self._open_probing_tab(kivy_app, 4)
        capture_screenshot(kivy_app, name)
        self._close_probing_popup(kivy_app)
        if update_references:
            save_reference(name)
        else:
            compare_screenshots(name)

    def test_probing_popup_angle(self, kivy_app, connected_idle_state, update_references):
        name = "probing_popup_angle"
        kivy_app.root.content.current = "Control"
        apply_machine_state(kivy_app)
        self._open_probing_tab(kivy_app, 5)
        capture_screenshot(kivy_app, name)
        self._close_probing_popup(kivy_app)
        if update_references:
            save_reference(name)
        else:
            compare_screenshots(name)

    def test_probing_popup_probe_tip(self, kivy_app, connected_idle_state, update_references):
        name = "probing_popup_probe_tip"
        kivy_app.root.content.current = "Control"
        apply_machine_state(kivy_app)
        self._open_probing_tab(kivy_app, 6)
        capture_screenshot(kivy_app, name)
        self._close_probing_popup(kivy_app)
        if update_references:
            save_reference(name)
        else:
            compare_screenshots(name)

    def test_probing_popup_calibration(self, kivy_app, connected_idle_state, update_references):
        name = "probing_popup_calibration"
        kivy_app.root.content.current = "Control"
        apply_machine_state(kivy_app)
        self._open_probing_tab(kivy_app, 7)
        capture_screenshot(kivy_app, name)
        self._close_probing_popup(kivy_app)
        if update_references:
            save_reference(name)
        else:
            compare_screenshots(name)

    def test_probing_popup_fourth_axis(self, kivy_app, connected_idle_state, update_references):
        from carveracontroller.CNC import CNC

        name = "probing_popup_fourth_axis"
        # Set the 4-axis hardware bit (``FuncSetting & 1``) and push
        # ``has_4axis`` directly so the kv re-evaluates against the
        # four-axis branch without loading gcode (``load_gcode_file``
        # is what normally derives ``has_4axis`` from parsed A-axis
        # usage). The autouse reset restores ``has_4axis``.
        CNC.vars["FuncSetting"] |= 1
        kivy_app.root.content.current = "Control"
        apply_machine_state(kivy_app)
        App.get_running_app().has_4axis = True
        self._open_probing_tab(kivy_app, 8)
        capture_screenshot(kivy_app, name)
        self._close_probing_popup(kivy_app)
        if update_references:
            save_reference(name)
        else:
            compare_screenshots(name)

    def test_probing_preview_popup(self, kivy_app, connected_idle_state, update_references):
        name = "probing_preview_popup"
        # End-to-end gcode-generation path: pressing the Outside
        # Corner "Top Left" button generates M464 gcode and opens
        # ``preview_popup`` with the gcode shown in ``lb_preview``.
        # ``show_preview`` also schedules
        # ``link_shared_data_with_refresh`` 0.1s out to wire the
        # popup's RecycleView to ``app.mdi_data``; the pump after
        # the press lets that callback run before capture.
        kivy_app.root.content.current = "Control"
        apply_machine_state(kivy_app)
        pp = kivy_app.root.probing_popup
        pp.open()
        pump_frames(10, sleep=0.05)
        # Pin the visible probing-popup tab so the popup behind the
        # preview overlay is the same regardless of which tab the
        # previous test left selected on the shared instance.
        panel = pp.ids.tabbedpanelid
        tabs = list(reversed(panel.tab_list))
        panel.switch_to(tabs[0])
        pump_frames(5, sleep=0.05)
        pp.on_outside_corner_probing_pressed("TopLeft")
        pump_frames(10, sleep=0.05)
        capture_screenshot(kivy_app, name)
        pp.preview_popup.dismiss()
        pp.dismiss()
        pump_frames(5, sleep=0.05)
        if update_references:
            save_reference(name)
        else:
            compare_screenshots(name)

    def test_select_probe_popup(self, kivy_app, connected_idle_state, update_references):
        from carveracontroller.CNC import CNC

        name = "select_probe_popup"
        # Wrong-tool branch of ``open_probing_popup``: when the
        # spindle holds a regular tool (not 0 and not >= 999990) the
        # controller refuses to open ``probing_popup`` and instead
        # constructs and opens a fresh
        # ``SelectAndCalibrateProbePopup``. The ad-hoc instance is
        # parented to ``Window`` and is dismissed by the autouse
        # reset's ``Window.children`` walk.
        CNC.vars["tool"] = 5
        kivy_app.root.content.current = "Control"
        apply_machine_state(kivy_app)
        kivy_app.root.open_probing_popup()
        pump_frames(10, sleep=0.05)
        capture_screenshot(kivy_app, name)
        kivy_app.root.select_probe_popup.dismiss()
        pump_frames(5, sleep=0.05)
        if update_references:
            save_reference(name)
        else:
            compare_screenshots(name)

    def test_xyz_probe_popup(self, kivy_app, connected_idle_state, update_references):
        name = "xyz_probe_popup"
        # Manual XYZ block probe popup. Plain open / capture /
        # dismiss flow with the same pump cadence as the other
        # popup tests so the animation freeze settles regardless of
        # which test opened a popup immediately before this one.
        kivy_app.root.content.current = "Control"
        apply_machine_state(kivy_app)
        kivy_app.root.xyz_probe_popup.open()
        pump_frames(10, sleep=0.05)
        capture_screenshot(kivy_app, name)
        kivy_app.root.xyz_probe_popup.dismiss()
        pump_frames(5, sleep=0.05)
        if update_references:
            save_reference(name)
        else:
            compare_screenshots(name)
