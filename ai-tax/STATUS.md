# STATUS.md — AI Tax
Last updated: 2026-02-05T21:00Z

## 当前状态: UI开发中 🚀

## 项目目标
用AI帮用户报税，从Jason自己的2024年税开始验证全流程。
目标：让朋友家人能用（免费），架构按产品标准搭，考虑未来商业化。

## 用户Profile (第一个用例)
- Married Filing Jointly
- Massachusetts
- 家庭收入 $500K+ (W-2)
- 投资收入（股票、利息、分红）
- 出租房/投资房
- 房贷、HSA、401K
- 需要税务优化（折旧、退休账户、TLH等）

## 已完成 ✅

### 核心引擎
- [x] Tax Engine with 2024/2025 constants
- [x] Fact Graph engine (IRS Direct File inspired)
- [x] Document parser scaffolding
- [x] Federal core module (tax brackets, deductions)
- [x] Income sources module (W-2, 1099 handling)
- [x] Investments module (capital gains, dividends)
- [x] 46 unit tests passing

### 安全 & 合规
- [x] AES-256-GCM encryption (upgraded from AES-128)
- [x] Data retention policy (3 years)
- [x] PII masking & secure logging
- [x] WISP (Written Information Security Plan)
- [x] Privacy Policy
- [x] Terms of Service  
- [x] User Consent Form (§7216 compliant)
- [x] Legal review document

### UI (Mercury风格)
- [x] Static HTML preview
- [x] Reflex app structure
- [x] Dashboard page (stats, documents, summary)
- [x] Upload page (drag & drop)
- [x] Review page (tax calculations)
- [x] Settings page (API keys, options)
- [x] Dark theme with gradient accents
- [x] Inter font, glass card effects

## 进行中 🔄
- [ ] Connect UI to tax engine (state → calculations)
- [ ] Document parsing with AI (OCR → structured data)
- [ ] Google OAuth integration (Drive/Gmail)

## 下一步 📋
1. 完善UI-backend集成
2. 测试Reflex app本地运行
3. 等Jason上传2024税务文档到Drive
4. 跑通完整流程：上传 → 解析 → 计算 → 生成报告

## 技术栈
- **Backend**: Python 3.12
- **Tax Engine**: Custom (IRS Direct File inspired)
- **UI**: Reflex (Python → React)
- **Document Parsing**: Claude Vision / local OCR
- **Encryption**: AES-256-GCM (Fernet wrapper)
- **OAuth**: Google APIs (Drive, Gmail)

## 关键文件
```
ai-tax/
├── src/core/
│   ├── tax_engine.py      # Tax calculations
│   ├── fact_graph.py      # IRS Fact Graph
│   ├── tax_constants.py   # 2024/2025 brackets
│   ├── encryption.py      # AES-256-GCM
│   └── modules/           # Federal, income, investments
├── ui/
│   ├── aitax/             # Reflex app
│   │   ├── aitax.py       # Main pages
│   │   ├── state.py       # App state
│   │   └── components.py  # UI components
│   └── preview.html       # Static preview
├── docs/
│   ├── WISP.md            # Security plan
│   ├── PRIVACY-POLICY.md
│   ├── TERMS-OF-SERVICE.md
│   ├── USER-CONSENT-FORM.md
│   └── LEGAL-REVIEW.md
└── tests/                 # 46 tests
```

## 研究文档
- 产品可行性: `research/ai-tax-product-2026-02-03.md`
- 税务优化: `research/tax-optimization-playbook-2025.md`
- 技术架构: `research/technical-architecture-research.md`
- 改进研究: `research/improvements-research-2026-02-05.md`

## 技术决策记录
| 决策 | 选择 | 原因 |
|------|------|------|
| Tax Engine | 自建 (Python) | Direct File是Scala，我们用Python复用逻辑 |
| UI Framework | Reflex | Python全栈，Mercury级美观度 |
| Encryption | AES-256-GCM | 合规要求，替换了Fernet的AES-128 |
| Column Tax | 不集成 | 白标UI模式与AI-first冲突 |
| PTIN | 暂不需要 | 朋友家人免费用不需要 |

## 合规状态
- ✅ FTC Safeguards Rule (WISP)
- ✅ IRS Pub 4557 (security)
- ✅ IRC §7216 consent (rewritten)
- ✅ Anthropic DPA (auto-included in ToS)
- ⏳ PTIN ($30.75/yr) - 商业化时需要

## Blockers
- 等Jason上传2024税务文档
- GitHub账号suspended
