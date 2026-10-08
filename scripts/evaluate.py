import sys,json,time,platform,csv
from pathlib import Path
import numpy as np,sklearn
from sklearn.metrics import classification_report,confusion_matrix
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.engine import Engine,synthetic,make_csv,FEATURES,LABELS
root=Path(__file__).resolve().parents[1];out=root/'docs'/'test_results';out.mkdir(exist_ok=True)
e=Engine();x,y=synthetic(seed=9088,per_class=160);pred=e.rf.predict(x)
times=[]
for _ in range(8):
    t=time.perf_counter();r=e.analyze(make_csv(per_class=100));times.append((time.perf_counter()-t)*1000)
baseline=np.array(['覆盖不足' if v[0]<-105 else '干扰风险' if v[1]<5 else '负载拥塞' if v[2]>85 else '传输异常' if v[4]>100 else '正常' for v in x])
metrics={'dataset':'合成数据，同一生成机制不同随机种子，不能代表真实网络泛化性能','train_seed':2026,'test_seed':9088,'test_samples':len(y),'train_samples':2000,'python':platform.python_version(),'numpy':np.__version__,'sklearn':sklearn.__version__,'classification':classification_report(y,pred,output_dict=True),'threshold_baseline_accuracy':float(np.mean(baseline==y)),'confusion_labels':LABELS,'confusion_matrix':confusion_matrix(y,pred,labels=LABELS).tolist(),'performance':{'samples':500,'repeats':8,'median_ms':round(float(np.median(times)),2),'p95_ms':round(float(np.percentile(times,95)),2)},'llm_live_test':'未配置真实API密钥，未做真实服务联调；仅完成模拟响应及失败分支测试'}
(out/'metrics.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2))
(out/'example_analysis.json').write_text(json.dumps(e.analyze(make_csv()),ensure_ascii=False,indent=2))
with (out/'holdout_synthetic.csv').open('w') as f:
    w=csv.writer(f);w.writerow(FEATURES+['label','prediction']);w.writerows([*map(float,a),b,c] for a,b,c in zip(x,y,pred))
print(json.dumps(metrics,ensure_ascii=False,indent=2))
