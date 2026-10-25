"""Offline acceptance checks for required WACK results, independent of exit code."""
import runpy
import tempfile
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET

CHECK = runpy.run_path(str(Path(__file__).parent / 'scripts/check-wack-report.py'))['check']


class WackReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'report.xml'
        self.root = ET.fromstring('''<REPORT OVERALL_RESULT="PASS" PARTIAL_RUN="FALSE">
          <REQUIREMENTS><REQUIREMENT><TEST NAME="DPIAwarenessValidation" OPTIONAL="FALSE">
          <RESULT>PASS</RESULT></TEST><TEST NAME="Blocked executables" OPTIONAL="TRUE">
          <RESULT>FAIL</RESULT></TEST></REQUIREMENT></REQUIREMENTS></REPORT>''')

    def check(self):
        ET.ElementTree(self.root).write(self.path)
        return CHECK(self.path)

    def test_complete_required_pass_retains_optional_finding(self):
        result = self.check()
        self.assertTrue(result['passed'])
        self.assertEqual(result['optional_findings'][0]['name'], 'Blocked executables')

    def test_required_dpi_warning_is_rejected_even_with_overall_pass(self):
        self.root.find('.//RESULT').text = 'WARNING'
        self.assertFalse(self.check()['passed'])

    def test_overall_warning_is_rejected(self):
        self.root.set('OVERALL_RESULT', 'WARNING')
        self.assertFalse(self.check()['passed'])

    def test_partial_run_is_rejected(self):
        self.root.set('PARTIAL_RUN', 'TRUE')
        self.assertFalse(self.check()['passed'])

    def test_missing_dpi_test_is_rejected(self):
        self.root.find('.//TEST').set('NAME', 'Other test')
        self.assertFalse(self.check()['passed'])

    def test_other_required_failure_is_rejected(self):
        self.root.findall('.//TEST')[1].set('OPTIONAL', 'FALSE')
        self.assertFalse(self.check()['passed'])

    def test_unknown_result_is_rejected(self):
        self.root.findall('.//RESULT')[1].text = 'NOT RUN'
        self.assertFalse(self.check()['passed'])

    def test_missing_completeness_is_rejected(self):
        del self.root.attrib['PARTIAL_RUN']
        self.assertFalse(self.check()['passed'])
