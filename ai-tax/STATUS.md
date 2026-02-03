# STATUS.md — AI Tax
Last updated: 2026-02-03T17:55Z

## 当前状态: 进行中

## 项目目标
用AI帮用户报税，从Jason自己的2025年税开始验证全流程（包括e-file到IRS）。
架构按产品标准搭，暂不收费但考虑未来商业化。

## 用户Profile (第一个用例)
- Married Filing Jointly
- Massachusetts
- 家庭收入 $500K+ (W-2)
- 投资收入（股票、利息、分红）
- 出租房/投资房
- 房贷、HSA、401K
- 需要税务优化（折旧、退休账户、TLH等）

## 技术路径
- Option A (快): Column Tax白标API + AI前端
- Option B (自建): 参考IRS Direct File开源代码 + MeF集成

## 需要支持的税表
1040, Schedule 1/2/3/A/B/C/D/E, Form 8949/8889/8959/8960, MA State Return

## 已完成
1. [x] 产品可行性研究报告
2. [x] 税务优化Playbook（针对Jason情况）
3. [x] Column Tax API研究 → 结论：白标UI模式，不适合AI-first方案
4. [x] IRS Direct File开源代码架构研究 → Fact Graph引擎是核心可复用组件
5. [x] 项目骨架搭建（models, tax_engine, document_parser, tests）
6. [x] 12个单元测试全部通过（税务计算验证）

## 下一步
1. [ ] Clone Direct File repo，本地跑起来
2. [ ] 研究Fact Graph XML模块，理解税务规则格式
3. [ ] 原型：LLM ↔ Fact Graph集成（AI能否读取fact graph状态并生成问题）
4. [ ] EFIN申请流程启动（需要6-12个月）
5. [ ] Jason提供2025年税表开始跑数据
6. [ ] 搭建文档解析原型（W-2 OCR → 结构化数据）

## 关键研究
- 产品可行性报告: research/ai-tax-product-2026-02-03.md
- 税务优化playbook: research/tax-optimization-playbook-2025.md
- 技术架构研究: research/technical-architecture-research.md

## 技术决策
- **税务引擎**: Fork IRS Direct File的Scala Fact Graph引擎（712+税务facts，经IRS验证）
- **AI层**: LLM替代传统问卷流程，读取Fact Graph状态，生成自然语言问题
- **MeF filing**: Phase 1 生成XML/PDF → Phase 2 合作e-file provider → Phase 3 自有EFIN
- **Column Tax**: 不集成（白标UI模式与AI-first冲突），但参考其合规模型

## Blockers
- 等Jason的W-2/1099/去年1040
- GitHub账号suspended，无法提issue或创建repo
