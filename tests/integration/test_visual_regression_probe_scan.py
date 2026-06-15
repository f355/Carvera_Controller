"""Visual regression tests for the probe-scan addon popup."""

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


def find_tabbed_panel_with_tab(root, tab_text):
    for widget in root.walk():
        if hasattr(widget, "tab_list") and any(getattr(tab, "text", None) == tab_text for tab in widget.tab_list):
            return widget
    raise AssertionError(f"Could not find tabbed panel containing {tab_text!r}")


def setup_probe_scan_popup(app):
    from carveracontroller.CNC import CNC

    app.is_community_firmware = True
    app.fw_version_digitized = 999999
    CNC.vars["tool"] = 0
    CNC.vars["wx"] = 12.3456
    CNC.vars["wy"] = -7.25
    CNC.vars["wz"] = 3.0
    app.root.open_probe_scan_popup()
    popup = app.root.probe_scan_popup
    pump_frames(5, sleep=0.05)
    return popup


def set_probe_scan_tab(popup, tab_text):
    tabbed_panel = find_tabbed_panel_with_tab(popup, tab_text)
    switch_tab_by_text(tabbed_panel, tab_text)


def set_icon_toggle_state(root, image_suffix):
    matches = [widget for widget in root.walk() if getattr(widget, "image", "").endswith(image_suffix)]
    if not matches:
        raise AssertionError(f"Could not find probe-scan icon ending with {image_suffix!r}")
    matches[0].state = "down"
    pump_frames(5)


def add_probe_scan_sample_features(popup):
    from carveracontroller.addons.probe_scan.core.session import ProbeScanFeature

    popup.session.features.extend(
        [
            ProbeScanFeature.new_point("Stored position", 12.3456, -7.25, 3.0, source="Manual"),
            ProbeScanFeature.new_circle("Manual circle", 20.0, 15.0, 6.0),
        ]
    )
    popup._refresh_feature_ui()
    pump_frames(5)


def add_probe_scan_dense_feature_list(popup):
    from carveracontroller.addons.probe_scan.core.session import ProbeScanFeature

    popup.session.features.extend(
        [
            ProbeScanFeature.new_point("Stock lower left", 0.0, 0.0, 0.0, source="Manual"),
            ProbeScanFeature.new_point("Stock lower right", 80.0, 0.0, 0.0, source="Manual"),
            ProbeScanFeature.new_point("Stock upper right", 80.0, 50.0, 0.0, source="Manual"),
            ProbeScanFeature.new_point("Stock upper left", 0.0, 50.0, 0.0, source="Manual"),
            ProbeScanFeature.new_circle("Fixture bore", 18.0, 14.0, 3.25),
            ProbeScanFeature.new_circle("Locating boss", 58.0, 32.0, 4.0),
        ]
    )
    popup._selection_order[:] = [popup.session.features[0].id, popup.session.features[1].id]
    popup._preview_focus_id = popup.session.features[4].id
    popup._refresh_feature_ui()
    pump_frames(5)


def hide_probe_scan_feature(popup, index):
    popup.session.features[index].sketch_visible = False
    popup._refresh_feature_ui()
    pump_frames(5)


def add_probe_scan_construct_selection(popup):
    from carveracontroller.addons.probe_scan.core.session import ProbeScanFeature

    features = [
        ProbeScanFeature.new_point("Corner A", 0.0, 0.0, 0.0, source="Manual"),
        ProbeScanFeature.new_point("Corner B", 28.0, 0.0, 0.0, source="Manual"),
        ProbeScanFeature.new_point("Corner C", 28.0, 18.0, 0.0, source="Manual"),
        ProbeScanFeature.new_circle("Measured bore", 14.0, 9.0, 4.25),
    ]
    popup.session.features.extend(features)
    popup._selection_order[:] = [features[0].id, features[1].id]
    popup._preview_focus_id = features[2].id
    popup._refresh_feature_ui()
    pump_frames(5)


