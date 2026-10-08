import argparse,json,mimetypes,uuid,threading
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.parse import urlparse
from collections import OrderedDict
from backend.engine import Engine,make_csv,report
from backend.llm import explain

ROOT=Path(__file__).resolve().parent
def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--port',type=int,default=8787); parser.add_argument('--host',default='127.0.0.1'); args=parser.parse_args()
    engine=Engine(); cache=OrderedDict(); lock=threading.Lock()
    class Handler(BaseHTTPRequestHandler):
        def send(self,code,data,mime='application/json; charset=utf-8'):
            raw=data.encode() if isinstance(data,str) else data
            self.send_response(code);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(raw)));self.send_header('X-Content-Type-Options','nosniff');self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(raw)
        def json(self,code,data):self.send(code,json.dumps(data,ensure_ascii=False))
        def do_GET(self):
            path=urlparse(self.path).path
            if path=='/api/health':return self.json(200,{'status':'ok','version':'1.0.0'})
            if path=='/api/demo':return self.send(200,make_csv(),'text/csv; charset=utf-8')
            if path.startswith('/api/report/'):
                with lock:r=cache.get(path.split('/')[-1])
                return self.send(200,report(r),'text/markdown; charset=utf-8') if r else self.json(404,{'error':'报告不存在或已过期，请重新分析'})
            files={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}
            if path not in files:return self.json(404,{'error':'页面不存在'})
            f=ROOT/'frontend'/files[path];return self.send(200,f.read_bytes(),mimetypes.guess_type(str(f))[0]+'; charset=utf-8')
        def do_POST(self):
            origin=self.headers.get('Origin')
            if origin and urlparse(origin).netloc!=self.headers.get('Host'):return self.json(403,{'error':'不接受跨站请求'})
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=2_200_000:raise ValueError('请求体大小不合法')
                data=json.loads(self.rfile.read(size))
                if not isinstance(data,dict):raise ValueError('JSON需为对象')
                if self.path=='/api/analyze':
                    result=engine.analyze(data.get('csv_text')); rid=str(uuid.uuid4());result['id']=rid
                    with lock:
                        cache[rid]=result
                        while len(cache)>8:cache.popitem(last=False)
                    return self.json(200,result)
                if self.path=='/api/chat':
                    with lock:r=cache.get(data.get('id'))
                    if not r:return self.json(404,{'error':'报告不存在或已过期，请重新分析'})
                    return self.json(200,explain(r,data.get('question')))
                return self.json(404,{'error':'接口不存在'})
            except (ValueError,TypeError,UnicodeDecodeError) as e:return self.json(400,{'error':str(e)})
            except Exception:return self.json(500,{'error':'处理失败，请检查服务器日志或重试'})
        def log_message(self,*a):pass
    print(f'WirelessCare ready: http://{args.host}:{args.port}',flush=True)
    ThreadingHTTPServer((args.host,args.port),Handler).serve_forever()
if __name__=='__main__':main()
