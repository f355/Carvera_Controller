"""Visual regression tests for file, MDI, and command surfaces."""

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


def capture_dropdown_state(app, dropdown, anchor, name, update_references, visual_reference_config, frames=5):
    show_content_page(app, "File")
    if dropdown.parent:
        dropdown.parent.remove_widget(dropdown)
    dropdown.open(anchor)
    if hasattr(dropdown, "opened"):
        dropdown.opened = True
    pump_frames(frames)
    capture_screenshot(app, name)
    dropdown.dismiss()
    pump_frames(2)
    save_or_compare_reference(name, visual_reference_config, update_references)


def setup_file_popup_remote_page(app):
    popup = app.root.file_popup
    popup.firmware_mode = False
    popup.popup_manager.transition.duration = 0
    popup.popup_manager.current = "remote_page"
    popup.remote_rv.curr_dir = "/sd/gcodes/projects"
    popup.remote_rv.curr_dir_name = "projects"
    popup.remote_rv.curr_full_path_list = ["/sd/gcodes", "/sd/gcodes/projects"]
    popup.remote_rv.curr_path_list = ["root", "projects"]
    popup.remote_rv.curr_file_list_buff = [
        {"name": "fixtures", "is_dir": True, "size": 0, "date": 1_700_000_000},
        {"name": "Face 4x4 stock.cnc", "is_dir": False, "size": 18432, "date": 1_700_000_300},
        {"name": "rotary-indexing.nc", "is_dir": False, "size": 9216, "date": 1_700_000_600},
    ]
    popup.remote_rv.fill_dir(switch_reverse=False)
    return popup


def setup_file_popup_local_page(app):
    popup = app.root.file_popup
    popup.firmware_mode = False
    popup.popup_manager.transition.duration = 0
    popup.popup_manager.current = "local_page"
    popup.local_rv.curr_dir = "/workspace/gcodes"
    popup.local_rv.curr_dir_name = "gcodes"
    popup.local_rv.curr_full_path_list = ["/workspace", "/workspace/gcodes"]
    popup.local_rv.curr_path_list = ["workspace", "gcodes"]
    popup.local_rv.curr_file_list_buff = [
        {"name": "calibration", "is_dir": True, "size": 0, "date": 1_700_001_000},
        {"name": "surfacing-pass.cnc", "is_dir": False, "size": 12345, "date": 1_700_001_300},
        {"name": "probe-grid-test.nc", "is_dir": False, "size": 6789, "date": 1_700_001_600},
    ]
    popup.local_rv.fill_dir(switch_reverse=False)
    return popup


def setup_file_popup_firmware_page(app):
    popup = app.root.file_popup
    popup.firmware_mode = True
    popup.popup_manager.transition.duration = 0
    popup.popup_manager.current = "local_page"
    popup.local_rv.curr_dir = "/workspace/firmware"
    popup.local_rv.curr_dir_name = "firmware"
    popup.local_rv.curr_full_path_list = ["/workspace", "/workspace/firmware"]
    popup.local_rv.curr_path_list = ["workspace", "firmware"]
    popup.local_rv.curr_file_list_buff = [
        {"name": "carvera-controller-2.0.0.bin", "is_dir": False, "size": 2_048_000, "date": 1_700_002_000},
        {"name": "README.txt", "is_dir": False, "size": 4096, "date": 1_700_002_300},
    ]
    popup.local_rv.fill_dir(switch_reverse=False)
    return popup


def setup_manual_command_page(app):
    show_content_page(app, "File")
    app.root.cmd_manager.current = "manual_cmd_page"
    app.root.manual_rv.data = [
        {"text": "> ?", "color": (225 / 255, 225 / 255, 225 / 255, 1)},
        {"text": "< Idle|MPos:-180.000,-120.000,-5.000|FS:0,0>", "color": (160 / 255, 160 / 255, 160 / 255, 1)},
        {"text": "> G0 X0 Y0", "color": (225 / 255, 225 / 255, 225 / 255, 1)},
    ]
    app.root.manual_cmd.text = "G38.2 Z-12 F80"
    app.root.manual_cmd.focus = False
    pump_frames(5)


def setup_gcode_command_page(app):
    show_content_page(app, "File")
    app.selected_remote_filename = "/sd/gcodes/projects/probe-grid-test.nc"
    app.curr_page = 2
    app.total_pages = 4
    app.loading_page = False
    app.root.cmd_manager.transition.duration = 0
    app.root.cmd_manager.current = "gcode_cmd_page"
    app.root.gcode_rv.data = [
        {
            "line_no": 251,
            "text": "G0 X0 Y0 Z10",
            "highlighted_text": "[color=ff0000]G0[/color] X0 Y0 Z10",
            "color": (200 / 255, 200 / 255, 200 / 255, 1),
        },
        {
            "line_no": 252,
            "text": "T15 M6",
            "highlighted_text": "T15 [color=ffc300]M6[/color]",
            "color": (200 / 255, 200 / 255, 200 / 255, 1),
        },
        {
            "line_no": 253,
            "text": "G38.2 Z-35 F120",
            "highlighted_text": "[color=00ccff]G38.2[/color] Z-35 F120",
            "color": (200 / 255, 200 / 255, 200 / 255, 1),
        },
        {
            "line_no": 254,
            "text": "G1 X80 Y60 F800",
            "highlighted_text": "[color=00ff00]G1[/color] X80 Y60 F800",
            "color": (200 / 255, 200 / 255, 200 / 255, 1),
        },
    ]
    app.root.gcode_rv.data_length = len(app.root.gcode_rv.data)
    pump_frames(5)