def stabilize_scrollbar_colors(root):
    for widget in root.walk():
        if not hasattr(widget, "_bar_color") or not hasattr(widget, "bar_inactive_color"):
            continue
        inactive_trigger = getattr(widget, "_bind_inactive_bar_color_ev", None)
        if inactive_trigger is not None:
            inactive_trigger.cancel()
        widget._bar_color = widget.bar_inactive_color


def find_button_with_text(root, text):
    matches = [widget for widget in root.walk() if getattr(widget, "text", None) == text]
    if not matches:
        raise AssertionError(f"Could not find button {text!r}")
    return max(matches, key=lambda widget: widget.y)


def dismiss_open_dropdowns():
    from kivy.core.window import Window
    from kivy.uix.dropdown import DropDown

    for widget in list(Window.children):
        if isinstance(widget, DropDown):
            widget.dismiss()


def dismiss_popup_with_title(title):
    from kivy.core.window import Window
    from kivy.uix.popup import Popup

    for widget in list(Window.children):
        if isinstance(widget, Popup) and widget.title == title:
            widget.dismiss()
            return
    raise AssertionError(f"Could not find popup titled {title!r}")


def capture_probe_scan_state(app, popup, name, update_references, visual_reference_config):
    stabilize_scrollbar_colors(popup)
    capture_screenshot(app, name)
    popup.dismiss()
    pump_frames(2)
    save_or_compare_reference(name, visual_reference_config, update_references)


