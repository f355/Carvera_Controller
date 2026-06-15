"""Visual regression tests for coordinate, probing-origin, and WCS workflows."""

import os

import pytest

from tests.integration.conftest import (
    apply_machine_state,
    capture_screenshot,
    pump_frames,
    save_or_compare_reference,
    show_content_page,
)

REFERENCE_GROUP = os.path.splitext(os.path.basename(__file__))[0]


def reference_name(name):
    return f"{REFERENCE_GROUP}/{name}"


def capture_popup_state(app, popup, name, update_references, visual_reference_config, frames=5):
    show_content_page(app, "Control")
    popup.open()
    pump_frames(frames)
    capture_screenshot(app, name)
    popup.dismiss()
    pump_frames(2)
    save_or_compare_reference(name, visual_reference_config, update_references)


def switch_tab_by_text(tabbed_panel, tab_text):
    for tab in tabbed_panel.tab_list:
        if tab.text == tab_text:
            tabbed_panel.switch_to(tab)
            pump_frames(5)
            return
    raise AssertionError(f"Could not find tab {tab_text!r}")


def setup_coord_popup_mode(app, mode):
    from carveracontroller.CNC import CNC

    app.selected_remote_filename = "/sd/gcodes/Face 4x4 stock.cnc"
    CNC.vars["xmin"] = 12.0
    CNC.vars["xmax"] = 122.0
    CNC.vars["ymin"] = 18.0
    CNC.vars["ymax"] = 98.0
    CNC.vars["wcox"] = 1.25
    CNC.vars["wcoy"] = -2.5
    CNC.vars["anchor1_x"] = 0.0
    CNC.vars["anchor1_y"] = 0.0
    CNC.vars["anchor2_offset_x"] = 110.0
    CNC.vars["anchor2_offset_y"] = 80.0
    CNC.vars["rotation_offset_x"] = 0.0
    CNC.vars["rotation_offset_y"] = 0.0

    popup = app.root.coord_popup
    popup.mode = mode
    popup.set_config("origin", "anchor", 2)
    popup.set_config("origin", "x_offset", 2.5)
    popup.set_config("origin", "y_offset", -1.5)
    popup.set_config("margin", "active", mode in {"Run", "Margin"})
    popup.set_config("zprobe", "active", mode in {"Run", "ZProbe", "Leveling"})
    popup.set_config("zprobe", "origin", 2)
    popup.set_config("zprobe", "x_offset", 8.0)
    popup.set_config("zprobe", "y_offset", 6.0)
    popup.set_config("leveling", "active", mode == "Leveling")
    popup.set_config("leveling", "x_points", 5)
    popup.set_config("leveling", "y_points", 3)
    popup.set_config("leveling", "height", 10)
    popup.set_config("leveling", "xn_offset", 4.0)
    popup.set_config("leveling", "xp_offset", 4.0)
    popup.set_config("leveling", "yn_offset", 3.0)
    popup.set_config("leveling", "yp_offset", 3.0)
    popup.load_config()
    pump_frames(5)
    return popup


def setup_wcs_settings_popup(app):
    from carveracontroller.CNC import CNC

    app.is_community_firmware = True
    CNC.can_rotate_wcs = True
    app.root.controller.viewWCS = lambda: None
    popup = app.root.wcs_settings_popup
    popup.populate_wcs_values(
        {
            "G54": [1.0, 2.0, -3.0, 0.0, 0.0, 12.5],
            "G55": [10.0, 20.0, -1.5, 90.0, 0.0, 0.0],
            "G56": [0.0, 0.0, 0.0, 0.0, 0.0, -8.25],
            "G57": [30.0, 40.0, -2.25, 0.0, 0.0, 3.0],
            "G58": [50.0, 60.0, -4.5, 180.0, 0.0, 0.0],
            "G59": [70.0, 80.0, -6.75, 270.0, 0.0, 0.0],
            "G59.1": [5.0, 6.0, -7.0, 0.0, 0.0, 0.0],
            "G59.2": [8.0, 9.0, -10.0, 0.0, 0.0, 0.0],
            "G59.3": [11.0, 12.0, -13.0, 0.0, 0.0, 0.0],
        }
    )
    return popup


def set_origin_current_position(popup):
    popup.cbx_anchor1.active = False
    popup.cbx_anchor2.active = False
    popup.cbx_4axis_origin.active = False
    popup.cbx_current_position.active = True
    popup.update_offsets()
    pump_frames(5)