def setup_gcode_context_menu(app):
    from carveracontroller.main import GCodeLineContextMenu

    setup_gcode_command_page(app)
    app.root.coord_popup.cbx_startline.active = True
    app.root.coord_popup.txt_startline.text = "253"
    menu = GCodeLineContextMenu(253)
    app.root.add_widget(menu)
    menu.pos = (360, 520)
    pump_frames(5)
    return menu


def find_icon_button(root, icon):
    matches = [widget for widget in root.walk() if getattr(widget, "icon", None) == icon]
    if not matches:
        raise AssertionError(f"Could not find icon button {icon!r}")
    return max(matches, key=lambda widget: widget.y)


def setup_top_bar_dropdown(app, dropdown_name):
    from carveracontroller.CNC import CNC

    app.is_community_firmware = True
    app.fw_version_digitized = 999999
    CNC.can_rotate_wcs = True
    dropdown_map = {
        "status": (app.root.status_drop_down, app.root.status_data_view),
        "x_axis": (app.root.x_drop_down, app.root.x_data_view),
        "y_axis": (app.root.y_drop_down, app.root.y_data_view),
        "z_axis": (app.root.z_drop_down, app.root.z_data_view),
        "a_axis": (app.root.a_drop_down, app.root.a_data_view),
        "coordinate_system": (app.root.coordinate_system_drop_down, app.root.coord_system_data_view),
        "feed": (app.root.feed_drop_down, app.root.feed_data_view),
        "spindle": (app.root.spindle_drop_down, app.root.spindle_laser_data_view),
        "tool": (app.root.tool_drop_down, app.root.tool_data_view),
        "function_menu": (app.root.func_drop_down, find_icon_button(app.root, "data/list.png")),
    }
    dropdown, anchor = dropdown_map[dropdown_name]
    if dropdown_name == "coordinate_system":
        dropdown.update_ui()
    return dropdown, anchor


def setup_laser_top_bar_dropdown(app):
    from carveracontroller.CNC import CNC

    app.is_community_firmware = True
    app.lasering = True
    CNC.vars["lasermode"] = 1
    CNC.vars["laserpower"] = 18.5
    CNC.vars["laserscale"] = 70
    CNC.vars["lasertesting"] = 1
    app.root.spindle_laser_data_view.data_icon = "data/laser.png"
    app.root.spindle_laser_data_view.main_text = "18.5"
    app.root.spindle_laser_data_view.minr_text = "70 %"
    app.root.spindle_laser_data_view.scale = 70
    app.root.spindle_laser_data_view.active = True
    app.root.laser_drop_down.status_scale.value = "70%"
    app.root.laser_drop_down.switch.set_flag = True
    app.root.laser_drop_down.switch.active = True
    app.root.laser_drop_down.test_switch.set_flag = True
    app.root.laser_drop_down.test_switch.active = True
    app.root.laser_drop_down.scale_slider.set_flag = True
    app.root.laser_drop_down.scale_slider.value = 70
    return app.root.laser_drop_down, app.root.spindle_laser_data_view


class TestFilePopupStates:
    """Screenshots of deterministic remote and local file chooser pages."""

    @pytest.mark.visual_reference(reference_name("file_popup_remote_page"))
    def test_remote_page(self, kivy_app, connected_idle_state, update_references, visual_reference_config):
        apply_machine_state(kivy_app)
        popup = setup_file_popup_remote_page(kivy_app)
        capture_popup_state(
            kivy_app, popup, reference_name("file_popup_remote_page"), update_references, visual_reference_config
        )

    @pytest.mark.visual_reference(reference_name("file_popup_local_page"))
    def test_local_page(self, kivy_app, connected_idle_state, update_references, visual_reference_config):
        apply_machine_state(kivy_app)
        popup = setup_file_popup_local_page(kivy_app)
        capture_popup_state(
            kivy_app, popup, reference_name("file_popup_local_page"), update_references, visual_reference_config
        )

    @pytest.mark.visual_reference(reference_name("file_popup_firmware_page"))
    def test_firmware_page(self, kivy_app, connected_idle_state, update_references, visual_reference_config):
        apply_machine_state(kivy_app)
        popup = setup_file_popup_firmware_page(kivy_app)
        capture_popup_state(
            kivy_app, popup, reference_name("file_popup_firmware_page"), update_references, visual_reference_config
        )

    @pytest.mark.visual_reference(reference_name("operation_dropdown_remote_file"))
    def test_operation_dropdown_remote_file(
        self, kivy_app, connected_idle_state, update_references, visual_reference_config
    ):
        apply_machine_state(kivy_app)
        popup = setup_file_popup_remote_page(kivy_app)
        popup.open()
        pump_frames(5)
        name = reference_name("operation_dropdown_remote_file")
        capture_dropdown_state(
            kivy_app,
            kivy_app.root.operation_drop_down,
            popup.btn_select,
            name,
            update_references,
            visual_reference_config,
        )
        popup.dismiss()
        pump_frames(2)