class TestProbeScanPopupStates:
    """Screenshots of stable probe-scan tabs and selected probing presets."""

    @pytest.mark.visual_reference(reference_name("probe_scan_manual_with_features"))
    def test_manual_tab_with_features(self, kivy_app, connected_idle_state, update_references, visual_reference_config):
        apply_machine_state(kivy_app)
        popup = setup_probe_scan_popup(kivy_app)
        set_probe_scan_tab(popup, "Manual")
        add_probe_scan_sample_features(popup)
        capture_probe_scan_state(
            kivy_app,
            popup,
            reference_name("probe_scan_manual_with_features"),
            update_references,
            visual_reference_config,
        )

    @pytest.mark.visual_reference(reference_name("probe_scan_touch_left_preset"))
    def test_touch_tab_left_preset(self, kivy_app, connected_idle_state, update_references, visual_reference_config):
        apply_machine_state(kivy_app)
        popup = setup_probe_scan_popup(kivy_app)
        set_probe_scan_tab(popup, "Touch")
        set_icon_toggle_state(popup, "single_axis/X+.png")
        capture_probe_scan_state(
            kivy_app,
            popup,
            reference_name("probe_scan_touch_left_preset"),
            update_references,
            visual_reference_config,
        )

    @pytest.mark.visual_reference(reference_name("probe_scan_bore_center_preset"))
    def test_bore_tab_center_preset(self, kivy_app, connected_idle_state, update_references, visual_reference_config):
        apply_machine_state(kivy_app)
        popup = setup_probe_scan_popup(kivy_app)
        set_probe_scan_tab(popup, "Bore")
        set_icon_toggle_state(popup, "inside_center/inside_center_circular_bore.png")
        capture_probe_scan_state(
            kivy_app,
            popup,
            reference_name("probe_scan_bore_center_preset"),
            update_references,
            visual_reference_config,
        )

    @pytest.mark.visual_reference(reference_name("probe_scan_angle_right_preset"))
    def test_angle_tab_right_preset(self, kivy_app, connected_idle_state, update_references, visual_reference_config):
        apply_machine_state(kivy_app)
        popup = setup_probe_scan_popup(kivy_app)
        set_probe_scan_tab(popup, "Angle")
        set_icon_toggle_state(popup, "angle/probe_angle_y_right.png")
        capture_probe_scan_state(
            kivy_app,
            popup,
            reference_name("probe_scan_angle_right_preset"),
            update_references,
            visual_reference_config,
        )

    @pytest.mark.visual_reference(reference_name("probe_scan_boss_block_preset"))
    def test_boss_tab_block_preset(self, kivy_app, connected_idle_state, update_references, visual_reference_config):
        apply_machine_state(kivy_app)
        popup = setup_probe_scan_popup(kivy_app)
        set_probe_scan_tab(popup, "Boss")
        set_icon_toggle_state(popup, "outside_center/outside_center_rect_boss.png")
        capture_probe_scan_state(
            kivy_app,
            popup,
            reference_name("probe_scan_boss_block_preset"),
            update_references,
            visual_reference_config,
        )

    @pytest.mark.visual_reference(reference_name("probe_scan_corner_in_top_left_preset"))
    def test_corner_in_tab_top_left_preset(
        self, kivy_app, connected_idle_state, update_references, visual_reference_config
    ):
        apply_machine_state(kivy_app)
        popup = setup_probe_scan_popup(kivy_app)
        set_probe_scan_tab(popup, "Corner in")
        set_icon_toggle_state(popup, "inside_corner/inX+Y-.png")
        capture_probe_scan_state(
            kivy_app,
            popup,
            reference_name("probe_scan_corner_in_top_left_preset"),
            update_references,
            visual_reference_config,
        )

    @pytest.mark.visual_reference(reference_name("probe_scan_corner_out_bottom_right_preset"))
    def test_corner_out_tab_bottom_right_preset(
        self, kivy_app, connected_idle_state, update_references, visual_reference_config
    ):
        apply_machine_state(kivy_app)
        popup = setup_probe_scan_popup(kivy_app)
        set_probe_scan_tab(popup, "Corner out")
        set_icon_toggle_state(popup, "outside_corner/X-Y+.png")
        capture_probe_scan_state(
            kivy_app,
            popup,
            reference_name("probe_scan_corner_out_bottom_right_preset"),
            update_references,
            visual_reference_config,
        )

    @pytest.mark.visual_reference(reference_name("probe_scan_construct_selection"))
    def test_construct_selection_with_features(
        self, kivy_app, connected_idle_state, update_references, visual_reference_config
    ):
        apply_machine_state(kivy_app)
        popup = setup_probe_scan_popup(kivy_app)
        set_probe_scan_tab(popup, "Manual")
        add_probe_scan_construct_selection(popup)
        capture_probe_scan_state(
            kivy_app,
            popup,
            reference_name("probe_scan_construct_selection"),
            update_references,
            visual_reference_config,
        )

    @pytest.mark.visual_reference(reference_name("probe_scan_jog_overlay"))
    def test_jog_overlay(self, kivy_app, connected_idle_state, update_references, visual_reference_config):
        apply_machine_state(kivy_app)
        popup = setup_probe_scan_popup(kivy_app)
        popup.open_jog_popup()
        pump_frames(10, sleep=0.02)
        name = reference_name("probe_scan_jog_overlay")
        capture_screenshot(kivy_app, name)
        popup._dismiss_jog_popup()
        popup.dismiss()
        pump_frames(2)
        save_or_compare_reference(name, visual_reference_config, update_references)


