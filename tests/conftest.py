"""Shared test fixtures for unit and integration tests.

Provides machine-state fixtures that set ``CNC.vars`` to simulate
different machine states without needing real hardware.

The integration-test autouse ``reset_app_state`` fixture in
``tests/integration/conftest.py`` restores ``CNC.vars`` (and the rest
of the app state surface) to the as-booted disconnected baseline
after every test. These fixtures are therefore *deltas on top of a
clean baseline* — they only set the keys that differ from the
disconnected default and declare no teardown.
"""

import pytest


@pytest.fixture
def connected_idle_state():
    """Simulate a connected, idle Carvera machine.

    Layered on top of the disconnected baseline restored by the
    autouse reset fixture; no teardown.
    """
    from carveracontroller.CNC import CNC

    CNC.vars["state"] = "Idle"
    CNC.vars["color"] = (52 / 255, 152 / 255, 219 / 255, 1)
    # Positions
    CNC.vars["wx"] = 0.0
    CNC.vars["wy"] = 0.0
    CNC.vars["wz"] = 0.0
    CNC.vars["wa"] = 0.0
    CNC.vars["mx"] = -180.0
    CNC.vars["my"] = -120.0
    CNC.vars["mz"] = -5.0
    CNC.vars["ma"] = 0.0
    # Tool
    CNC.vars["tool"] = 1
    CNC.vars["tlo"] = 35.0
    CNC.vars["target_tool"] = -1
    CNC.vars["target_collet_type"] = 0
    # Feed and spindle
    CNC.vars["curfeed"] = 0.0
    CNC.vars["curspindle"] = 0.0
    CNC.vars["tarfeed"] = 0.0
    CNC.vars["tarspindle"] = 0.0
    CNC.vars["spindletemp"] = 25.0
    CNC.vars["OvFeed"] = 100
    CNC.vars["OvSpindle"] = 100
    CNC.vars["OvRapid"] = 100
    # Laser
    CNC.vars["lasermode"] = 0
    CNC.vars["laserstate"] = 0
    CNC.vars["lasertesting"] = 0
    CNC.vars["laserpower"] = 0.0
    CNC.vars["laserscale"] = 0.0
    # Machine state
    CNC.vars["atc_state"] = 0
    CNC.vars["vacuummode"] = 0
    CNC.vars["wpvoltage"] = 3.3
    CNC.vars["active_coord_system"] = 0
    CNC.vars["rotation_angle"] = 0
    CNC.vars["max_delta"] = 0.0
    # Firmware
    CNC.vars["version"] = "1.5.0"
    CNC.vars["running"] = False
    # Playback
    CNC.vars["playedlines"] = 0
    CNC.vars["playedpercent"] = 0
    CNC.vars["playedseconds"] = 0
    CNC.vars["is_playing"] = 0
    # Alarm
    CNC.vars["halt_reason"] = 1
    CNC.vars["alarm_message"] = ""
    # Hardware feature flags (set when machine reports its model)
    CNC.vars["FuncSetting"] = 0  # bit 0: 4-axis, bit 2: ATC


@pytest.fixture
def alarm_state(connected_idle_state):
    """Machine in alarm state (e.g., limit switch hit).

    Delta on top of ``connected_idle_state``; no teardown.
    """
    from carveracontroller.CNC import CNC

    CNC.vars["state"] = "Alarm"
    CNC.vars["color"] = (231 / 255, 76 / 255, 60 / 255, 1)
    CNC.vars["halt_reason"] = 2
    CNC.vars["alarm_message"] = "Hard limit triggered"


@pytest.fixture
def mock_controller():
    """A Controller mock for unit tests that doesn't touch hardware."""
    from unittest.mock import MagicMock
    from carveracontroller.Controller import Controller

    controller = MagicMock(spec=Controller)
    controller.jog_mode = Controller.JOG_MODE_STEP
    controller.is_community_firmware = False
    controller.connection_type = 0
    controller._manual_disconnect = False
    return controller
