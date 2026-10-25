"""Offline checks of the frozen Windows bundle's notice inventory."""
import argparse
import ast
import hashlib
import importlib.metadata
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]


def notice_matches(path, expected):
    if not path.is_file():
        return False
    data = path.read_bytes()
    lf = data.replace(b'\r\n', b'\n')
    # Git may translate text on checkout. Preserve exact text while accepting
    # its LF/CRLF representations; executable binary hashes stay byte-exact.
    return expected in {hashlib.sha256(value).hexdigest()
                        for value in (data, lf, lf.replace(b'\n', b'\r\n'))}


def check(package, toc):
    root = package / '_internal' / 'ThirdPartyNotices'
    inventory = json.loads((root / 'windows' / 'inventory.json').read_text())
    for relative, expected in inventory['files'].items():
        path = root / relative
        if not notice_matches(path, expected):
            raise RuntimeError(f'Missing or changed notice/source: {relative}')
    # Use PyInstaller's actual module inventory, not only pip's installed list.
    modules = ast.literal_eval(toc.read_text())[1]
    components = {item['component'] for item in inventory['components']}
    for item in inventory['components']:
        try:
            installed = importlib.metadata.version(item['component'])
        except importlib.metadata.PackageNotFoundError:
            continue
        if installed != item['version']:
            raise RuntimeError(f"Dependency version changed; review notices: {item['component']}")
    native = {p.relative_to(package / '_internal').as_posix(): p
              for p in (package / '_internal').rglob('*')
              if p.is_file() and p.suffix.lower() in ('.dll', '.pyd', '.jar')}
    if native.keys() != inventory['binaries'].keys():
        raise RuntimeError('Bundled binary list changed; review dependency inventory')
    for relative, item in inventory['binaries'].items():
        if item['component'] not in components or hashlib.sha256(native[relative].read_bytes()).hexdigest() != item['sha256']:
            raise RuntimeError(f'Bundled binary changed; review notices/provenance: {relative}')
    aliases = {'webview': 'pywebview', 'clr': 'pythonnet', '_cffi_backend': 'cffi',
               'win32ctypes': 'pywin32-ctypes', 'ordlookup': 'pefile',
               '_distutils_hack': 'setuptools', 'PyInstaller': 'PyInstaller'}
    for name, *_ in modules:
        top = name.split('.')[0]
        if top in sys.stdlib_module_names or (PROJECT / (top + '.py')).is_file():
            continue
        if aliases.get(top, top) not in components:
            raise RuntimeError(f'Frozen module has no notice mapping: {name}')
    print(f"Windows notice audit passed: {len(inventory['files'])} pinned notice/source files; frozen module roots mapped.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, default=PROJECT / 'dist/windows/OM Power Control')
    parser.add_argument('--toc', type=Path, default=PROJECT / 'build/windows/OM Power Control/PYZ-00.toc')
    args = parser.parse_args()
    check(args.package, args.toc)