class TestProbeScanFeatureActions:
    """Screenshots of feature-list actions and session controls."""

    @pytest.mark.visual_reference(reference_name("probe_scan_feature_list_hidden_selection"))
    def test_feature_list_hidden_selection(
        self, kivy_app, connected_idle_state, update_references, visual_reference_config
    ):
        apply_machine_state(kivy_app)
        popup = setup_probe_scan_popup(kivy_app)
        set_probe_scan_tab(popup, "Manual")
        add_probe_scan_dense_feature_list(popup)
        hide_probe_scan_feature(popup, 2)
        capture_probe_scan_state(
            kivy_app,
            popup,
            reference_name("probe_scan_feature_list_hidden_selection"),
            update_references,
            visual_reference_config,
        )

    @pytest.mark.visual_reference(reference_name("probe_scan_copy_format_dropdown"))
    def test_copy_format_dropdown(self, kivy_app, connected_idle_state, update_references, visual_reference_config):
        apply_machine_state(kivy_app)
        popup = setup_probe_scan_popup(kivy_app)
        add_probe_scan_sample_features(popup)
        anchor = find_button_with_text(popup, "Copy as...")
        popup.open_copy_format_dropdown(anchor)
        pump_frames(5)
        name = reference_name("probe_scan_copy_format_dropdown")
        stabilize_scrollbar_colors(popup)
        capture_screenshot(kivy_app, name)
        dismiss_open_dropdowns()
        popup.dismiss()
        pump_frames(2)
        save_or_compare_reference(name, visual_reference_config, update_references)

    @pytest.mark.visual_reference(reference_name("probe_scan_save_format_dropdown"))
    def test_save_format_dropdown(self, kivy_app, connected_idle_state, update_references, visual_reference_config):
        apply_machine_state(kivy_app)
        popup = setup_probe_scan_popup(kivy_app)
        add_probe_scan_sample_features(popup)
        anchor = find_button_with_text(popup, "Save as...")
        popup.open_save_format_dropdown(anchor)
        pump_frames(5)
        name = reference_name("probe_scan_save_format_dropdown")
        stabilize_scrollbar_colors(popup)
        capture_screenshot(kivy_app, name)
        dismiss_open_dropdowns()
        popup.dismiss()
        pump_frames(2)
        save_or_compare_reference(name, visual_reference_config, update_references)

    @pytest.mark.visual_reference(reference_name("probe_scan_rename_feature_popup"))
    def test_rename_feature_popup(self, kivy_app, connected_idle_state, update_references, visual_reference_config):
        apply_machine_state(kivy_app)
        popup = setup_probe_scan_popup(kivy_app)
        add_probe_scan_sample_features(popup)
        popup._on_rename_feature(popup.session.features[0].id)
        pump_frames(5)
        name = reference_name("probe_scan_rename_feature_popup")
        stabilize_scrollbar_colors(popup)
        capture_screenshot(kivy_app, name)
        dismiss_popup_with_title("Rename feature")
        popup.dismiss()
        pump_frames(2)
        save_or_compare_reference(name, visual_reference_config, update_references)

    @pytest.mark.visual_reference(reference_name("probe_scan_reset_confirm"))
    def test_reset_confirm(self, kivy_app, connected_idle_state, update_references, visual_reference_config):
        apply_machine_state(kivy_app)
        popup = setup_probe_scan_popup(kivy_app)
        add_probe_scan_sample_features(popup)
        popup.on_reset_session()
        pump_frames(5)
        name = reference_name("probe_scan_reset_confirm")
        stabilize_scrollbar_colors(popup)
        capture_screenshot(kivy_app, name)
        kivy_app.root.confirm_popup.dismiss()
        popup.dismiss()
        pump_frames(2)
        save_or_compare_reference(name, visual_reference_config, update_references)

    @pytest.mark.visual_reference(reference_name("probe_scan_probing_locked_banner"))
    def test_probing_locked_banner(self, kivy_app, connected_idle_state, update_references, visual_reference_config):
        apply_machine_state(kivy_app)
        popup = setup_probe_scan_popup(kivy_app)
        add_probe_scan_dense_feature_list(popup)
        popup.probing_status_text = "Running M461 bore center probe..."
        popup.is_probing = True
        popup._apply_probing_ui_lock()
        pump_frames(5)
        name = reference_name("probe_scan_probing_locked_banner")
        stabilize_scrollbar_colors(popup)
        capture_screenshot(kivy_app, name)
        popup.is_probing = False
        popup.dismiss()
        pump_frames(2)
        save_or_compare_reference(name, visual_reference_config, update_references)
