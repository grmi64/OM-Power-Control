"""Offline tests for explicit access handoff; no amplifier socket is opened."""
import os
import contextlib
import io
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, MagicMock, patch
import windows_access
import windows_app


class AccessModeTests(unittest.TestCase):
    state = {'connection': 'Disconnected', 'control': {'pending': None}}

    def request(self, **changes):
        return {'mode': 'read-only', 'host': '192.0.2.1', 'port': 10001,
                'confirmed': True, **changes}

    def test_hardware_modes_always_start_disconnected(self):
        for mode, flag in [('read-only', '--read-only'), ('hardware', '--hardware')]:
            args = windows_access.prepare_launch(self.request(mode=mode), self.state)
            self.assertEqual(args, [flag, '--start-disconnected', '--host=192.0.2.1', '--amp-port', '10001'])

    def test_option_like_and_malformed_hosts_do_not_arm_handoff(self):
        bridge = windows_app.DisplayBridge(Path('unused'), {})
        bridge._access_allowed = True
        bridge._monitor = Mock(snapshot=Mock(return_value=self.state))
        for host in ['--hardware', '-amp.local', 'amp-.local', '.', 'amp..local',
                     'amp.local..', 'a' * 64 + '.local', '999.0.2.1']:
            with self.subTest(host=host), self.assertRaises(ValueError):
                bridge.request_access_mode(self.request(host=host))
            self.assertIsNone(getattr(bridge, '_access_args', None))

    def test_valid_endpoint_forms_remain_available(self):
        for host in ['192.0.2.1', 'om-3501a', 'amp.local', 'amp.local.', 'localhost']:
            with self.subTest(host=host):
                args = windows_access.prepare_launch(self.request(host=host), self.state)
                self.assertIn('--host=' + host, args)

    def test_simulation_does_not_forward_endpoint(self):
        self.assertEqual(windows_access.prepare_launch({'mode': 'simulation'}, self.state), ['--simulate', '--start-disconnected'])

    def test_active_or_incomplete_connection_is_rejected(self):
        for connection in ['Connected', 'Stale', 'Connecting', 'Disconnecting', 'Waiting for amplifier data']:
            with self.assertRaises(ValueError):
                windows_access.prepare_launch(self.request(), {**self.state, 'connection': connection})
        for state in [{**self.state, 'control': {'pending': {'action': 'toggle'}}}, {**self.state, 'transmitting': True}]:
            with self.assertRaises(ValueError):
                windows_access.prepare_launch(self.request(), state)

    def test_explicit_hardware_confirmation_required(self):
        for confirmed in [False, None, 'true', 1]:
            with self.assertRaises(ValueError):
                windows_access.prepare_launch(self.request(confirmed=confirmed), self.state)

    def test_invalid_modes_and_endpoints_are_rejected(self):
        for value in [None, [], {}, self.request(mode='--hardware'), self.request(host='simulation'), self.request(host=''), self.request(host='host & cmd'), self.request(port=True), self.request(port=0), self.request(port=65536)]:
            with self.assertRaises(ValueError):
                windows_access.prepare_launch(value, self.state)

    def test_restricted_bridge_cannot_upgrade_mode(self):
        bridge = windows_app.DisplayBridge(Path('unused'), {})
        bridge._monitor = Mock()
        with self.assertRaises(ValueError):
            bridge.request_access_mode(self.request())
        bridge._monitor.snapshot.assert_not_called()

    def test_bridge_rechecks_state_before_requesting_close(self):
        bridge = windows_app.DisplayBridge(Path('unused'), {})
        bridge._access_allowed = True
        bridge._monitor = Mock()
        bridge._close_for_access = Mock()
        bridge._monitor.snapshot.return_value = {'connection': 'Connected'}
        with self.assertRaises(ValueError):
            bridge.request_access_mode(self.request())
        bridge._close_for_access.assert_not_called()
        bridge._monitor.snapshot.return_value = self.state
        self.assertEqual(bridge.request_access_mode(self.request()), {'reopening': True})
        bridge._close_for_access.assert_not_called()
        with self.assertRaises(ValueError):
            bridge.request_access_mode(self.request())

    def test_frozen_relaunch_uses_only_own_executable_and_no_shell(self):
        with patch.object(sys, 'frozen', True, create=True), patch('windows_access.subprocess.Popen') as spawn:
            windows_access.launch_replacement(['--simulate', '--start-disconnected'])
        args, kwargs = spawn.call_args
        self.assertEqual(args[0], [sys.executable, '--simulate', '--start-disconnected'])
        self.assertFalse(kwargs['shell'])
        self.assertEqual(kwargs['env']['PYINSTALLER_RESET_ENVIRONMENT'], '1')

    def test_mode_handoff_restores_simulation_settings_environment(self):
        def run(_argv):
            os.environ['OM_SETTINGS_PATH'] = 'simulation-settings.json'
            return ['--simulate', '--start-disconnected']
        def launch(_args):
            self.assertNotIn('OM_SETTINGS_PATH', os.environ)
        with patch.dict(os.environ, {}, clear=True), patch('windows_app._run_once', side_effect=run), patch('windows_app.launch_replacement', side_effect=launch) as spawn:
            self.assertEqual(windows_app.main([]), 0)
            spawn.assert_called_once()

    def test_original_settings_override_survives_error(self):
        def fail(_argv):
            os.environ['OM_SETTINGS_PATH'] = 'temporary'
            raise RuntimeError('test')
        with patch.dict(os.environ, {'OM_SETTINGS_PATH': 'isolated-test'}), patch('windows_app._run_once', side_effect=fail):
            with self.assertRaises(RuntimeError):
                windows_app.main([])
            self.assertEqual(os.environ['OM_SETTINGS_PATH'], 'isolated-test')

    def test_access_smoke_cannot_relaunch_hardware(self):
        bridge = windows_app.DisplayBridge(Path('unused'), {})
        bridge._access_allowed = True
        bridge._access_smoke_only = True
        bridge._monitor = Mock(snapshot=Mock(return_value=self.state))
        bridge._close_for_access = Mock()
        with self.assertRaises(ValueError):
            bridge.request_access_mode(self.request(mode='hardware'))
        bridge._close_for_access.assert_not_called()

    def test_access_smoke_rejects_all_hardware_launch_flags_before_startup(self):
        with patch('windows_app.configure_process_dpi') as startup, contextlib.redirect_stderr(io.StringIO()):
            for flag in ['--hardware', '--read-only', '--mode-test', '--power-test', '--readiness-test', '--tune-test']:
                with self.assertRaises(SystemExit) as exc:
                    windows_app.main(['--access-smoke-test', flag])
                self.assertEqual(exc.exception.code, 2)
            startup.assert_not_called()

    def test_disconnected_start_overrides_endpoint_and_saved_autoconnect(self):
        with tempfile.TemporaryDirectory() as folder:
            for mode in ['--read-only', '--hardware', '--simulate']:
                monitor = Mock(settings={**windows_access.settings.DEFAULTS, 'host': '192.0.2.1', 'auto_connect': True}, thread=None)
                server = Mock(html='<main></main>', server_port=12345)
                native = types.SimpleNamespace(__file__=__file__, settings={},
                    create_window=Mock(return_value=MagicMock()), start=Mock())
                argv = [mode, '--start-disconnected']
                if mode != '--simulate':
                    argv = windows_access.prepare_launch(self.request(
                        mode='hardware' if mode == '--hardware' else 'read-only',
                        host='om-3501a.local', port=10002), self.state)
                with patch('dxc_feed.start', return_value=None), patch.dict(sys.modules, {'webview': native}), patch('windows_app.configure_process_dpi'), patch('windows_app.ensure_webview2_runtime'), patch('windows_app.settings.data_directory', return_value=Path(folder)), patch('windows_app.logging.basicConfig'), patch('windows_app.InstanceLock'), patch('windows_app.Monitor', return_value=monitor), patch('windows_app.create_server', return_value=server), patch('windows_app.threading.Thread'), patch('windows_app.sys.platform', 'win32'):
                    self.assertEqual(windows_app.main(argv), 0)
                monitor.connect.assert_not_called()
                if mode != '--simulate':
                    self.assertEqual(monitor.settings['host'], 'om-3501a.local')
                    self.assertEqual(monitor.settings['port'], 10002)