class TestCommandManagerStates:
    """Screenshots of command-manager states on the file page."""

    @pytest.mark.visual_reference(reference_name("manual_command_page_with_history"))
    def test_manual_command_page_with_history(
        self, kivy_app, connected_idle_state, update_references, visual_reference_config
    ):
        apply_machine_state(kivy_app)
        setup_manual_command_page(kivy_app)
        name = reference_name("manual_command_page_with_history")
        capture_screenshot(kivy_app, name)
        save_or_compare_reference(name, visual_reference_config, update_references)

    @pytest.mark.visual_reference(reference_name("gcode_command_page_loaded_rows"))
    def test_gcode_command_page_loaded_rows(
        self, kivy_app, connected_idle_state, update_references, visual_reference_config
    ):
        apply_machine_state(kivy_app)
        setup_gcode_command_page(kivy_app)
        name = reference_name("gcode_command_page_loaded_rows")
        capture_screenshot(kivy_app, name)
        save_or_compare_reference(name, visual_reference_config, update_references)

    @pytest.mark.visual_reference(reference_name("gcode_context_menu_resume_line"))
    def test_gcode_context_menu_resume_line(
        self, kivy_app, connected_idle_state, update_references, visual_reference_config
    ):
        apply_machine_state(kivy_app)
        menu = setup_gcode_context_menu(kivy_app)
        name = reference_name("gcode_context_menu_resume_line")
        capture_screenshot(kivy_app, name)
        menu.dismiss()
        pump_frames(2)
        save_or_compare_reference(name, visual_reference_config, update_references)


class TestTopBarDropdownStates:
    """Screenshots of the top-bar dropdowns above the file and MDI views."""

    @pytest.mark.parametrize(
        ("name", "dropdown_name"),
        [
            pytest.param(
                reference_name("top_bar_status_dropdown"),
                "status",
                marks=pytest.mark.visual_reference(reference_name("top_bar_status_dropdown")),
            ),
            pytest.param(
                reference_name("top_bar_x_axis_dropdown"),
                "x_axis",
                marks=pytest.mark.visual_reference(reference_name("top_bar_x_axis_dropdown")),
            ),
            pytest.param(
                reference_name("top_bar_y_axis_dropdown"),
                "y_axis",
                marks=pytest.mark.visual_reference(reference_name("top_bar_y_axis_dropdown")),
            ),
            pytest.param(
                reference_name("top_bar_z_axis_dropdown"),
                "z_axis",
                marks=pytest.mark.visual_reference(reference_name("top_bar_z_axis_dropdown")),
            ),
            pytest.param(
                reference_name("top_bar_a_axis_dropdown"),
                "a_axis",
                marks=pytest.mark.visual_reference(reference_name("top_bar_a_axis_dropdown")),
            ),
            pytest.param(
                reference_name("top_bar_coordinate_system_dropdown"),
                "coordinate_system",
                marks=pytest.mark.visual_reference(reference_name("top_bar_coordinate_system_dropdown")),
            ),
            pytest.param(
                reference_name("top_bar_feed_dropdown"),
                "feed",
                marks=pytest.mark.visual_reference(reference_name("top_bar_feed_dropdown")),
            ),
            pytest.param(
                reference_name("top_bar_spindle_dropdown"),
                "spindle",
                marks=pytest.mark.visual_reference(reference_name("top_bar_spindle_dropdown")),
            ),
            pytest.param(
                reference_name("top_bar_tool_dropdown"),
                "tool",
                marks=pytest.mark.visual_reference(reference_name("top_bar_tool_dropdown")),
            ),
            pytest.param(
                reference_name("top_bar_function_menu_dropdown"),
                "function_menu",
                marks=pytest.mark.visual_reference(reference_name("top_bar_function_menu_dropdown")),
            ),
        ],
    )
    def test_top_bar_dropdown(
        self, kivy_app, connected_idle_state, name, dropdown_name, update_references, visual_reference_config
    ):
        apply_machine_state(kivy_app)
        setup_manual_command_page(kivy_app)
        dropdown, anchor = setup_top_bar_dropdown(kivy_app, dropdown_name)
        capture_dropdown_state(kivy_app, dropdown, anchor, name, update_references, visual_reference_config)

    @pytest.mark.visual_reference(reference_name("top_bar_laser_dropdown_active"))
    def test_laser_dropdown_active(self, kivy_app, connected_idle_state, update_references, visual_reference_config):
        apply_machine_state(kivy_app)
        setup_manual_command_page(kivy_app)
        dropdown, anchor = setup_laser_top_bar_dropdown(kivy_app)
        capture_dropdown_state(
            kivy_app,
            dropdown,
            anchor,
            reference_name("top_bar_laser_dropdown_active"),
            update_references,
            visual_reference_config,
        )
