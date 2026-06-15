"""Visual regression tests for settings and update workflow popups."""

import json
import os
import shutil

import pytest
from kivy.app import App
from kivy.uix.popup import Popup

from tests.integration.conftest import (
    OUTPUT_DIR,
    apply_machine_state,
    capture_screenshot,
    pump_frames,
    save_or_compare_reference,
    show_content_page,
)

REFERENCE_GROUP = os.path.splitext(os.path.basename(__file__))[0]
CONFIG_C1_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "carveracontroller", "config_c1.json")


def reference_name(name):
    return f"{REFERENCE_GROUP}/{name}"


def switch_tab_by_text(root, tab_text):
    for widget in root.walk():
        if not hasattr(widget, "tab_list"):
            continue
        for tab in widget.tab_list:
            if tab.text == tab_text:
                widget.switch_to(tab)
                pump_frames(5)
                return
    raise AssertionError(f"Could not find tab {tab_text!r}")


def capture_popup_state(app, popup, name, update_references, visual_reference_config, frames=5):
    show_content_page(app, "Control")
    popup.open()
    pump_frames(frames)
    capture_screenshot(app, name)
    popup.dismiss()
    pump_frames(2)
    save_or_compare_reference(name, visual_reference_config, update_references)


def load_connected_settings(app):
    App.get_running_app().model = "C1"
    app.root.config_loaded = True
    with open(CONFIG_C1_PATH) as config_file:
        config_data = json.load(config_file)
    for entry in config_data:
        if "key" in entry and entry.get("type") != "title":
            app.root.setting_list[entry["key"]] = entry.get("default", "0")
    app.root.load_machine_config()
    apply_machine_state(app)


def setup_config_popup_pending_changes(app):
    load_connected_settings(app)
    popup = app.root.config_popup
    popup.open()
    pump_frames(5)
    popup.btn_apply.disabled = False
    pump_frames(5)
    stabilize_settings_popup_scrollbars(popup)
    return popup


def setup_upgrade_popup_controller_update(app):
    app.ctl_has_update = True
    app.fw_has_update = False
    popup = app.root.upgrade_popup
    popup.cbx_check_at_startup.active = True
    popup.ctl_version_txt.text = "Controller 2.2.0 available"
    popup.ctl_upd_text.text = (
        "2.2.0\n"
        "- Improved visual layout for file and MDI surfaces.\n"
        "- Refined probing workflow controls.\n"
        "- Stability fixes for reconnect and update dialogs."
    )
    popup.fw_version_txt.text = "Firmware is current"
    popup.fw_upd_text.text = "No firmware update is available for this machine."
    return popup


def setup_upgrade_popup_firmware_update(app):
    app.ctl_has_update = False
    app.fw_has_update = True
    popup = app.root.upgrade_popup
    popup.cbx_check_at_startup.active = False
    popup.ctl_version_txt.text = "Controller is current"
    popup.ctl_upd_text.text = "No controller update is available."
    popup.fw_version_txt.text = "Firmware 2.1.4 available"
    popup.fw_upd_text.text = (
        "2.1.4\n"
        "- Adds probing command refinements.\n"
        "- Updates fourth-axis calibration behavior.\n"
        "- Requires machine reset after installation."
    )
    return popup


def setup_upgrade_popup_no_updates(app):
    app.ctl_has_update = False
    app.fw_has_update = False
    popup = app.root.upgrade_popup
    popup.cbx_check_at_startup.active = True
    popup.check_button.disabled = False
    popup.ctl_version_txt.text = "Controller is current"
    popup.ctl_upd_text.text = "No controller update is available for this installation."
    popup.fw_version_txt.text = "Firmware is current"
    popup.fw_upd_text.text = "No firmware update is available for this machine."
    return popup


def setup_config_restore_confirm(app):
    load_connected_settings(app)
    popup = app.root.config_popup
    popup.open()
    pump_frames(5)
    stabilize_settings_popup_scrollbars(popup)
    app.root.open_setting_restore_confirm_popup()
    pump_frames(5)
    return popup, app.root.confirm_popup


def stabilize_settings_popup_scrollbars(popup):
    for widget in popup.walk():
        if not hasattr(widget, "_bar_color") or not hasattr(widget, "bar_inactive_color"):
            continue
        inactive_trigger = getattr(widget, "_bind_inactive_bar_color_ev", None)
        if inactive_trigger is not None:
            inactive_trigger.cancel()
        widget._bar_color = widget.bar_inactive_color


