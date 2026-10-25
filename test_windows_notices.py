"""Offline regressions for omission/drift checks in the release notice audit."""
import hashlib
import json
import runpy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

CHECK = runpy.run_path(str(Path(__file__).parent / 'scripts/check-windows-notices.py'))['check']


class NoticeAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.package = Path(self.temp.name)
        self.notices = self.package / '_internal/ThirdPartyNotices'
        (self.notices / 'windows').mkdir(parents=True)
        (self.notices / 'LICENSE').write_bytes(b'upstream notice')
        self.inventory = {'files': {'LICENSE': hashlib.sha256(b'upstream notice').hexdigest()},
                          'components': [], 'binaries': {}}
        self.toc = self.package / 'PYZ.toc'
        self.toc.write_text(repr(('PYZ', [('json', 'stdlib', 'PYMODULE')])) )
        self.save()

    def save(self):
        (self.notices / 'windows/inventory.json').write_text(json.dumps(self.inventory))

    def test_complete_inventory_passes(self):
        CHECK(self.package, self.toc)

    def test_git_line_ending_conversion_preserves_notice_check(self):
        self.inventory['files']['LICENSE'] = hashlib.sha256(b'upstream\r\nnotice\r\n').hexdigest()
        self.save()
        (self.notices / 'LICENSE').write_bytes(b'upstream\nnotice\n')
        CHECK(self.package, self.toc)
        self.inventory['files']['LICENSE'] = hashlib.sha256(b'upstream\nnotice\n').hexdigest()
        self.save()
        (self.notices / 'LICENSE').write_bytes(b'upstream\r\nnotice\r\n')
        CHECK(self.package, self.toc)
        (self.notices / 'LICENSE').write_bytes(b'upstream\r\nnotice\n')
        CHECK(self.package, self.toc)

    def test_missing_or_changed_notice_fails(self):
        (self.notices / 'LICENSE').write_bytes(b'changed')
        with self.assertRaisesRegex(RuntimeError, 'Missing or changed notice'):
            CHECK(self.package, self.toc)
        (self.notices / 'LICENSE').unlink()
        with self.assertRaisesRegex(RuntimeError, 'Missing or changed notice'):
            CHECK(self.package, self.toc)

    def test_unmapped_frozen_dependency_fails(self):
        self.toc.write_text(repr(('PYZ', [('unreviewed_dependency', 'wheel', 'PYMODULE')])) )
        with self.assertRaisesRegex(RuntimeError, 'no notice mapping'):
            CHECK(self.package, self.toc)

    def test_added_or_modified_binary_fails(self):
        binary = self.package / '_internal/new.dll'
        binary.write_bytes(b'original')
        with self.assertRaisesRegex(RuntimeError, 'binary list changed'):
            CHECK(self.package, self.toc)
        self.inventory['components'] = [{'component': 'reviewed', 'version': '1'}]
        self.inventory['binaries']['new.dll'] = {'component': 'reviewed', 'sha256': hashlib.sha256(b'original').hexdigest()}
        self.save()
        binary.write_bytes(b'changed')
        with self.assertRaisesRegex(RuntimeError, 'binary changed'):
            CHECK(self.package, self.toc)

    def test_dependency_version_drift_fails(self):
        self.inventory['components'] = [{'component': 'reviewed', 'version': '1'}]
        self.save()
        with patch('importlib.metadata.version', return_value='2'):
            with self.assertRaisesRegex(RuntimeError, 'Dependency version changed'):
                CHECK(self.package, self.toc)
