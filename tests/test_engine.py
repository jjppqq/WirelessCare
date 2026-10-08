import unittest,sys,io,json,os
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.engine import Engine,make_csv,parse_csv,report,FEATURES
from backend.llm import explain

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.engine=Engine();cls.csv=make_csv();cls.result=cls.engine.analyze(cls.csv)
    def test_demo(self):self.assertEqual(self.result['summary']['samples'],120)
    def test_missing(self):
        with self.assertRaises(ValueError):parse_csv('cell_id,rsrp_dbm\na,-90')
    def test_nan(self):
        lines=self.csv.splitlines();row=lines[1].split(',');row[2]='nan';lines[1]=','.join(row)
        with self.assertRaises(ValueError):parse_csv('\n'.join(lines))
    def test_percent_range(self):
        lines=self.csv.splitlines();row=lines[1].split(',');row[4]='101';lines[1]=','.join(row)
        with self.assertRaises(ValueError):parse_csv('\n'.join(lines))
    def test_duplicate(self):
        with self.assertRaises(ValueError):parse_csv(self.csv+self.csv.splitlines()[1]+'\n')
    def test_label_not_used(self):
        other=self.csv.replace('覆盖不足','伪造标签').replace('正常','干扰风险')
        a=self.engine.analyze(other)
        self.assertEqual([r['diagnosis'] for r in a['rows']],[r['diagnosis'] for r in self.result['rows']])
    def test_bom(self):self.assertEqual(len(parse_csv('\ufeff'+self.csv)),120)
    def test_reproducible(self):self.assertEqual(self.result,self.engine.analyze(self.csv))
    def test_multi(self):
        txt='timestamp,cell_id,'+','.join(FEATURES)+'\n2026-09-25T00:00:00,CELL-X,-120,1,95,6,140,3\n'
        r=self.engine.analyze(txt)['rows'][0];self.assertEqual(r['diagnosis'],'多因素异常');self.assertTrue(r['needs_review'])
    def test_report(self):self.assertIn('K01',report(self.result));self.assertIn(self.result['sha256'],report(self.result))
    def test_offline(self):
        with patch.dict(os.environ,{},clear=True):self.assertIn('未调用大模型',explain(self.result,'先检查什么')['mode'])
    def test_api_payload(self):
        response=io.BytesIO(json.dumps({'choices':[{'message':{'content':'测试服务响应'}}]}).encode())
        with patch.dict(os.environ,{'WIRELESSCARE_API_KEY':'test','WIRELESSCARE_API_BASE':'https://example.com/v1','WIRELESSCARE_MODEL':'test'},clear=True),patch('urllib.request.urlopen',return_value=response) as call:
            a=explain(self.result,'原因');self.assertEqual(a['answer'],'测试服务响应');self.assertIn('K01',json.loads(call.call_args.args[0].data)['messages'][1]['content'])
    def test_api_failure(self):
        with patch.dict(os.environ,{'WIRELESSCARE_API_KEY':'test','WIRELESSCARE_API_BASE':'https://example.com/v1','WIRELESSCARE_MODEL':'test'},clear=True),patch('urllib.request.urlopen',side_effect=OSError('failure')):self.assertIn('失败',explain(self.result,'原因')['mode'])
    def test_empty(self):
        with self.assertRaises(ValueError):parse_csv('timestamp,cell_id,'+','.join(FEATURES))

if __name__=='__main__':unittest.main(verbosity=2)