def create_file_picker_fixture():
    fixture_dir = os.path.join(OUTPUT_DIR, "file_picker_fixture")
    shutil.rmtree(fixture_dir, ignore_errors=True)
    os.makedirs(os.path.join(fixture_dir, "00-machine-backups"))

    files = {
        "01-controller.ini": "[carvera]\nshow_update = 0\n",
        "02-firmware-settings.json": '{"zprobe": {"probe_tip_diameter": 3.175}}\n',
        "03-readme.txt": "Deterministic file picker fixture.\n",
    }
    for filename, content in files.items():
        path = os.path.join(fixture_dir, filename)
        with open(path, "w") as fixture_file:
            fixture_file.write(content)

    fixed_timestamp = 1_700_000_000
    for dirpath, dirnames, filenames in os.walk(fixture_dir):
        os.utime(dirpath, (fixed_timestamp, fixed_timestamp))
        for name in [*dirnames, *filenames]:
            os.utime(os.path.join(dirpath, name), (fixed_timestamp, fixed_timestamp))
    return fixture_dir


def setup_pick_file_popup():
    from carveracontroller.main import PickFilePopup

    fixture_dir = create_file_picker_fixture()
    content = PickFilePopup(lambda *_args: None, lambda: None)
    popup = Popup(
        title="Choose where to back up your machine configuration",
        content=content,
        size_hint=(0.75, 0.75),
        auto_dismiss=True,
    )
    content.ids.filechooser.rootpath = fixture_dir
    content.ids.filechooser.path = fixture_dir
    content.ids.filechooser.selection = [os.path.join(fixture_dir, "01-controller.ini")]
    return popup


class TestSettingsPopups:
    """Screenshots of settings workflow states that are not covered by baseline pages."""

    @pytest.mark.visual_reference(reference_name("config_popup_pending_changes"))
    def test_config_popup_pending_changes(
        self, kivy_app, connected_idle_state, update_references, visual_reference_config
    ):
        popup = setup_config_popup_pending_changes(kivy_app)
        name = reference_name("config_popup_pending_changes")
        capture_screenshot(kivy_app, name)
        popup.dismiss()
        pump_frames(2)
        save_or_compare_reference(name, visual_reference_config, update_references)

    @pytest.mark.visual_reference(reference_name("config_popup_restore_confirm"))
    def test_config_popup_restore_confirm(
        self, kivy_app, connected_idle_state, update_references, visual_reference_config
    ):
        popup, confirm_popup = setup_config_restore_confirm(kivy_app)
        name = reference_name("config_popup_restore_confirm")
        capture_screenshot(kivy_app, name)
        confirm_popup.dismiss()
        popup.dismiss()
        pump_frames(2)
        save_or_compare_reference(name, visual_reference_config, update_references)


class TestUpdatePopups:
    """Screenshots of deterministic controller and firmware update panels."""

    @pytest.mark.visual_reference(reference_name("upgrade_popup_controller_update"))
    def test_upgrade_popup_controller_update(self, kivy_app, update_references, visual_reference_config):
        popup = setup_upgrade_popup_controller_update(kivy_app)
        capture_popup_state(
            kivy_app,
            popup,
            reference_name("upgrade_popup_controller_update"),
            update_references,
            visual_reference_config,
        )

    @pytest.mark.visual_reference(reference_name("upgrade_popup_firmware_update"))
    def test_upgrade_popup_firmware_update(self, kivy_app, update_references, visual_reference_config):
        popup = setup_upgrade_popup_firmware_update(kivy_app)
        popup.open()
        pump_frames(5)
        switch_tab_by_text(popup, "Firmware")
        name = reference_name("upgrade_popup_firmware_update")
        capture_screenshot(kivy_app, name)
        popup.dismiss()
        pump_frames(2)
        save_or_compare_reference(name, visual_reference_config, update_references)

    @pytest.mark.visual_reference(reference_name("upgrade_popup_no_updates"))
    def test_upgrade_popup_no_updates(self, kivy_app, update_references, visual_reference_config):
        popup = setup_upgrade_popup_no_updates(kivy_app)
        capture_popup_state(
            kivy_app,
            popup,
            reference_name("upgrade_popup_no_updates"),
            update_references,
            visual_reference_config,
        )


class TestFilePickerPopups:
    """Screenshots of deterministic file chooser popups used by config backup flows."""

    @pytest.mark.visual_reference(reference_name("pick_file_popup_backup_destination"))
    def test_pick_file_popup_backup_destination(self, kivy_app, update_references, visual_reference_config):
        popup = setup_pick_file_popup()
        popup.open()
        pump_frames(10)
        name = reference_name("pick_file_popup_backup_destination")
        capture_screenshot(kivy_app, name)
        popup.dismiss()
        pump_frames(2)
        save_or_compare_reference(name, visual_reference_config, update_references)
