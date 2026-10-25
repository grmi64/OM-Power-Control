"""Gate a complete MSIX WACK report, including its required DPI analysis."""
import argparse
from collections import Counter
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def check(path):
    root = ET.parse(path).getroot()
    errors = []
    if root.tag != 'REPORT':
        errors.append('Not a WACK REPORT')
    if root.get('OVERALL_RESULT') != 'PASS':
        errors.append('Overall WACK result is not PASS')
    if root.get('PARTIAL_RUN') != 'FALSE':
        errors.append('Report does not confirm a complete run')
    tests = []
    for test in root.findall('./REQUIREMENTS/REQUIREMENT/TEST'):
        result = (test.findtext('RESULT') or '').strip()
        optional = test.get('OPTIONAL')
        name = test.get('NAME', '(unnamed)')
        tests.append({'name': name, 'result': result, 'optional': optional == 'TRUE'})
        if optional not in ('TRUE', 'FALSE') or result not in ('PASS', 'FAIL', 'WARNING'):
            errors.append(f'{name}: unknown test classification/result')
        elif optional != 'TRUE' and result != 'PASS':
            errors.append(f'{name}: required test result is {result}')
    dpi = [test for test in tests if test['name'] == 'DPIAwarenessValidation']
    if len(dpi) != 1 or dpi[0]['result'] != 'PASS' or dpi[0]['optional']:
        errors.append('Missing or unsuccessful required DPIAwarenessValidation')
    summary = {'passed': not errors, 'overall': root.get('OVERALL_RESULT'),
               'partial_run': root.get('PARTIAL_RUN'), 'counts': dict(Counter(t['result'] for t in tests)),
               'optional_findings': [t for t in tests if t['optional'] and t['result'] != 'PASS'],
               'errors': errors}
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    args = parser.parse_args()
    try:
        result = check(args.report)
    except (OSError, ET.ParseError) as exc:
        result = {'passed': False, 'errors': [str(exc)]}
    print(json.dumps(result, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
