import json,os,re,tempfile
from pathlib import Path
DEFAULTS={'host':'','port':10001,'auto_connect':False,'callsign':'','model':'OM-3501A'}
def location():return Path(os.environ.get('OM_SETTINGS_PATH',str(Path.home()/'Library/Application Support/OM3501A Control/settings.json')))
def validate(value):
 if not isinstance(value,dict):raise ValueError('Invalid connection settings')
 host=str(value.get('host','')).strip();callsign=str(value.get('callsign','')).strip().upper()
 if host and not re.fullmatch(r'[a-zA-Z0-9.\-]{1,253}',host):raise ValueError('Enter a valid host address')
 port=value.get('port')
 if isinstance(port,bool) or not isinstance(port,int) or not 1<=port<=65535:raise ValueError('Port must be between 1 and 65535')
 if not host and value.get('auto_connect') is True:raise ValueError('Set the amplifier address before enabling auto-connect')
 model=str(value.get('model','OM-3501A')).strip().upper()
 if not model or len(model)>40 or any(ord(c)<32 for c in model):raise ValueError('Enter an amplifier model (up to 40 characters)')
 if len(callsign)>24:raise ValueError('Callsign is too long')
 return {'host':host,'port':port,'auto_connect':value.get('auto_connect') is True,'callsign':callsign,'model':model}
def load():
 try:return validate(json.loads(location().read_text()))
 except (OSError,ValueError,TypeError):return dict(DEFAULTS)
def save(value):
 value=validate(value);p=location();p.parent.mkdir(parents=True,exist_ok=True)
 fd,name=tempfile.mkstemp(dir=p.parent,prefix='.settings-')
 try:
  with os.fdopen(fd,'w') as f:json.dump(value,f)
  os.replace(name,p)
 finally:
  if os.path.exists(name):os.unlink(name)
 return value
