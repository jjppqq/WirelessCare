"""Store API settings locally; getpass keeps the key out of terminal history."""
import getpass,json,os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.llm import CONFIG_PATH,validate_base

def main():
    print('只配置你已开通的OpenAI兼容服务。使用方需承担服务调用费用。密钥不会上传。')
    base=validate_base(input('HTTPS API基础地址（通常以/v1结尾）：').strip())
    model=input('实际模型名称：').strip()
    key=getpass.getpass('API密钥（输入隐藏）：').strip()
    if not model or not key: raise ValueError('模型名称和密钥不能为空')
    # Truncate using a private descriptor rather than briefly creating a public file.
    fd=os.open(CONFIG_PATH,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(fd,'w',encoding='utf-8') as f:
        json.dump({'api_base':base,'model':model,'api_key':key},f,ensure_ascii=False,indent=2)
    if os.name!='nt': os.chmod(CONFIG_PATH,0o600)
    print('已保存本地配置。先运行python scripts/check_llm.py，成功后重启python run.py。')
if __name__=='__main__':
    try:main()
    except (ValueError,OSError) as e: print(str(e));sys.exit(2)
