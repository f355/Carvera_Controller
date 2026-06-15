"""Visual regression tests for probing routine setup screens."""

import os

import pytest

from tests.integration.conftest import (
    apply_machine_state,
    capture_screenshot,
    pump_frames,
    save_or_compare_reference,
)

REFERENCE_GROUP = os.path.splitext(os.path.basename(__file__))[0]


def reference_name(name):
    return f"{REFERENCE_GROUP}/{name}"


def switch_tab_by_text(tabbed_panel, tab_text):
    for tab in tabbed_panel.tab_list:
        if tab.text == tab_text:
            tabbed_panel.switch_to(tab)
            pump_frames(5)
            return
    raise AssertionError(f"Could not find tab {tab_text!r}")


def setup_probing_popup_tab(app, tab_text):
    from carveracontroller.CNC import CNC

    app.is_community_firmware = True
    CNC.vars["tool"] = 0
    popup = app.root.probing_popup
    popup.open()
    pump_frames(5)
    switch_tab_by_text(popup.ids.tabbedpanelid, tab_text)
    return popup


def capture_probing_preview_state(app, popup, name, update_references, visual_reference_config):
    pump_frames(5, sleep=0.05)
    capture_screenshot(app, name)
    popup.preview_popup.dismiss()
    popup.dismiss()
    pump_frames(2)
    save_or_compare_reference(name, visual_reference_config, update_references)


class TestProbingRoutinePopups:
    """Screenshots of each probing routine tab and its settings panel."""

    @pytest.mark.parametrize(
        ("name", "tab_text"),
        [
            pytest.param(
                reference_name("probing_popup_outside_corners"),
                "Outside Corners",
                marks=pytest.mark.visual_reference(reference_name("probing_popup_outside_corners")),
            ),
            pytest.param(
                reference_name("probing_popup_inside_corners"),
                "Inside Corners",
                marks=pytest.mark.visual_reference(reference_name("probing_popup_inside_corners")),
            ),
            pytest.param(
                reference_name("probing_popup_single_axis"),
                "Single Axis",
                marks=pytest.mark.visual_reference(reference_name("probing_popup_single_axis")),
            ),
            pytest.param(
                reference_name("probing_popup_bore_pocket"),
                "Bore/Pocket",
                marks=pytest.mark.visual_reference(reference_name("probing_popup_bore_pocket")),
            ),
            pytest.param(
                reference_name("probing_popup_boss_block"),
                "Boss/Block",
                marks=pytest.mark.visual_reference(reference_name("probing_popup_boss_block")),
            ),
            pytest.param(
                reference_name("probing_popup_angle"),
                "Angle",
                marks=pytest.mark.visual_reference(reference_name("probing_popup_angle")),
            ),
            pytest.param(
                reference_name("probing_popup_probe_tip"),
                "ProbeTip",
                marks=pytest.mark.visual_reference(reference_name("probing_popup_probe_tip")),
            ),
            pytest.param(
                reference_name("probing_popup_calibration"),
                "Calibration",
                marks=pytest.mark.visual_reference(reference_name("probing_popup_calibration")),
            ),
            pytest.param(
                reference_name("probing_popup_fourth_axis"),
                "4th Axis",
                marks=pytest.mark.visual_reference(reference_name("probing_popup_fourth_axis")),
            ),
        ],
    )
    def test_probing_routine_tab(
        self, kivy_app, connected_idle_state, name, tab_text, update_references, visual_reference_config
    ):
        apply_machine_state(kivy_app)
        popup = setup_probing_popup_tab(kivy_app, tab_text)
        capture_screenshot(kivy_app, name)
        popup.dismiss()
        pump_frames(2)
        save_or_compare_reference(name, visual_reference_config, update_references)


