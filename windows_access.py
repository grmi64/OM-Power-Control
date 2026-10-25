"""Explicit Windows access-mode handoff; never opens an amplifier connection."""
import subprocess
import sys
import os
import ipaddress
import re
from pathlib import Path
import settings


def prepare_launch(value, state):
    if not isinstance(value, dict) or value.get('mode') not in ('simulation', 'read-only', 'hardware'):
        raise ValueError('Choose simulation, read-only telemetry or hardware controls')
    if state.get('connection') != 'Disconnected' or state.get('control', {}).get('pending') or state.get('transmitting') is True:
        raise ValueError('Disconnect before changing connection mode')
    mode = value['mode']
    if mode != 'simulation' and value.get('confirmed') is not True:
        raise ValueError('Confirm the selected hardware access mode')
    args = [{'simulation': '--simulate', 'read-only': '--read-only', 'hardware': '--hardware'}[mode], '--start-disconnected']
    if mode != 'simulation':
        host = value.get('host', '')
        if not isinstance(host, str) or not host.strip() or host.strip().lower() == 'simulation':
            raise ValueError('Enter the amplifier address for this mode')
        endpoint = settings.validate({**settings.DEFAULTS, 'host': host, 'port': value.get('port')})
        hostname = endpoint['host'][:-1] if endpoint['host'].endswith('.') else endpoint['host']
        labels = hostname.split('.')
        if not all(re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?', label) for label in labels):
            raise ValueError('Enter a valid amplifier IPv4 address or hostname')
        if len(labels) == 4 and all(label.isdigit() for label in labels):
            try:
                ipaddress.IPv4Address(hostname)
            except ipaddress.AddressValueError as exc:
                raise ValueError('Enter a valid amplifier IPv4 address or hostname') from exc
        # Keep the value attached to its option as a second layer of protection
        # against treating endpoint text as a new command-line option.
        args += ['--host=' + endpoint['host'], '--amp-port', str(endpoint['port'])]
    return args


def launch_replacement(args):
    # Structured argv, our own executable only; never invoke a shell/helper.
    command = [sys.executable]
    if not getattr(sys, 'frozen', False):
        command.append(str(Path(__file__).with_name('windows_app.py')))
    subprocess.Popen(command + args, shell=False, close_fds=True,
                     env={**os.environ, 'PYINSTALLER_RESET_ENVIRONMENT': '1'})