def set_origin_fourth_axis(app, popup):
    from carveracontroller.CNC import CNC

    app.has_4axis = True
    CNC.vars["wcox"] = 12.5
    CNC.vars["wcoy"] = -3.25
    CNC.vars["anchor1_x"] = 2.0
    CNC.vars["anchor1_y"] = -1.0
    CNC.vars["rotation_offset_x"] = 0.75
    CNC.vars["rotation_offset_y"] = 1.5
    popup.cbx_anchor1.active = False
    popup.cbx_anchor2.active = False
    popup.cbx_current_position.active = False
    popup.cbx_4axis_origin.active = True
    popup.update_offsets()
    pump_frames(5)


def set_coord_resume_line(popup):
    popup.cbx_startline.active = True
    popup.txt_startline.text = "253"
    pump_frames(5)


def setup_zprobe_work_origin(app):
    popup = app.root.coord_popup.zprobe_popup
    popup.cbx_origin1.active = True
    popup.cbx_origin2.active = False
    popup.txt_x_offset.text = "0.75"
    popup.txt_y_offset.text = "-1.25"
    pump_frames(5)
    return popup


def setup_auto_level_basic(app):
    popup = app.root.coord_popup.auto_level_popup
    popup.ids.cbx_autolevelOffsets.active = False
    popup.ids.sp_x_points.text = "9"
    popup.ids.sp_y_points.text = "5"
    popup.ids.sp_height.text = "15"
    popup.init()
    pump_frames(5)
    return popup


def setup_xyz_probe_popup(app):
    popup = app.root.xyz_probe_popup
    popup.ids.txt_probe_height.text = "12.7"
    popup.ids.txt_tool_diameter.text = "6.35"
    pump_frames(5)
    return popup


