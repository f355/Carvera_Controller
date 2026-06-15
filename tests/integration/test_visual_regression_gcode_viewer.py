"""Visual regression tests for loaded G-code viewer controls."""

import os

import pytest

from tests.integration.conftest import (
    apply_machine_state,
    capture_screenshot,
    load_gcode_file,
    pump_frames,
    save_or_compare_reference,
    show_content_page,
    stabilize_gcode_viewer,
)

_TESTS_DIR = os.path.join(os.path.dirname(__file__), "..")
GCODE_FILE = os.path.join(_TESTS_DIR, "resources", "Face 4x4 stock.cnc")
REFERENCE_GROUP = os.path.splitext(os.path.basename(__file__))[0]


def reference_name(name):
    return f"{REFERENCE_GROUP}/{name}"


def setup_loaded_gcode_viewer(kivy_app):
    apply_machine_state(kivy_app)
    load_gcode_file(kivy_app, GCODE_FILE)
    show_content_page(kivy_app, "File")
    kivy_app.root.cmd_manager.current = "gcode_cmd_page"
    kivy_app.show_gcode_ctl_bar = True
    stabilize_gcode_viewer(kivy_app)
    kivy_app.root.refresh_gcode_color_legend()
    pump_frames(5)


def stabilize_scrollbar_color(widget):
    inactive_trigger = getattr(widget, "_bind_inactive_bar_color_ev", None)
    if inactive_trigger is not None:
        inactive_trigger.cancel()
    widget._bar_color = widget.bar_color


class TestLoadedGcodeViewerStates:
    """Screenshots of the loaded-program viewer toolbar and legend states."""

    @pytest.mark.visual_reference(reference_name("gcode_viewer_toolbar_default"))
    def test_toolbar_default(self, kivy_app, connected_idle_state, update_references, visual_reference_config):
        setup_loaded_gcode_viewer(kivy_app)
        name = reference_name("gcode_viewer_toolbar_default")
        capture_screenshot(kivy_app, name)
        save_or_compare_reference(name, visual_reference_config, update_references)

    @pytest.mark.visual_reference(reference_name("gcode_viewer_toolbar_grid_hidden"))
    def test_toolbar_grid_hidden(self, kivy_app, connected_idle_state, update_references, visual_reference_config):
        setup_loaded_gcode_viewer(kivy_app)
        kivy_app.root.float_layout.tool_bar.show_grid = False
        kivy_app.root.gcode_viewer.set_grid_visible(False)
        pump_frames(5)
        name = reference_name("gcode_viewer_toolbar_grid_hidden")
        capture_screenshot(kivy_app, name)
        save_or_compare_reference(name, visual_reference_config, update_references)

    @pytest.mark.visual_reference(reference_name("gcode_viewer_toolbar_ortho_projection"))
    def test_toolbar_ortho_projection(self, kivy_app, connected_idle_state, update_references, visual_reference_config):
        setup_loaded_gcode_viewer(kivy_app)
        kivy_app.root.float_layout.tool_bar.ortho_projection = True
        kivy_app.root.gcode_viewer.set_ortho_projection(True)
        pump_frames(5)
        name = reference_name("gcode_viewer_toolbar_ortho_projection")
        capture_screenshot(kivy_app, name)
        save_or_compare_reference(name, visual_reference_config, update_references)

    @pytest.mark.visual_reference(reference_name("gcode_viewer_color_legend_tool"))
    def test_color_legend_tool(self, kivy_app, connected_idle_state, update_references, visual_reference_config):
        setup_loaded_gcode_viewer(kivy_app)
        kivy_app.root.on_gcode_color_scheme_changed("Tool")
        pump_frames(5)
        name = reference_name("gcode_viewer_color_legend_tool")
        capture_screenshot(kivy_app, name)
        save_or_compare_reference(name, visual_reference_config, update_references)

    @pytest.mark.visual_reference(reference_name("gcode_viewer_color_legend_speed"))
    def test_color_legend_speed(self, kivy_app, connected_idle_state, update_references, visual_reference_config):
        setup_loaded_gcode_viewer(kivy_app)
        kivy_app.root.on_gcode_color_scheme_changed("Speed")
        pump_frames(5)
        stabilize_scrollbar_color(kivy_app.root.ids.color_scheme_panel.ids.legend_scroll)
        name = reference_name("gcode_viewer_color_legend_speed")
        capture_screenshot(kivy_app, name)
        save_or_compare_reference(name, visual_reference_config, update_references)
