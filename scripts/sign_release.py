"""Sign nested Mach-O code before the enclosing application."""
import os,subprocess,sys
from pathlib import Path
app=Path(sys.argv[1]).resolve()
identity=os.environ['OM_SIGN_IDENTITY']
magic={bytes.fromhex(x) for x in ('cffaedfe','feedfacf','cefaedfe','feedface','cafebabe','bebafeca')}
for p in sorted(app.rglob('*'),key=lambda p:len(p.parts),reverse=True):
 if p.is_symlink() or not p.is_file():continue
 with p.open('rb') as f:header=f.read(4)
 if header in magic:subprocess.run(['codesign','--force','--options','runtime','--timestamp','--sign',identity,str(p)],check=True)
subprocess.run(['codesign','--force','--options','runtime','--timestamp','--sign',identity,str(app)],check=True)
subprocess.run(['codesign','--verify','--deep','--strict','--verbose=2',str(app)],check=True)
