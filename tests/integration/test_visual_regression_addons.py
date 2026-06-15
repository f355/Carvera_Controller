"""Visual regression tests for addon workflow popups."""

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


def capture_popup_state(app, popup, name, update_references, visual_reference_config, frames=5):
    show_content_page(app, "Control")
    popup.open()
    pump_frames(frames)
    capture_screenshot(app, name)
    popup.dismiss()
    pump_frames(2)
    save_or_compare_reference(name, visual_reference_config, update_references)


def open_facing_wizard(app):
    show_content_page(app, "Control")
    app.is_community_firmware = True
    popup = app.root.facing_popup
    popup.open()
    pump_frames(20)
    return popup


def set_facing_wizard_tab(popup, tab_text):
    tabbed_panel = find_tabbed_panel_with_tab(popup, tab_text)
    switch_tab_by_text(tabbed_panel, tab_text)


def capture_facing_wizard_state(app, popup, name, update_references, visual_reference_config):
    pump_frames(10, sleep=0.02)
    capture_screenshot(app, name)
    popup.dismiss()
    pump_frames(2)
    save_or_compare_reference(name, visual_reference_config, update_references)


class TestAddonWorkflowPopups:
    """Screenshots of addon modals that combine controls and preview panes."""

    @pytest.mark.visual_reference(reference_name("facing_wizard_popup_stock_tab"))
    def test_facing_wizard_popup_stock_tab(
        self, kivy_app, connected_idle_state, update_references, visual_reference_config
    ):
        apply_machine_state(kivy_app)
        kivy_app.is_community_firmware = True
        capture_popup_state(
            kivy_app,
            kivy_app.root.facing_popup,
            reference_name("facing_wizard_popup_stock_tab"),
            update_references,
            visual_reference_config,
            frames=20,
        )

    @pytest.mark.visual_reference(reference_name("facing_wizard_presets_menu_dropdown"))
    def test_facing_wizard_presets_menu_dropdown(
        self, kivy_app, connected_idle_state, update_references, visual_reference_config
    ):
        apply_machine_state(kivy_app)
        kivy_app.is_community_firmware = True
        popup = kivy_app.root.facing_popup
        popup.open()
        pump_frames(20)
        popup.open_presets_menu(popup.ids.btn_presets_menu)
        pump_frames(5)
        name = reference_name("facing_wizard_presets_menu_dropdown")
        capture_screenshot(kivy_app, name)
        popup.dismiss()
        pump_frames(2)
        save_or_compare_reference(name, visual_reference_config, update_references)

    @pytest.mark.visual_reference(reference_name("facing_wizard_cutting_spiral_finish"))
    def test_facing_wizard_cutting_spiral_finish(
        self, kivy_app, connected_idle_state, update_references, visual_reference_config
    ):
        apply_machine_state(kivy_app)
        popup = open_facing_wizard(kivy_app)
        set_facing_wizard_tab(popup, "Cutting")
        popup.ids.raster_spiral_btn.state = "down"
        popup.ids.chk_finish.active = True
        capture_facing_wizard_state(
            kivy_app,
            popup,
            reference_name("facing_wizard_cutting_spiral_finish"),
            update_references,
            visual_reference_config,
        )

    @pytest.mark.visual_reference(reference_name("facing_wizard_z_probe_grid_enabled"))
    def test_facing_wizard_z_probe_grid_enabled(
        self, kivy_app, connected_idle_state, update_references, visual_reference_config
    ):
        apply_machine_state(kivy_app)
        popup = open_facing_wizard(kivy_app)
        set_facing_wizard_tab(popup, "Z probe grid")
        popup.ids.chk_probe.active = True
        popup.ids.txt_grid_nx.text = "4"
        popup.ids.txt_grid_ny.text = "3"
        popup.ids.txt_probe_inset.text = "2"
        capture_facing_wizard_state(
            kivy_app,
            popup,
            reference_name("facing_wizard_z_probe_grid_enabled"),
            update_references,
            visual_reference_config,
        )

    @pytest.mark.visual_reference(reference_name("facing_wizard_tool_misc_ext_port"))
    def test_facing_wizard_tool_misc_ext_port(
        self, kivy_app, connected_idle_state, update_references, visual_reference_config
    ):
        apply_machine_state(kivy_app)
        popup = open_facing_wizard(kivy_app)
        set_facing_wizard_tab(popup, "Tool / Misc.")
        popup.ids.txt_m6_t.text = "7"
        popup.ids.spn_m6_collet.text = "6 mm"
        popup.ids.chk_ext_port.active = True
        popup.ids.txt_ext_port_s.text = "80"
        capture_facing_wizard_state(
            kivy_app,
            popup,
            reference_name("facing_wizard_tool_misc_ext_port"),
            update_references,
            visual_reference_config,
        )

    @pytest.mark.visual_reference(reference_name("facing_wizard_gcode_menu_dropdown"))
    def test_facing_wizard_gcode_menu_dropdown(
        self, kivy_app, connected_idle_state, update_references, visual_reference_config
    ):
        apply_machine_state(kivy_app)
        kivy_app.is_community_firmware = True
        popup = kivy_app.root.facing_popup
        popup.open()
        pump_frames(20)
        popup.open_gcode_menu(popup.ids.btn_gcode_menu)
        pump_frames(5)
        name = reference_name("facing_wizard_gcode_menu_dropdown")
        capture_screenshot(kivy_app, name)
        popup.dismiss()
        pump_frames(2)
        save_or_compare_reference(name, visual_reference_config, update_references)