class TestProbingPreviewPopups:
    """Screenshots of generated probing-operation confirmation dialogs."""

    @pytest.mark.visual_reference(reference_name("probing_preview_single_axis_z"))
    def test_single_axis_z_preview(self, kivy_app, connected_idle_state, update_references, visual_reference_config):
        apply_machine_state(kivy_app)
        popup = setup_probing_popup_tab(kivy_app, "Single Axis")
        pump_frames(5, sleep=0.05)
        popup.single_axis_settings.setting_changed("ZAxisDistance", "-8")
        popup.single_axis_settings.setting_changed("FastFeedRate", "120")
        popup.on_single_axis_probing_pressed("WorkpieceTop")
        capture_probing_preview_state(
            kivy_app,
            popup,
            reference_name("probing_preview_single_axis_z"),
            update_references,
            visual_reference_config,
        )

    @pytest.mark.visual_reference(reference_name("probing_preview_outside_corner"))
    def test_outside_corner_preview(self, kivy_app, connected_idle_state, update_references, visual_reference_config):
        apply_machine_state(kivy_app)
        popup = setup_probing_popup_tab(kivy_app, "Outside Corners")
        pump_frames(5, sleep=0.05)
        popup.outside_corner_settings.setting_changed("XAxisDistance", "18")
        popup.outside_corner_settings.setting_changed("YAxisDistance", "14")
        popup.outside_corner_settings.setting_changed("ProbeDepth", "2")
        popup.on_outside_corner_probing_pressed("TopLeft")
        capture_probing_preview_state(
            kivy_app,
            popup,
            reference_name("probing_preview_outside_corner"),
            update_references,
            visual_reference_config,
        )

    @pytest.mark.visual_reference(reference_name("probing_preview_bore_center"))
    def test_bore_center_preview(self, kivy_app, connected_idle_state, update_references, visual_reference_config):
        apply_machine_state(kivy_app)
        popup = setup_probing_popup_tab(kivy_app, "Bore/Pocket")
        pump_frames(5, sleep=0.05)
        popup.bore_settings.setting_changed("XAxisDistance", "22")
        popup.bore_settings.setting_changed("YAxisDistance", "22")
        popup.bore_settings.setting_changed("ProbeTipDiameter", "3.175")
        popup.on_bore_probing_pressed("CenterBore")
        capture_probing_preview_state(
            kivy_app,
            popup,
            reference_name("probing_preview_bore_center"),
            update_references,
            visual_reference_config,
        )

    @pytest.mark.visual_reference(reference_name("probing_preview_inside_corner"))
    def test_inside_corner_preview(self, kivy_app, connected_idle_state, update_references, visual_reference_config):
        apply_machine_state(kivy_app)
        popup = setup_probing_popup_tab(kivy_app, "Inside Corners")
        pump_frames(5, sleep=0.05)
        popup.inside_corner_settings.setting_changed("XAxisDistance", "18")
        popup.inside_corner_settings.setting_changed("YAxisDistance", "16")
        popup.inside_corner_settings.setting_changed("ProbeDepth", "2.5")
        popup.inside_corner_settings.setting_changed("ProbeTipDiameter", "3.175")
        popup.on_inside_corner_probing_pressed("BottomRight")
        capture_probing_preview_state(
            kivy_app,
            popup,
            reference_name("probing_preview_inside_corner"),
            update_references,
            visual_reference_config,
        )

    @pytest.mark.visual_reference(reference_name("probing_preview_boss_block"))
    def test_boss_block_preview(self, kivy_app, connected_idle_state, update_references, visual_reference_config):
        apply_machine_state(kivy_app)
        popup = setup_probing_popup_tab(kivy_app, "Boss/Block")
        pump_frames(5, sleep=0.05)
        popup.boss_settings.setting_changed("XAxisDistance", "25")
        popup.boss_settings.setting_changed("YAxisDistance", "18")
        popup.boss_settings.setting_changed("ProbeDepth", "3")
        popup.boss_settings.setting_changed("ProbeClearance", "6")
        popup.boss_settings.setting_changed("ProbeTipDiameter", "3.175")
        popup.on_boss_probing_pressed("CenterBlock")
        capture_probing_preview_state(
            kivy_app,
            popup,
            reference_name("probing_preview_boss_block"),
            update_references,
            visual_reference_config,
        )

    @pytest.mark.visual_reference(reference_name("probing_preview_angle_y_right"))
    def test_angle_y_right_preview(self, kivy_app, connected_idle_state, update_references, visual_reference_config):
        apply_machine_state(kivy_app)
        popup = setup_probing_popup_tab(kivy_app, "Angle")
        pump_frames(5, sleep=0.05)
        popup.angle_settings.setting_changed("YAxisDistance", "24")
        popup.angle_settings.setting_changed("ProbeDepth", "2")
        popup.angle_settings.setting_changed("QAngle", "12")
        popup.angle_settings.setting_changed("FastFeedRate", "150")
        popup.on_angle_probing_pressed("YRight")
        capture_probing_preview_state(
            kivy_app,
            popup,
            reference_name("probing_preview_angle_y_right"),
            update_references,
            visual_reference_config,
        )

    @pytest.mark.visual_reference(reference_name("probing_preview_probe_tip_bore"))
    def test_probe_tip_bore_preview(self, kivy_app, connected_idle_state, update_references, visual_reference_config):
        apply_machine_state(kivy_app)
        popup = setup_probing_popup_tab(kivy_app, "ProbeTip")
        pump_frames(5, sleep=0.05)
        popup.probeTipSettings.setting_changed("XAxisDistance", "14")
        popup.probeTipSettings.setting_changed("ProbeDepth", "2")
        popup.probeTipSettings.setting_changed("ProbeClearance", "4")
        popup.on_probeTip_probing_pressed("Bore")
        capture_probing_preview_state(
            kivy_app,
            popup,
            reference_name("probing_preview_probe_tip_bore"),
            update_references,
            visual_reference_config,
        )

    @pytest.mark.visual_reference(reference_name("probing_preview_calibration_fourth_z"))
    def test_calibration_fourth_z_preview(
        self, kivy_app, connected_idle_state, update_references, visual_reference_config
    ):
        apply_machine_state(kivy_app)
        popup = setup_probing_popup_tab(kivy_app, "Calibration")
        pump_frames(5, sleep=0.05)
        popup.calibration_settings.setting_changed("XAxisDistance", "20")
        popup.calibration_settings.setting_changed("PinDiameter", "6")
        popup.calibration_settings.setting_changed("ProbeTipDiameter", "3.175")
        popup.on_callibration_probing_pressed("FourthZ")
        capture_probing_preview_state(
            kivy_app,
            popup,
            reference_name("probing_preview_calibration_fourth_z"),
            update_references,
            visual_reference_config,
        )

    @pytest.mark.visual_reference(reference_name("probing_preview_fourth_axis_level"))
    def test_fourth_axis_level_preview(
        self, kivy_app, connected_idle_state, update_references, visual_reference_config
    ):
        apply_machine_state(kivy_app)
        popup = setup_probing_popup_tab(kivy_app, "4th Axis")
        pump_frames(5, sleep=0.05)
        popup.fourth_axis_settings.setting_changed("YTotalDistance", "36")
        popup.fourth_axis_settings.setting_changed("ProbeHeight", "8")
        popup.fourth_axis_settings.setting_changed("FeedRate", "120")
        popup.fourth_axis_settings.setting_changed("RetractDistance", "2")
        popup.on_fourth_axis_probing_pressed("Level")
        capture_probing_preview_state(
            kivy_app,
            popup,
            reference_name("probing_preview_fourth_axis_level"),
            update_references,
            visual_reference_config,
        )


class TestProbeSelectionPopups:
    """Screenshots of probing entry states when the wrong tool is loaded."""

    @pytest.mark.visual_reference(reference_name("select_probe_popup_wrong_tool"))
    def test_select_probe_popup_wrong_tool(
        self, kivy_app, connected_idle_state, update_references, visual_reference_config
    ):
        from carveracontroller.CNC import CNC

        apply_machine_state(kivy_app)
        kivy_app.is_community_firmware = True
        CNC.vars["tool"] = 1
        kivy_app.root.open_probing_popup()
        pump_frames(5)
        name = reference_name("select_probe_popup_wrong_tool")
        capture_screenshot(kivy_app, name)
        kivy_app.root.select_probe_popup.dismiss()
        pump_frames(2)
        save_or_compare_reference(name, visual_reference_config, update_references)
