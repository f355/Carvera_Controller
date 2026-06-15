"""Visual regression tests for active machine control states."""

import os

import pytest

from tests.integration.conftest import (
    apply_machine_state,
    capture_screenshot,
    freeze_animated_status,
    pump_frames,
    save_or_compare_reference,
    show_content_page,
)

REFERENCE_GROUP = os.path.splitext(os.path.basename(__file__))[0]


def reference_name(name):
    return f"{REFERENCE_GROUP}/{name}"


def set_playback_state(app, state):
    from carveracontroller.CNC import CNC

    app.selected_remote_filename = "/sd/gcodes/projects/probe-grid-test.nc"
    app.selected_local_filename = "/tmp/probe-grid-test.nc"
    app.root.progress_info = "Line 348 / 1260"
    CNC.vars["state"] = state
    state_colors = {
        "Hold": (244 / 255, 208 / 255, 63 / 255, 1),
        "Pause": (52 / 255, 152 / 255, 219 / 255, 1),
        "Run": (46 / 255, 204 / 255, 113 / 255, 1),
    }
    CNC.vars["color"] = state_colors[state]
    CNC.vars["curfeed"] = 720.0
    CNC.vars["tarfeed"] = 900.0
    CNC.vars["curspindle"] = 12000.0
    CNC.vars["tarspindle"] = 16000.0
    CNC.vars["playedlines"] = 348
    CNC.vars["playedpercent"] = 42.0
    CNC.vars["playedseconds"] = 96
    CNC.vars["running"] = True
    CNC.vars["is_playing"] = 1
    app.root.wpb_margin.value = 100
    app.root.wpb_zprobe.value = 100
    app.root.wpb_leveling.value = 0
    app.root.wpb_play.value = 42
    show_content_page(app, "Control")
    apply_machine_state(app)
    freeze_animated_status(app)
    pump_frames(5)


def set_continuous_keyboard_jog_state(app):
    from carveracontroller.CNC import CNC

    app.is_community_firmware = True
    app.fw_version_digitized = 999999
    CNC.vars["state"] = "Idle"
    CNC.vars["color"] = (46 / 255, 204 / 255, 113 / 255, 1)
    show_content_page(app, "Control")
    apply_machine_state(app)
    app.root.update_ui_for_jog_mode_cont()
    app.root.keyboard_jog_control = True
    app.jog_keyboard_enable = "down"
    pump_frames(5)


def capture_dropdown_state(app, dropdown, anchor, name, update_references, visual_reference_config, frames=5):
    show_content_page(app, "Control")
    if dropdown.parent:
        dropdown.parent.remove_widget(dropdown)
    dropdown.open(anchor)
    pump_frames(frames)
    capture_screenshot(app, name)
    dropdown.dismiss()
    pump_frames(2)
    save_or_compare_reference(name, visual_reference_config, update_references)


class TestRuntimeControlPages:
    """Screenshots of active playback controls and their disabled/enabled states."""

    @pytest.mark.visual_reference(reference_name("running_control_page"))
    def test_running_control_page(self, kivy_app, connected_idle_state, update_references, visual_reference_config):
        set_playback_state(kivy_app, "Run")
        name = reference_name("running_control_page")
        capture_screenshot(kivy_app, name)
        save_or_compare_reference(name, visual_reference_config, update_references)

    @pytest.mark.visual_reference(reference_name("hold_control_page"))
    def test_hold_control_page(self, kivy_app, connected_idle_state, update_references, visual_reference_config):
        set_playback_state(kivy_app, "Hold")
        name = reference_name("hold_control_page")
        capture_screenshot(kivy_app, name)
        save_or_compare_reference(name, visual_reference_config, update_references)

    @pytest.mark.visual_reference(reference_name("pause_control_page"))
    def test_pause_control_page(self, kivy_app, connected_idle_state, update_references, visual_reference_config):
        set_playback_state(kivy_app, "Pause")
        name = reference_name("pause_control_page")
        capture_screenshot(kivy_app, name)
        save_or_compare_reference(name, visual_reference_config, update_references)


class TestJogControls:
    """Screenshots of jog controls that are not visible in top-bar coverage."""

    @pytest.mark.visual_reference(reference_name("jog_speed_dropdown"))
    def test_jog_speed_dropdown(self, kivy_app, connected_idle_state, update_references, visual_reference_config):
        apply_machine_state(kivy_app)
        show_content_page(kivy_app, "Control")
        capture_dropdown_state(
            kivy_app,
            kivy_app.root.jog_speed_drop_down,
            kivy_app.root.ids.jog_speed_btn,
            reference_name("jog_speed_dropdown"),
            update_references,
            visual_reference_config,
        )

    @pytest.mark.visual_reference(reference_name("continuous_keyboard_jog_controls"))
    def test_continuous_keyboard_jog_controls(
        self, kivy_app, connected_idle_state, update_references, visual_reference_config
    ):
        set_continuous_keyboard_jog_state(kivy_app)
        name = reference_name("continuous_keyboard_jog_controls")
        capture_screenshot(kivy_app, name)
        save_or_compare_reference(name, visual_reference_config, update_references)
