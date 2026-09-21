# agent-analyst：数据分析多智能体（Text-to-SQL · 魔改 MetaGPT）

一句话：把 MetaGPT 的「软件公司 SOP」改成「数据分析团队」，从自然语言问题直接产出基于真实数据的结论。
核心卖点是「真执行去 toy 化」——LLM 生成的 SQL 真的跑在 DuckDB 上、结果结构化回流、报错回流自我修正，
而不是「假装写代码」。

## 五个 Agent（LangGraph 流水线）

understand（需求分析）→ plan（规划拆 SQL）→ execute（**真执行 SQL + self-repair**）→ verify（校验）→ report（报告）
→ 低置信/校验不过时 `interrupt` 人工复核，拒绝则回环到 plan 重跑（上限 2 次防死循环）。

## 目录结构

- `app/agents/`：5 个 agent（understand / planner / executor / verifier / reporter）
- `app/graph/workflow.py`：LangGraph 编排
- `app/tools/db.py`：`execute_sql` 真执行 DuckDB（read_only 连接）
- `app/models.py` / `app/state.py`：Pydantic 领域模型 + 共享 state
- `data/analytics.duckdb`：77MB，108,537 条真实 GitHub 事件（2026-09-01 00:00~02:00）
- `data/load_data.py`：从 GH Archive 下载并建表（`created_at` 存 TIMESTAMP 是踩坑后的修法）
- `data/eval/`：评估集 + 报告
- `docs/RESUME.md`：简历 + 评估结果 + 面试钩子

## 怎么跑（本项目复用 agent_qz 的 venv，duckdb/langgraph/langchain 都装在那里）

```bash
D:\学习日志\agent_qz\.venv\Scripts\python.exe main.py "问题"          # 单次问问题
D:\学习日志\agent_qz\.venv\Scripts\python.exe evaluate.py             # 跑 12 问评估
D:\学习日志\agent_qz\.venv\Scripts\python.exe evaluate_repair.py      # self-repair 压力测试
D:\学习日志\agent_qz\.venv\Scripts\python.exe -m pytest -q             # 单元测试（17 个）
D:\学习日志\agent_qz\.venv\Scripts\python.exe -m ruff check .          # 代码检查
D:\学习日志\agent_qz\.venv\Scripts\python.exe data/load_data.py --date 2026-09-01 --hours 2  # 扩数据
```

正式环境用 `pip install -e ".[dev]"`（见 pyproject.toml），别长期借用 agent_qz 的 venv。

`.env` 里有 DeepSeek API key（git 已忽略）。终端中文乱码是 GBK 显示问题，代码里已 `sys.stdout.reconfigure(utf-8)`，报告以 `data/eval/eval_report.md` 为准。

## 评估结果（真实数字，2026-09-22）

- 12 问标注集（答案预先用真实数据算好）：**多 agent 端到端正确率 12/12 = 100%**，单 LLM 基线 **0/12**（答案写于看到查询结果之前，只会编数字/留占位符）。
- self-repair 压力测试：8 条注入错误 SQL，**修复率 8/8**。
- 关键结论：**「SQL 能跑 ≠ 结论对」**——结果回流是必须项不是可选项。

## 已知边界 / 待改进（面试被问怎么答）

- 样本量小（12 问、单表聚合、单次运行）——方向性可信，绝对数值需谨慎。
- schema 硬编码在 prompt（单表 7 列）；真实 Text-to-SQL 的 schema linking 是下一步。
- self-repair 在主评估里修复 0 次（planner SQL 语法都对），价值靠注入错误压力测试单独证明。
- 数据 2 小时演示规模，可随时拉更多小时（GH Archive 公开可扩）。

## 注意

- 这是「数据分析」方向，不是隔壁 `agent_qz` 的「招聘」方向（那是最早放弃的方向）。
- GitHub 仓库：https://github.com/rainsunsun/SQLReasoner.git（改完代码记得 commit + push）。
- 工程化已落地：pydantic-settings 配置校验 / LLM 超时重试 / DuckDB read_only + SELECT 白名单 / pytest 单测 / ruff / GitHub Actions CI，详见 README「工程化与稳健性」。
