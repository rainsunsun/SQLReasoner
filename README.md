# 数据分析多智能体（Text-to-SQL · 魔改 MetaGPT）

把 MetaGPT 的「软件公司 SOP」改成「数据分析团队」：从自然语言问题直接产出基于**真实数据**的分析结论。

核心是 **「真执行去 toy 化」**——LLM 生成的 SQL 真的跑在 DuckDB 上、查询结果结构化回流、报错回流自我修正，而不是「假装写代码」。

## 核心亮点

- **真执行**：执行 Agent 的 SQL 真实跑在 DuckDB 上（`read_only` 连接代码层兜底），查询结果结构化回流、不经 LLM 字符串转述，杜绝编造数字。
- **SQL 自我修复**：执行失败 → 报错回流 → LLM 结构化修正 → 重跑（上限 3 次）。
- **human-in-the-loop**：校验不过或结论低置信时 `interrupt` 中断人工复核，拒绝则回环重跑。
- **有评估、有基线**：自建 12 问标注集 + 单 LLM 基线 ablation，用数据证明「拆 agent + 结果回流」的价值。

## 架构

```
自然语言问题
    │
    ▼
[understand 需求分析] ──► AnalysisGoal
    │
    ▼
[plan 规划拆 SQL] ──► QueryPlan
    │
    ▼
[execute 执行 + self-repair] ──► 真实查询结果（DuckDB 真查）
    │
    ▼
[verify 校验] ──► 是否可信
    │
    ▼
[report 报告] ──► 结论 + 置信度
    │
    ▼
低置信/校验不过 ──► [review 人工复核] ──(reject)──► 回到 plan
                        │
                      (accept)
                        │
                        ▼
                      END
```

- **understand**：把业务问题翻译成可执行的分析目标（指标/维度/过滤/输出形式）。
- **plan**：把目标拆成按序执行的只读 SELECT。
- **execute**：真执行 SQL；失败时把报错原样回流给 LLM 修正后重跑（self-repair）。
- **verify**：校验结果合理性（是否为空、量级是否合理、是否回答了问题）。
- **report**：把结果解读成带真实数字的结论 + 置信度。
- **review**：`interrupt` 交人工 accept/reject，reject 回环到 plan（上限防死循环）。

## 技术栈

| 层 | 选型 |
|---|---|
| 编排 | LangGraph（StateGraph + MemorySaver + interrupt） |
| LLM | OpenAI 兼容接口（DeepSeek，可切 Claude/Qwen/GLM） |
| 结构化输出 | Pydantic + `with_structured_output` |
| 数据仓库 | DuckDB（read_only 只读连接） |
| 数据源 | GH Archive 真实 GitHub 事件 |

## 目录结构

```
app/
  agents/         # 5 个 agent：understand / planner / executor / verifier / reporter
  graph/          # workflow.py：LangGraph 编排
  tools/          # db.py：execute_sql 真执行
  models.py       # Pydantic 领域模型
  state.py        # 共享 state
data/
  analytics.duckdb  # 108,537 条真实事件（2026-09-01 00:00~02:00）
  load_data.py      # 从 GH Archive 下载建表
  eval/             # 评估集 questions.py + 报告 eval_report.md
evaluate.py         # 三组对照评估（多 agent vs 单 LLM vs 无修复）
evaluate_repair.py  # self-repair 压力测试
main.py             # CLI 入口
docs/RESUME.md      # 简历 + 面试钩子
```

## 快速开始

```bash
# 1. 装依赖（建议独立 venv；见下方「环境说明」）
pip install -r requirements.txt

# 2. 配 .env（LLM_API_KEY / LLM_BASE_URL / LLM_MODEL）

# 3. 问一个问题
python main.py "2026-09-01 00:00 到 02:00 这两个小时，GitHub 上哪种事件类型最多？"
```

真实输出示例：

```
回答: PushEvent 最多，共 104,834 条，占该时段全部事件(108,537 条)的 96.59%
可信度: 0.97
```

## 跑评估

```bash
python evaluate.py            # 12 问三组对照，输出 data/eval/eval_report.md
python evaluate_repair.py     # self-repair 压力测试（注入 8 条错误 SQL）
python data/load_data.py --date 2026-09-01 --hours 24   # 扩数据（拉更多小时）
```

## 评估结果（真实，2026-09-22）

| 指标 | 单 LLM 基线 | 多 agent |
|---|---|---|
| SQL 执行成功率 | 12/12 = 100% | 12/12 = 100% |
| **端到端正确率** | **0/12 = 0%** | **12/12 = 100%** |

- self-repair 压力测试：8 条注入错误 SQL，修复率 **8/8**。
- 基线 0% 的根因：单 LLM 一次调用同时生成 SQL 和答案，答案写于「看到查询结果之前」，只能编数字 —— **「SQL 能跑 ≠ 结论对」**。

## 环境说明

- 本项目目前**未建独立 venv**，开发时复用 `agent_qz` 的 venv（`D:\学习日志\agent_qz\.venv\Scripts\python.exe`）。建议后续建独立环境：`python -m venv .venv && .venv\Scripts\pip install -r requirements.txt`。
- 终端中文乱码是 Windows GBK 显示问题，代码已 `sys.stdout.reconfigure(utf-8)`，报告以 `data/eval/eval_report.md` 为准。

## 已知边界

- 12 问、单表聚合、单次运行——小样本，方向性可信，绝对数值需谨慎。
- schema 硬编码在 prompt（单表 7 列）；真实 Text-to-SQL 的 schema linking 是下一步。
- 数据为 2 小时演示规模，可随时扩（GH Archive 公开可扩、DuckDB 列式扫描）。