class TestCoordWorkflowPopups:
    """Screenshots of the config-and-run workflow and nested coordinate dialogs."""

    @pytest.mark.parametrize(
        ("name", "mode"),
        [
            pytest.param(
                reference_name("coord_popup_run_mode"),
                "Run",
                marks=pytest.mark.visual_reference(reference_name("coord_popup_run_mode")),
            ),
            pytest.param(
                reference_name("coord_popup_margin_mode"),
                "Margin",
                marks=pytest.mark.visual_reference(reference_name("coord_popup_margin_mode")),
            ),
            pytest.param(
                reference_name("coord_popup_zprobe_mode"),
                "ZProbe",
                marks=pytest.mark.visual_reference(reference_name("coord_popup_zprobe_mode")),
            ),
            pytest.param(
                reference_name("coord_popup_leveling_mode"),
                "Leveling",
                marks=pytest.mark.visual_reference(reference_name("coord_popup_leveling_mode")),
            ),
        ],
    )
    def test_coord_popup_modes(
        self, kivy_app, connected_idle_state, name, mode, update_references, visual_reference_config
    ):
        apply_machine_state(kivy_app)
        popup = setup_coord_popup_mode(kivy_app, mode)
        capture_popup_state(kivy_app, popup, name, update_references, visual_reference_config)

    @pytest.mark.visual_reference(reference_name("origin_popup_offset_tab"))
    def test_origin_popup_offset_tab(self, kivy_app, connected_idle_state, update_references, visual_reference_config):
        apply_machine_state(kivy_app)
        setup_coord_popup_mode(kivy_app, "Run")
        capture_popup_state(
            kivy_app,
            kivy_app.root.coord_popup.origin_popup,
            reference_name("origin_popup_offset_tab"),
            update_references,
            visual_reference_config,
        )

    @pytest.mark.visual_reference(reference_name("origin_popup_xyz_probe_tab"))
    def test_origin_popup_xyz_probe_tab(
        self, kivy_app, connected_idle_state, update_references, visual_reference_config
    ):
        apply_machine_state(kivy_app)
        setup_coord_popup_mode(kivy_app, "Run")
        popup = kivy_app.root.coord_popup.origin_popup
        popup.open()
        pump_frames(5)
        switch_tab_by_text(popup.ids.tabbed_panel, "Set By XYZ Probe")
        name = reference_name("origin_popup_xyz_probe_tab")
        capture_screenshot(kivy_app, name)
        popup.dismiss()
        pump_frames(2)
        save_or_compare_reference(name, visual_reference_config, update_references)

    @pytest.mark.visual_reference(reference_name("origin_popup_current_position"))
    def test_origin_popup_current_position(
        self, kivy_app, connected_idle_state, update_references, visual_reference_config
    ):
        apply_machine_state(kivy_app)
        setup_coord_popup_mode(kivy_app, "Run")
        popup = kivy_app.root.coord_popup.origin_popup
        popup.open()
        pump_frames(5)
        set_origin_current_position(popup)
        name = reference_name("origin_popup_current_position")
        capture_screenshot(kivy_app, name)
        popup.dismiss()
        pump_frames(2)
        save_or_compare_reference(name, visual_reference_config, update_references)

    @pytest.mark.visual_reference(reference_name("origin_popup_fourth_axis"))
    def test_origin_popup_fourth_axis(self, kivy_app, connected_idle_state, update_references, visual_reference_config):
        apply_machine_state(kivy_app)
        setup_coord_popup_mode(kivy_app, "Run")
        popup = kivy_app.root.coord_popup.origin_popup
        popup.open()
        pump_frames(5)
        set_origin_fourth_axis(kivy_app, popup)
        name = reference_name("origin_popup_fourth_axis")
        capture_screenshot(kivy_app, name)
        popup.dismiss()
        pump_frames(2)
        save_or_compare_reference(name, visual_reference_config, update_references)

    @pytest.mark.visual_reference(reference_name("coord_popup_resume_line"))
    def test_coord_popup_resume_line(self, kivy_app, connected_idle_state, update_references, visual_reference_config):
        apply_machine_state(kivy_app)
        popup = setup_coord_popup_mode(kivy_app, "Run")
        set_coord_resume_line(popup)
        capture_popup_state(
            kivy_app,
            popup,
            reference_name("coord_popup_resume_line"),
            update_references,
            visual_reference_config,
        )

    @pytest.mark.visual_reference(reference_name("zprobe_popup_path_origin"))
    def test_zprobe_popup_path_origin(self, kivy_app, connected_idle_state, update_references, visual_reference_config):
        apply_machine_state(kivy_app)
        setup_coord_popup_mode(kivy_app, "ZProbe")
        capture_popup_state(
            kivy_app,
            kivy_app.root.coord_popup.zprobe_popup,
            reference_name("zprobe_popup_path_origin"),
            update_references,
            visual_reference_config,
        )

    @pytest.mark.visual_reference(reference_name("zprobe_popup_work_origin"))
    def test_zprobe_popup_work_origin(self, kivy_app, connected_idle_state, update_references, visual_reference_config):
        apply_machine_state(kivy_app)
        setup_coord_popup_mode(kivy_app, "ZProbe")
        popup = setup_zprobe_work_origin(kivy_app)
        capture_popup_state(
            kivy_app,
            popup,
            reference_name("zprobe_popup_work_origin"),
            update_references,
            visual_reference_config,
        )

    @pytest.mark.visual_reference(reference_name("xyz_probe_popup_current_position"))
    def test_xyz_probe_popup_current_position(
        self, kivy_app, connected_idle_state, update_references, visual_reference_config
    ):
        apply_machine_state(kivy_app)
        popup = setup_xyz_probe_popup(kivy_app)
        capture_popup_state(
            kivy_app,
            popup,
            reference_name("xyz_probe_popup_current_position"),
            update_references,
            visual_reference_config,
        )

    @pytest.mark.visual_reference(reference_name("auto_level_popup_offsets"))
    def test_auto_level_popup_offsets(self, kivy_app, connected_idle_state, update_references, visual_reference_config):
        apply_machine_state(kivy_app)
        setup_coord_popup_mode(kivy_app, "Leveling")
        popup = kivy_app.root.coord_popup.auto_level_popup
        popup.ids.cbx_autolevelOffsets.active = True
        popup.init()
        capture_popup_state(
            kivy_app, popup, reference_name("auto_level_popup_offsets"), update_references, visual_reference_config
        )

    @pytest.mark.visual_reference(reference_name("auto_level_popup_basic_grid"))
    def test_auto_level_popup_basic_grid(
        self, kivy_app, connected_idle_state, update_references, visual_reference_config
    ):
        apply_machine_state(kivy_app)
        setup_coord_popup_mode(kivy_app, "Leveling")
        popup = setup_auto_level_basic(kivy_app)
        capture_popup_state(
            kivy_app,
            popup,
            reference_name("auto_level_popup_basic_grid"),
            update_references,
            visual_reference_config,
        )


class TestWCSPopups:
    """Screenshots of WCS and rotation controls."""

    @pytest.mark.visual_reference(reference_name("wcs_settings_popup_values"))
    def test_wcs_settings_popup_values(
        self, kivy_app, connected_idle_state, update_references, visual_reference_config
    ):
        apply_machine_state(kivy_app)
        popup = setup_wcs_settings_popup(kivy_app)
        capture_popup_state(
            kivy_app, popup, reference_name("wcs_settings_popup_values"), update_references, visual_reference_config
        )

    @pytest.mark.visual_reference(reference_name("set_rotation_popup"))
    def test_set_rotation_popup(self, kivy_app, connected_idle_state, update_references, visual_reference_config):
        from carveracontroller.CNC import CNC

        apply_machine_state(kivy_app)
        CNC.vars["rotation_angle"] = 12.345
        capture_popup_state(
            kivy_app,
            kivy_app.root.set_rotation_popup,
            reference_name("set_rotation_popup"),
            update_references,
            visual_reference_config,
        )
