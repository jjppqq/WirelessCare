"""Reproducible synthetic baseline. Thresholds are project heuristics, not 3GPP limits."""
import csv
import io
import math
import hashlib
from datetime import datetime, timedelta
import numpy as np
from sklearn.ensemble import RandomForestClassifier, IsolationForest

FEATURES = ['rsrp_dbm', 'sinr_db', 'prb_pct', 'drop_pct', 'latency_ms', 'throughput_mbps']
LABELS = ['正常', '覆盖不足', '干扰风险', '负载拥塞', '传输异常']
BOUNDS = [(-160,-30),(-30,60),(0,100),(0,100),(0,10000),(0,10000)]
PROFILES = [([-85,20,42,0.5,20,70],[7,4,15,0.3,6,20]),
            ([-116,3,43,5,55,12],[6,4,18,2,15,6]),
            ([-82,-1,50,4,60,14],[8,3,20,1.7,16,7]),
            ([-85,16,94,3,95,9],[7,4,4,1.3,20,4]),
            ([-85,18,45,2.5,190,18],[7,4,15,1.2,40,8])]
KNOWLEDGE = {
 '覆盖不足': ('K01', '弱接收功率可能与遮挡、覆盖边缘或天线配置有关。', ['先核查天线馈线与告警，再开展现场路测。', '评估下倾角、覆盖补点或小区重选参数，变更前留存原配置。'], '复测RSRP分布、掉线率和邻区干扰。'),
 '干扰风险': ('K02', '信号功率正常但SINR偏低时，应检查同频干扰和重叠覆盖。', ['检查频谱及邻区同频资源使用，排查外部干扰。', '评估资源协调或天线调整，先进行小范围试验。'], '复测SINR与吞吐，确认邻区指标没有恶化。'),
 '负载拥塞': ('K03', 'PRB占用偏高且业务体验下降，可能存在无线资源拥塞。', ['核对忙时用户数、业务构成与流量趋势。', '评估负载均衡、载波扩容或调度参数，先保留回退方案。'], '比较同时间段PRB、时延和吞吐。'),
 '传输异常': ('K04', '无线指标较好而时延显著升高，应检查回传与业务服务器。', ['核查回传丢包、链路利用率和端到端分段时延。', '检查交换机、回传链路及服务器，不直接修改无线发射功率。'], '复测分段时延、丢包和吞吐。'),
 '待核实': ('K05', '现有指标无法区分所有根因，需要补充证据。', ['补充告警、邻区、用户数、丢包与现场测试。'], '新增证据后重新分析。')
}

def synthetic(seed=2026, per_class=400):
    rng=np.random.default_rng(seed); xs=[]; ys=[]
    for label,(mean,std) in zip(LABELS,PROFILES):
        a=rng.normal(mean,std,(per_class,len(FEATURES)))
        for j,(lo,hi) in enumerate(BOUNDS): a[:,j]=np.clip(a[:,j],lo,hi)
        xs.extend(a); ys.extend([label]*per_class)
    return np.array(xs), np.array(ys)

