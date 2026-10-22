"""Opt-in loopback feed; the existing Monitor remains the only amplifier reader."""
import json,secrets,threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
PORT=51981
class Server(ThreadingHTTPServer):
 daemon_threads=True

def start(monitor,port=PORT):
 token=secrets.token_urlsafe(32)
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*args):pass
  def reply(self,code,value):
   data=json.dumps(value,allow_nan=False).encode();self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Content-Length',str(len(data)));self.end_headers()
   try:self.wfile.write(data)
   except (BrokenPipeError,ConnectionResetError):pass
  def allowed(self):return self.headers.get('Host')=='127.0.0.1:'+str(self.server.server_port) and not self.headers.get('Origin')
  def do_GET(self):
   if not self.allowed() or self.path!='/api/v1/telemetry':self.reply(403,{'error':'Local backend access only.'});return
   s=monitor.snapshot()
   if not s['settings'].get('share_dxc'):self.reply(403,{'error':'Enable Share readings and controls with DX Caliber in OM Power Control.'});return
   live=s.get('connection')=='Connected' and s.get('age_seconds',999)<=3
   state='live' if live else 'stale' if s.get('connection')=='Stale' else 'disconnected'
   # No station address, callsign, raw packets or connection history leave the app.
   names=('connection','status','age_seconds','forward','reflected','swr','input','plate_a','gain_db','screen_ma','frequency_khz','temperature_c','transmitting','countdown','control')
   om={k:s.get(k) for k in names};om['settings']={'model':s['settings'].get('model','OM-3501A')}
   self.reply(200,{'schema_version':1,'model':'OM Power Control','status':state,'age_seconds':s.get('age_seconds'),'om':om,'control_token':token})
  def do_POST(self):
   if not self.allowed() or self.path!='/api/v1/control' or not secrets.compare_digest(self.headers.get('X-OM-Feed-Token',''),token):self.reply(403,{'error':'Invalid local session.'});return
   if not monitor.snapshot()['settings'].get('share_dxc'):self.reply(403,{'error':'DX Caliber sharing is disabled.'});return
   try:
    size=int(self.headers.get('Content-Length','0'))
    if not 0<size<=1024:raise ValueError('Invalid control request size.')
    value=json.loads(self.rfile.read(size))
    if not isinstance(value,dict) or value.get('action') not in ('toggle','on','off'):raise ValueError('Choose an amplifier control.')
    monitor.command(value['action'],value.get('id'),value.get('expected_mode'),source='DXC')
   except (ValueError,TypeError,AttributeError) as exc:self.reply(409,{'error':str(exc)});return
   self.reply(200,{'queued':True})
 server=Server(('127.0.0.1',port),Handler)
 threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.2},daemon=True,name='DX Caliber OM feed').start()
 return server
