# WirelessCare · 无线网络智能诊断助手

2026 AIC 算法创新赛 / AI+软件创新 的 AI辅助开发原型。

完整研究主题：基于大模型的无线通信网络智能故障诊断与优化助手。

## 当前状态

- 可运行：CSV导入、输入校验、随机森林候选分类、孤立森林异常检测、证据与知识库解释、趋势图、报告与JSON导出。
- 可运行：离线知识库证据汇总，明确标注未调用大模型。
- 已实现、未真实联调：OpenAI兼容大模型API。需团队自行配置合法服务及密钥。
- 尚未完成：团队试用与成果归属确认、官方模板套版、团队编号命名、真实API联调、百度网盘正式提交。
- 数据来源：自建合成数据。不存在运营商实测数据、用户试点、专利或软著。
- 此版本由AI辅助生成代码与材料，尚未由参赛团队完成审查，不应直接作为已独立完成的团队成果提交。官方规则禁止代做。

## 功能

1. 导入时间、小区ID与六项通信KPI，校验缺列、范围、空值和重复时间。
2. 训练并运行随机森林与孤立森林，CSV中的label列不参与预测。
3. 将模型候选与阈值证据并列呈现，保留多因素异常与待核实状态。
4. 查询K01–K05知识条目，给出排查、优化建议与复测指标。
5. 查看各小区趋势，导出全部结果及可追溯输入哈希。
6. 可选调用服务端大模型API，仅提供辅助解释，不生成测量值。

## 快速开始

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python run.py
```

浏览器打开 http://127.0.0.1:8787 。Windows也可双击 `scripts/start_windows.bat`。

测试环境为Python 3.12.14 / numpy 2.3.5 / scikit-learn 1.8.0。Python 3.10及以上为目标环境，其他组合尚未实测。

## 可选大模型

推荐运行以下工具，在自己电脑的终端隐藏输入密钥。不要把密钥发到聊天或提交到GitHub。

```bash
python scripts/configure_llm.py
python scripts/check_llm.py
python run.py
```

联调步骤与人工复核项见[大模型联调与团队试用](docs/联调与团队试用.md)。也可设置以下服务端环境变量，优先于本地配置。

```bash
export WIRELESSCARE_API_BASE="https://your-provider.example/v1"
export WIRELESSCARE_API_KEY="your-local-key"
export WIRELESSCARE_MODEL="your-model-name"
python run.py
```

PowerShell使用 `$env:WIRELESSCARE_API_KEY="..."` 等形式。环境变量缺失时自动使用明确标注的离线说明。示例域名与模型名必须替换为实际服务配置。外部服务会收到最多12条按小区和诊断类型轮选的异常样本及摘要，真实数据接入前应确认授权并脱敏。

## 项目结构

```text
WirelessCare/
  backend/       数据校验、模型、知识库、大模型适配
  frontend/      中文Web工作台
  demo_data/     合成CSV示例
  docs/          软件说明、算法、测试、架构、规则对照
  scripts/       启动、评估、提交命名工具
  tests/         可重复运行的测试
  release/       方案PDF、答辩材料、演示MP4草稿
  run.py         HTTP服务启动入口
  requirements.txt
```

## 复现实验

```bash
python -m unittest discover -s tests -v
python scripts/evaluate.py
```

指标见 `docs/test_results/metrics.json`，实验局限见 `docs/测试报告.md`。

## 许可与来源

团队审查前保留版权及许可决定，不擅自代表团队发布MIT许可证。第三方依赖许可见 `docs/第三方资源与AI使用说明.md`。参考同学CommAgent的目录组织和README形式，未复制其代码、算法或素材。

## 材料下载

所有草稿位于[release](release/)，提交前核对[官方要求对照](docs/SCORING.md)。精确复现环境可使用requirements.lock.txt，其他平台需重新验证。