def make_csv(seed=72, per_class=24):
    x,y=synthetic(seed,per_class); out=io.StringIO(); w=csv.writer(out)
    w.writerow(['timestamp','cell_id']+FEATURES+['label'])
    for i,(a,label) in enumerate(zip(x,y)):
        w.writerow([(datetime(2026,9,25,18)+timedelta(minutes=i%per_class*5)).isoformat(), 'CELL-'+str(i//per_class+1), *[round(float(v),2) for v in a],label])
    return out.getvalue()

def parse_csv(text):
    if not isinstance(text,str) or len(text.encode('utf-8'))>2_000_000: raise ValueError('CSV需为UTF-8文本且小于2MB')
    reader=csv.DictReader(io.StringIO(text.lstrip('\ufeff')))
    required=['timestamp','cell_id']+FEATURES
    if not reader.fieldnames or len(set(reader.fieldnames))!=len(reader.fieldnames): raise ValueError('表头缺失或重复')
    missing=set(required)-set(reader.fieldnames)
    if missing: raise ValueError('缺少列：'+', '.join(sorted(missing)))
    rows=[]; seen=set()
    for line,r in enumerate(reader,2):
        if len(rows)>=5000: raise ValueError('最多导入5000行')
        if None in r: raise ValueError(f'第{line}行列数不匹配')
        try:
            dt=datetime.fromisoformat(r['timestamp'].replace('Z','+00:00'))
            cell=r['cell_id'].strip()
            if not cell or len(cell)>64: raise ValueError('小区ID为空或过长')
            key=(dt.isoformat(),cell)
            if key in seen: raise ValueError('同一小区时间戳重复')
            seen.add(key)
            vals=[float(r[k]) for k in FEATURES]
            for k,v,(lo,hi) in zip(FEATURES,vals,BOUNDS):
                if not math.isfinite(v) or not lo<=v<=hi: raise ValueError(f'{k}超出范围[{lo},{hi}]')
        except (ValueError,TypeError,KeyError,AttributeError) as e: raise ValueError(f'第{line}行：{e}') from e
        rows.append(dict(timestamp=dt.isoformat(),cell_id=cell,**dict(zip(FEATURES,vals))))
    if not rows: raise ValueError('数据为空')
    return rows

def evidence(r):
    hits=[]
    if r['rsrp_dbm'] < -105: hits.append(('覆盖不足',f"RSRP={r['rsrp_dbm']:.2f}dBm < -105dBm"))
    if r['sinr_db'] < 5 and r['rsrp_dbm'] >= -105: hits.append(('干扰风险',f"SINR={r['sinr_db']:.2f}dB < 5dB，RSRP未触发弱覆盖阈值"))
    if r['prb_pct'] > 85: hits.append(('负载拥塞',f"PRB={r['prb_pct']:.2f}% > 85%"))
    if r['latency_ms'] > 100 and r['rsrp_dbm'] >= -105 and r['sinr_db'] >= 5 and r['prb_pct'] <=85:
        hits.append(('传输异常',f"时延={r['latency_ms']:.2f}ms > 100ms，覆盖/干扰/负载阈值未触发"))
    if r['drop_pct'] > 2: hits.append(('体验异常',f"掉线率={r['drop_pct']:.2f}% > 2%"))
    return hits

class Engine:
    def __init__(self):
        x,y=synthetic()
        self.rf=RandomForestClassifier(n_estimators=100,max_depth=10,random_state=2026,n_jobs=1).fit(x,y)
        self.iso=IsolationForest(n_estimators=100,contamination=0.05,random_state=2026,n_jobs=1).fit(x[y=='正常'])

    def analyze(self,text):
        rows=parse_csv(text); x=np.array([[r[k] for k in FEATURES] for r in rows])
        p=self.rf.predict_proba(x); anomaly=self.iso.predict(x); scores=self.iso.decision_function(x)
        for i,r in enumerate(rows):
            idx=int(np.argmax(p[i])); pred=str(self.rf.classes_[idx]); conf=float(p[i,idx]); hits=evidence(r)
            causes=list(dict.fromkeys(k for k,_ in hits if k!='体验异常'))
            uncertain=(conf<0.65 or (pred!='正常' and pred not in causes))
            diagnosis='多因素异常' if len(causes)>1 else (causes[0] if causes else ('待核实' if anomaly[i]<0 or hits or pred!='正常' else '正常'))
            kb=[{'id':KNOWLEDGE[c][0],'cause':c,'explanation':KNOWLEDGE[c][1],'actions':KNOWLEDGE[c][2],'verification':KNOWLEDGE[c][3]} for c in (causes or (['待核实'] if diagnosis!='正常' else []))]
            r.update(prediction=pred,confidence=round(conf,4),diagnosis=diagnosis,needs_review=bool(uncertain or diagnosis=='待核实' or len(causes)>1),is_anomaly=bool(anomaly[i]<0),anomaly_score=round(float(scores[i]),4),evidence=[v for _,v in hits],knowledge=kb)
        cells=[]
        for cell in sorted(set(r['cell_id'] for r in rows)):
            group=[r for r in rows if r['cell_id']==cell]
            counts={k:sum(r['diagnosis']==k for r in group) for k in sorted(set(r['diagnosis'] for r in group))}
            cells.append({'cell_id':cell,'samples':len(group),'abnormal':sum(r['diagnosis']!='正常' for r in group),'diagnoses':counts,'means':{k:round(float(np.mean([r[k] for r in group])),2) for k in FEATURES}})
        return {'sha256':hashlib.sha256(text.encode()).hexdigest(),'rows':rows,'cells':cells,'summary':{'samples':len(rows),'cells':len(cells),'abnormal':sum(r['diagnosis']!='正常' for r in rows),'review':sum(r['needs_review'] for r in rows)},'disclosure':'随机森林及孤立森林使用自建合成数据训练。阈值为项目启发式配置，未经真实运营商数据验证。概率不是经校准的真实故障概率。仅生成排查建议，不自动修改网络。'}

def report(result):
    s=result['summary']; lines=['# 无线网络诊断报告','',result['disclosure'],'',f"样本：{s['samples']}；小区：{s['cells']}；异常：{s['abnormal']}；需复核：{s['review']}",f"输入SHA256：{result['sha256']}",'']
    for c in result['cells']: lines.extend([f"## {c['cell_id']}",f"样本{c['samples']}，异常{c['abnormal']}，分类统计：{c['diagnoses']}",f"均值：{c['means']}",''])
    for r in result['rows']:
        if r['diagnosis']=='正常': continue
        lines.extend([f"### {r['timestamp']} / {r['cell_id']} / {r['diagnosis']}",f"模型候选：{r['prediction']}，模型概率：{r['confidence']}，复核：{r['needs_review']}"]+r['evidence'])
        for k in r['knowledge']: lines.extend([f"[{k['id']}] {k['explanation']}"]+k['actions']+[k['verification']])
        lines.append('')
    return '\n'.join(lines)
