"""Render local access-mode assets in WebView2, without an app backend or hardware."""
import json
from pathlib import Path
import re
import sys
import threading
import time
import uuid


def main():
    if sys.platform != 'win32':
        raise RuntimeError('This rendering check requires Windows and WebView2')
    import webview

    project = Path(__file__).resolve().parents[1]
    output = project / '.tmp' / ('access-rendering-' + uuid.uuid4().hex)
    output.mkdir(parents=True)
    # Use the production shared styles and Windows panel/script. Deliberately
    # omit the app backend and main UI script: no fetch or amplifier exists here.
    styles = ''.join(re.findall(r'<style>(.*?)</style>',
        (project / 'live.html').read_text(encoding='utf-8'), re.S))
    panel = (project / 'windows_access.html').read_text(encoding='utf-8').split('<script>')[0]
    script = (project / 'windows_access.js').read_text(encoding='utf-8')
    html = ('<html><head><style>' + styles + '</style></head><body>'
        '<p>OFFLINE SIMULATION rendering check</p>' + panel + '<script>'
        'window.omAccessMode={allowed:false,mode:"simulation",host:"",port:10001};'
        'window.lastState={connection:"Disconnected"};' + script + '</script></body></html>')
    window = webview.create_window('Offline simulation rendering check', html=html,
        width=900, height=790, hidden=True)
    result = {'passed': False, 'backend_started': False, 'cases': []}
    finished = threading.Event()

    def check():
        try:
            if not window.events.loaded.wait(20):
                raise RuntimeError('WebView2 did not load the local test document')
            for compact, width in [(False, 900), (True, 420)]:
                window.resize(width, 790)
                deadline = time.monotonic() + 5
                while bool(window.evaluate_js('window.innerWidth < 600')) != compact:
                    if time.monotonic() > deadline:
                        raise RuntimeError('Test viewport did not resize')
                    time.sleep(.05)
                window.evaluate_js('document.body.classList.toggle("compact",' + json.dumps(compact) + ')')
                for mode in ['simulation', 'read-only', 'hardware', 'simulation']:
                    window.evaluate_js('document.getElementById("accessMode").value=' + json.dumps(mode)
                        + ';document.getElementById("accessMode").onchange()')
                    case = window.evaluate_js('''(()=>{
                        const e=document.getElementById('accessEndpoint'), r=e.getBoundingClientRect();
                        return {hidden:e.hidden,display:getComputedStyle(e).display,
                            width:r.width,height:r.height,children:[...e.querySelectorAll('input')].map(n=>{
                                const b=n.getBoundingClientRect();return {width:b.width,height:b.height};
                            })};})()''')
                    case.update(mode=mode, compact=compact)
                    result['cases'].append(case)
                    if mode == 'simulation':
                        if not case['hidden'] or case['display'] != 'none' or case['width'] != 0 or case['height'] != 0:
                            raise AssertionError('Simulation endpoint fields still render')
                    elif case['hidden'] or case['display'] == 'none' or case['height'] <= 0 or len(case['children']) != 2 or any(
                            child['width'] <= 0 or child['height'] <= 0 for child in case['children']):
                        raise AssertionError('Selected amplifier-mode endpoint fields do not render')
            result['passed'] = True
        except Exception as exc:
            result['error'] = str(exc)
        finally:
            (output / 'report.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
            finished.set()
            window.destroy()

    def timeout():
        if not finished.wait(40):
            result['error'] = 'Rendering check timed out'
            window.destroy()

    threading.Thread(target=timeout, daemon=True).start()
    webview.start(check, gui='edgechromium', private_mode=True, storage_path=str(output / 'WebView2'))
    result['passed'] = bool(result['passed'] and not result.get('error'))
    (output / 'report.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))
    print('Rendering evidence:', output / 'report.json')
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
