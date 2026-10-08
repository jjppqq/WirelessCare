"""Actual API smoke test with synthetic KPI; never reports mocks as live results."""
import argparse,hashlib,json,sys,time
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.engine import Engine,make_csv
from backend.llm import configuration,validate_base,explain,select_samples

def main():
    p=argparse.ArgumentParser(description='真实API联调，只发送合成KPI；可能产生供应商费用')
    p.add_argument('--output',default='outputs/llm_check.json');args=p.parse_args()
    config=configuration();required=[k for k,v in config.items() if not v]
    if required:
        print('未调用API：缺少配置 '+', '.join(required)+'。先运行python scripts/configure_llm.py。')
        return 2
    base=validate_base(config['api_base'])
    result=Engine().analyze(make_csv());beg=time.perf_counter()
    response=explain(result,'请比较各小区的候选故障原因，引用知识编号，给出需要补充的证据和复测方法。')
    success=response['mode']=='大模型API辅助说明（需人工复核）'
    answer=response['answer']
    evidence={'tested_at':datetime.now(timezone.utc).isoformat(),'status':'api_response_received' if success else 'api_failed',
      'mode':response['mode'],'api_base':base,'model':config['model'],'elapsed_ms':round((time.perf_counter()-beg)*1000,2),
      'data_source':'project_generated_synthetic','input_sha256':result['sha256'],
      'sent_sample_count':len(select_samples(result['rows'])),'answer_sha256':hashlib.sha256(answer.encode()).hexdigest(),
      'answer':answer,'manual_review':{'knowledge_references':None,'numeric_fidelity':None,'cause_uncertainty':None,'safe_verification_plan':None},
      'disclosure':'接到真实服务响应不等于回答质量通过；人工复核项待实际审查。未完成团队试用。'}
    dest=Path(args.output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
    print('真实API响应已收到，需人工复核。' if success else 'API调用失败，请检查配置、额度和网络。')
    print('联调记录已保存：'+str(dest));return 0 if success else 1
if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,OSError) as e: print(str(e));sys.exit(2)
