"""Local demo launch; capability is passed in the browser fragment, never logged."""
import os
import subprocess
import sys
import time
import urllib.request
import webbrowser
from app.config import Settings

settings=Settings()
if not settings.demo_mode or settings.runtime_dir.name.lower()!='demo':raise SystemExit('Launcher requires the isolated demo runtime')
proc=subprocess.Popen([sys.executable,'-m','app'],env=os.environ.copy())
try:
    for attempt in range(60):
        if proc.poll() is not None:raise SystemExit('Application failed to start')
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{settings.port}/api/v1/readyz',timeout=1) as response:
                if response.status==200:break
        except Exception:time.sleep(.5)
    else:raise SystemExit('Application did not become ready')
    capability=(settings.runtime_dir/'demo-operator.token').read_text(encoding='utf-8').strip()
    webbrowser.open(f'http://127.0.0.1:{settings.port}/#bootstrap={capability}')
    print(f'ReportFix ready at http://127.0.0.1:{settings.port}; press Ctrl+C to stop.')
    proc.wait()
except KeyboardInterrupt:pass
finally:
    proc.terminate()
    try:proc.wait(timeout=5)
    except subprocess.TimeoutExpired:proc.kill();proc.wait()
