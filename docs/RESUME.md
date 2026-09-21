# 简历项目经历（草稿）

> 数据分析多智能体系统（Text-to-SQL · 魔改 MetaGPT）—— 可直接贴进简历的版本。
> 所有数字均来自本项目真实评估（`evaluate.py` / `evaluate_repair.py`），不编造。

## 标准版（4 条 bullet）

**数据分析多智能体系统（Text-to-SQL · 魔改 MetaGPT）** ｜ 2026.09 ｜ 个人项目
*Python · LangGraph · DuckDB · LangChain · DeepSeek · Pydantic · FastAPI*

- **【S/T】** 针对「LLM 只会生成 SQL 文本、说不出可信数据结论」的痛点，将 MetaGPT 的「软件公司 SOP」重构为「数据分析团队」，目标是从自然语言问题直接产出基于真实数据的结论。
- **【A】** 用 LangGraph 编排 6 个职责单一 Agent（需求分析→schema linking→规划→执行→校验→报告），共享 state 传递上下文；执行 Agent 的 SQL 真实跑在 DuckDB 上（`read_only` 连接代码层兜底），查询结果结构化回流、不经 LLM 字符串转述，杜绝编造数字。
- **【A】** 落地 Text-to-SQL 的 schema linking 与多表建模：schema 运行时从 `information_schema` 动态读（单一事实来源，去硬编码），linker 按问题精筛相关表/列 + join 关系，建模 3 张表（事件事实表 + 仓库/用户维度表）；辅以 self-repair（报错回流→结构化修正→重跑，上限 3 次）+ human-in-the-loop（`interrupt` 人工复核，reject 回环重跑）+ SQLite 持久化 checkpoint（服务重启不丢会话）。
- **【R】** 自建 12 问标注评估集 + 单 LLM 基线 ablation：**端到端正确率 100%（12/12）vs 基线 0%（12/12）**；schema linking 改造后准确率持平、并修掉去硬编码引发的「LLM 幻觉时间范围」隐患（动态读数据时间范围注入需求分析）；self-repair 对 8 条注入错误 SQL **修复率 8/8**；数据为 GH Archive 真实 GitHub 事件 108,537 条。

---

## 评估结果（真实数据）

| 指标 | single-shot（单 LLM） | multi-agent（多 agent） |
|---|---|---|
| SQL 执行成功率 | 12/12 = 100% | 12/12 = 100% |
| 答案正确率（含关键事实） | 0/12 = 0% | 12/12 = 100% |
| 端到端正确率（查到且答对） | 0/12 = 0% | 12/12 = 100% |

- self-repair 压力测试：8 条故意注入常见错误的 SQL（列名/表名写错、漏引号、时间戳格式错、别名不存在），**修复率 8/8**。
- schema linking 前后对比：multi-agent 均 12/12（准确率持平）—— schema linking 是「工程化重构」（去硬编码 + 多表建模），不是提分项；真实价值是 schema / 数据变更时系统自动跟随，并顺带修掉一个时间幻觉隐患。
- 基线 0% 的根因：单 LLM 一次调用同时生成 SQL 和答案，答案写于「看到查询结果之前」，只能编数字（`12,345 条`、`[repo_name]`、`[cnt]`、`0 条（示例结果）`）——「SQL 能跑 ≠ 结论对」。

## 示例输出（真实运行）

问：2026-09-01 00:00–02:00 这两个小时，GitHub 上哪种事件类型最多？

答：**PushEvent，共 104,834 条，占该时段全部事件（108,537 条）的 96.59%**，置信度 0.97。

> 这是 `main.py` 的真实输出：SQL 真查 DuckDB、结论引用真实数字，不是 LLM 口头编的。面试可用它证明「真执行 + 结果回流」的实际效果。

## 面试钩子（每条 bullet 对应的可深挖点）

1. **多智能体编排**：为什么拆 6 个 agent 而非一个大 prompt？state 怎么流转？schema linking / 校验 / 报告为什么是独立职责？
2. **真执行去 toy 化**：结果为什么要结构化回流、不经 LLM 字符串？`read_only` 连接的意义？——引出「single-shot 编数字」的 ablation。
3. **schema linking**：为什么 Text-to-SQL 需要它？动态读 `information_schema` vs 硬编码 prompt 的取舍？linker 怎么精筛表列 + join？为什么拆维度表？（见 QA 文档）
4. **数据概览防幻觉**：去硬编码后 planner 对「这两个小时」幻觉成 2024-01-01 的坑，怎么定位、怎么用动态数据时间范围修掉？
5. **self-repair**：报错如何回流？为什么用结构化输出修正而非自由文本？上限 3 次的意义？修复率 8/8 怎么测的（注入错误）？
6. **human-in-the-loop**：哪些结论需要人工复核？`interrupt` 底层机制？reject 是真回环（回到 plan 重跑）还是假按钮？
7. **持久化 checkpoint**：为什么从 `MemorySaver` 换 `SqliteSaver`？`from_conn_string` 是上下文管理器、退出即关连接的坑？服务重启怎么不丢会话？
8. **后端两阶段 HITL**：`/ask` + `/review` 怎么把 `interrupt` 变成 HTTP？thread_id 怎么对应会话？
9. **评估体系**：评估集怎么设计？为什么用「确定性关键事实对拍」而非 LLM 判题（避免判题 bias）？基线为什么设计成「单次调用」？

## 诚实说明（面试被追问时的底线）

- 所有数字真实：108,537 条事件、12 问评估、端到端 100%、self-repair 8/8、6 agent、修复上限 3 次、27 个单测。
- **样本量小**：12 问、单表聚合类问题、单次运行（LLM 有随机性）。结论方向性可信（多 agent 显著优于单 LLM），绝对数值需谨慎，面试如实说「小样本验证，可扩」。
- **基线公平性**：single-shot 是「单次调用同时出 SQL+答案」；若面试官问「换成『写 SQL→执行→再看结果写答案』两步呢」——答：两步版本质已把 execute 和 report 拆开，就是往多 agent 走的方向；基线的意义是证明「不做结果回流，LLM 会编数字」。
- **self-repair 在 12 问主评估里修复 0 次**（planner SQL 均语法正确），其价值由注入错误压力测试（8/8）单独证明。
- **schema linking 的价值边界**：当前 3 张表、12 问单表聚合，linker 的「精筛」优势尚未在大 schema 上量化验证；它在本项目里更多体现为「去硬编码 + 多表 join 能力 + 数据概览防幻觉」，面试如实说「机制已落地，规模验证待扩」。
- 数据为 2 小时演示规模，能力上限取决于「拉多少小时数据」（GH Archive 公开可扩、DuckDB 列式扫描），非系统瓶颈。
