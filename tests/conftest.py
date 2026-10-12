"""A loopback-only Decisions stand-in. All tests are offline."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import socket
import threading
import time
import pytest

@pytest.fixture(autouse=True)
def block_remote_network(monkeypatch):
    original=socket.socket.connect
    def connect(sock,address):
        if isinstance(address,tuple) and address[0] not in ('127.0.0.1','::1','localhost'):
            raise AssertionError('Tests must never connect to a remote endpoint')
        return original(sock,address)
    monkeypatch.setattr(socket.socket,'connect',connect)

@pytest.fixture
def stub():
    config={'delay':0,'mode':'choice','requests':[],'headers':[],'status':200,'tokens':123}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_POST(self):
            body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            config['requests'].append(body); config['headers'].append(dict(self.headers))
            time.sleep(config['delay'])
            if 'questions' not in body:                      # Responses API shape (structured output)
                props = body['text']['format']['schema']['properties']
                out = {k: v['enum'][0] for k, v in props.items()}
                if config['mode'] == 'invalid': out = {k: 'OUTSIDE' for k in props}
                response = {'status': 'completed', 'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(out)}]}],
                            'usage': {'input_tokens': config['tokens'], 'output_tokens': 7, 'output_tokens_details': {'reasoning_tokens': 0}}}
                self.send_response(config['status']); self.send_header('Content-Type','application/json'); self.end_headers()
                self.wfile.write(json.dumps(response).encode()); return
            answers=[]
            for q in body['questions']:
                choices=q['choices']; n=len(choices)
                if config['mode']=='refusal': answer={'type':'refusal','name':q['name']}
                else:
                    answer={'type':'choice','name':q['name'],'choice':choices[0]['value'],'confidence':.75,
                            'probabilities':[{'value':c['value'],'probability':1/n} for c in choices]}
                    if config['mode']=='invalid': answer['choice']='OUTSIDE_OPTIONS'
                answers.append(answer)
            response={'model':'gpt-6-luna','answers':answers,'usage':{'input_tokens':config['tokens'],
                     'input_tokens_details':{'cached_tokens':0,'cache_write_tokens':0},'output_tokens':0,
                     'output_tokens_details':{'reasoning_tokens':0},'total_tokens':config['tokens']}}
            self.send_response(config['status']); self.send_header('Content-Type','application/json'); self.send_header('x-request-id','stub-request'); self.end_headers()
            try: self.wfile.write(json.dumps(response).encode())
            except (BrokenPipeError,ConnectionResetError): pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    config['url']=f'http://127.0.0.1:{server.server_port}/v1/decisions'
    yield config
    server.shutdown(); server.server_close(); thread.join()
