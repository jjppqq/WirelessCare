"""Transport/configuration contract tests. All remote responses here are simulated."""
import io,json,os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend import llm
from backend.engine import Engine,make_csv
class LLMTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.result=Engine().analyze(make_csv())
    def test_sampling_spans_cells(self):
        sample=llm.select_samples(self.result['rows'])
        self.assertLessEqual(len(sample),12)
        self.assertGreaterEqual(len({r['cell_id'] for r in sample}),4)
        self.assertTrue(all(r['diagnosis']!='正常' for r in sample))
    def test_empty_sampling(self):self.assertEqual(llm.select_samples([]),[])
    def test_config_environment_override(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'config.json';f.write_text(json.dumps({'api_key':'local','api_base':'https://a.example/v1','model':'local'}))
            with patch.object(llm,'CONFIG_PATH',f),patch.dict(os.environ,{'WIRELESSCARE_MODEL':'override'},clear=True):
                cfg=llm.configuration();self.assertEqual(cfg['model'],'override');self.assertEqual(cfg['api_key'],'local')
    def test_invalid_config(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'config.json';f.write_text('[]')
            with patch.object(llm,'CONFIG_PATH',f),self.assertRaises(ValueError):llm.configuration()
    def test_endpoint_rejects_secrets_or_http(self):
        for base in ['http://a.example/v1','https://key@a.example/v1','https://a.example/v1?key=secret','https://a.example/v1#x']:
            with self.subTest(base=base),self.assertRaises(ValueError):llm.validate_base(base)
    def test_request_contract(self):
        config={'api_key':'test-only','api_base':'https://a.example/v1','model':'model-test'}
        response=io.BytesIO(json.dumps({'choices':[{'message':{'content':'模拟回答'}}]}).encode())
        with patch.object(llm,'configuration',return_value=config),patch('urllib.request.urlopen',return_value=response) as call:
            ans=llm.explain(self.result,'优先检查什么')
        req=call.call_args.args[0];payload=json.loads(req.data);evidence=json.loads(payload['messages'][1]['content'])['evidence']
        self.assertEqual(req.full_url,'https://a.example/v1/chat/completions')
        self.assertEqual(req.get_header('Authorization'),'Bearer test-only')
        self.assertEqual(payload['model'],'model-test');self.assertEqual(ans['answer'],'模拟回答')
        self.assertEqual(len(evidence['samples']),12)
        self.assertNotIn('test-only',req.data.decode())
    def test_malformed_reply(self):
        with patch.object(llm,'configuration',return_value={'api_key':'test','api_base':'https://a.example','model':'m'}),patch('urllib.request.urlopen',return_value=io.BytesIO(b'{}')):
            self.assertEqual(llm.explain(self.result,'原因')['mode'],'大模型API调用失败')
    def test_packaging_excludes_local_secrets(self):
        import subprocess,zipfile,shutil
        project=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'scripts').mkdir();(root/'release').mkdir()
            shutil.copy2(project/'scripts/package_submission.py',root/'scripts/package_submission.py')
            target=root/'outputs'/'SECURITYCHECK-AI+软件创新-无线网络智能诊断助手'
            (root/'llm_config.json').write_text('{"api_key":"dummy-test-only"}')
            (root/'.env').write_text('DUMMY_SECRET=test-only')
            subprocess.run([sys.executable,str(root/'scripts/package_submission.py'),'--team-id','SECURITYCHECK'],check=True,capture_output=True)
            with zipfile.ZipFile(next(target.glob('*完整代码.zip'))) as z:
                self.assertFalse(any(Path(n).name in {'llm_config.json','.env'} for n in z.namelist()))
if __name__=='__main__':unittest.main()
