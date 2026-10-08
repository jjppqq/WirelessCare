"""After team review, assign a real contest team ID to files. Does not submit."""
import argparse,shutil,re,zipfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--team-id',required=True);a=p.parse_args()
if not re.fullmatch(r'[A-Za-z0-9_-]{1,50}',a.team_id):p.error('请输入实际团队编号，仅字母数字下划线连字符')
root=Path(__file__).resolve().parents[1];prefix=a.team_id+'-AI+软件创新-无线网络智能诊断助手';target=root/'outputs'/prefix;target.mkdir(parents=True,exist_ok=True)
for f in (root/'release').iterdir():
    if f.is_file():shutil.copy2(f,target/(prefix+'-'+f.name))
with zipfile.ZipFile(target/(prefix+'-完整代码.zip'),'w',zipfile.ZIP_DEFLATED) as archive:
    for f in root.rglob('*'):
        rel=f.relative_to(root)
        if f.is_file() and not any(x in {'outputs','release','.git','.venv','__pycache__'} for x in rel.parts) and f.name not in {'.env','llm_config.json'} and not f.name.endswith('.log'):
            archive.write(f,Path('WirelessCare')/rel)
print('已整理材料：',target,'。请确认团队审查、官方模板、API联调及材料真实性后再提交。')
