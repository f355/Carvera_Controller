"""Visual regression tests for common utility popups."""

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


def setup_confirm_popup(app):
    popup = app.root.confirm_popup
    popup.lb_title.text = "Delete File or Dir"
    popup.lb_content.text = "Confirm to delete 2 selected files or dirs?\n\nprobe-grid-test.nc\nsurfacing-pass.cnc"
    popup.confirm = lambda: None
    popup.cancel = None
    return popup


def setup_message_popup(app):
    popup = app.root.message_popup
    popup.lb_content.text = "Settings applied, need machine reset to take effect!"
    popup.btn_ok.disabled = False
    return popup


def setup_progress_popup(app):
    popup = app.root.progress_popup
    popup.progress_text = "Uploading surfacing-pass.cnc..."
    popup.progress_value = 64
    popup.cancel = lambda: None
    popup.btn_cancel.disabled = False
    return popup


def setup_reconnection_popup(app):
    popup = app.root.reconnection_popup
    popup.start_countdown(
        max_attempts=5,
        wait_time=10,
        reconnect_callback=lambda: None,
        cancel_callback=lambda: None,
    )
    popup.countdown = 7
    popup.current_attempt = 1
    popup.update_display()
    return popup


def setup_input_popup(app):
    popup = app.root.input_popup
    popup.lb_title.text = "New Folder"
    popup.txt_content.text = "probe-routines"
    popup.confirm = lambda: True
    return popup


def setup_manual_wifi_popup(app):
    popup = app.root.manual_wifi_popup
    popup.lb_title1.text = "Wi-Fi SSID"
    popup.lb_title2.text = "Password"
    popup.txt_content1.text = "Carvera-Shop"
    popup.txt_content2.text = "**********"
    popup.confirm = lambda: True
    return popup


def setup_unlock_popup(app):
    popup = app.root.unlock_popup
    popup.lb_title.text = "Machine Is Halted"
    popup.lb_content.text = "Choose unlock option:"
    popup.unlock_stay = lambda: None
    popup.unlock_safe_z = lambda: None
    return popup


class TestUtilityPopups:
    """Screenshots of common modal panels opened from the toolbar and menus."""

    @pytest.mark.visual_reference(reference_name("language_popup"))
    def test_language_popup(self, kivy_app, update_references, visual_reference_config):
        capture_popup_state(
            kivy_app,
            kivy_app.root.language_popup,
            reference_name("language_popup"),
            update_references,
            visual_reference_config,
        )

    @pytest.mark.visual_reference(reference_name("pairing_popup_ready"))
    def test_pairing_popup_ready(self, kivy_app, update_references, visual_reference_config):
        kivy_app.root.pairing_popup.pairing = False
        kivy_app.root.pairing_popup.countdown = 0
        kivy_app.root.pairing_popup.pairing_note = "Press the Wireless Probe until the green LED blinks quickly."
        capture_popup_state(
            kivy_app,
            kivy_app.root.pairing_popup,
            reference_name("pairing_popup_ready"),
            update_references,
            visual_reference_config,
        )

    @pytest.mark.visual_reference(reference_name("diagnose_popup_idle"))
    def test_diagnose_popup_idle(self, kivy_app, connected_idle_state, update_references, visual_reference_config):
        apply_machine_state(kivy_app)
        capture_popup_state(
            kivy_app,
            kivy_app.root.diagnose_popup,
            reference_name("diagnose_popup_idle"),
            update_references,
            visual_reference_config,
        )


class TestGenericWorkflowPopups:
    """Screenshots of generic modal controls used by many workflows."""

    @pytest.mark.visual_reference(reference_name("confirm_popup_delete_selection"))
    def test_confirm_popup_delete_selection(self, kivy_app, update_references, visual_reference_config):
        capture_popup_state(
            kivy_app,
            setup_confirm_popup(kivy_app),
            reference_name("confirm_popup_delete_selection"),
            update_references,
            visual_reference_config,
        )

    @pytest.mark.visual_reference(reference_name("message_popup_settings_applied"))
    def test_message_popup_settings_applied(self, kivy_app, update_references, visual_reference_config):
        capture_popup_state(
            kivy_app,
            setup_message_popup(kivy_app),
            reference_name("message_popup_settings_applied"),
            update_references,
            visual_reference_config,
        )

    @pytest.mark.visual_reference(reference_name("progress_popup_uploading"))
    def test_progress_popup_uploading(self, kivy_app, update_references, visual_reference_config):
        capture_popup_state(
            kivy_app,
            setup_progress_popup(kivy_app),
            reference_name("progress_popup_uploading"),
            update_references,
            visual_reference_config,
        )

    @pytest.mark.visual_reference(reference_name("reconnection_popup_countdown"))
    def test_reconnection_popup_countdown(self, kivy_app, update_references, visual_reference_config):
        capture_popup_state(
            kivy_app,
            setup_reconnection_popup(kivy_app),
            reference_name("reconnection_popup_countdown"),
            update_references,
            visual_reference_config,
        )

    @pytest.mark.visual_reference(reference_name("input_popup_new_folder"))
    def test_input_popup_new_folder(self, kivy_app, update_references, visual_reference_config):
        capture_popup_state(
            kivy_app,
            setup_input_popup(kivy_app),
            reference_name("input_popup_new_folder"),
            update_references,
            visual_reference_config,
        )

    @pytest.mark.visual_reference(reference_name("manual_wifi_popup_credentials"))
    def test_manual_wifi_popup_credentials(self, kivy_app, update_references, visual_reference_config):
        capture_popup_state(
            kivy_app,
            setup_manual_wifi_popup(kivy_app),
            reference_name("manual_wifi_popup_credentials"),
            update_references,
            visual_reference_config,
        )

    @pytest.mark.visual_reference(reference_name("unlock_popup_options"))
    def test_unlock_popup_options(self, kivy_app, update_references, visual_reference_config):
        capture_popup_state(
            kivy_app,
            setup_unlock_popup(kivy_app),
            reference_name("unlock_popup_options"),
            update_references,
            visual_reference_config,
        )
