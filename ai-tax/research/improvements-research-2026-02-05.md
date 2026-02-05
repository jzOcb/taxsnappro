# AI Tax — Improvements Research Report
**Date:** 2026-02-05
**Context:** 529 facts, 14 modules, Federal + MA state taxes, forked from IRS Direct File Fact Graph

---

## Table of Contents
1. [Competitive Landscape (Feb 2026)](#1-competitive-landscape-feb-2026)
2. [Document OCR/Parsing — Best Approaches](#2-document-ocrparsing--best-approaches)
3. [Tax Optimization Engine Ideas](#3-tax-optimization-engine-ideas)
4. [MeF E-Filing Alternatives](#4-mef-e-filing-alternatives)
5. [Technical Improvements](#5-technical-improvements)
6. [Priority Summary & Roadmap](#6-priority-summary--roadmap)

---

## 1. Competitive Landscape (Feb 2026)

### 1.1 Major Players — AI Features Update

#### TurboTax / Intuit
- **Intuit Assist** is their flagship AI feature: integrated across TurboTax, QuickBooks, Credit Karma
- AI-powered document scanning (W-2, 1099 photo import) — been doing this since ~2019, now with better accuracy
- "Expert Assist" tier: AI pre-fills + on-demand CPA review
- AI tax chatbot answers questions in natural language during filing flow
- **Pricing:** Free → $0 (simple W-2 only, with upsell traps); Deluxe $69; Premier $109; Self-Employed $129 + state fees ($59/state)
- **Moat:** Massive user base, IRS import integrations, brand trust, network effects with QuickBooks/Credit Karma
- **Weakness:** Aggressive upselling, confusing pricing, "dark patterns" criticism ongoing

#### H&R Block
- AI-powered "Tax Pro Review" — AI pre-reviews returns before human CPA signs
- AI assistant answers tax questions during DIY filing
- Mobile photo import for W-2s
- **Pricing:** Free (simple); Deluxe $55; Premium $85; Self-Employed $115 + state ($45/state)
- **Moat:** 10,000+ physical locations, dual DIY + in-person model
- **Weakness:** Slower AI innovation than Intuit; app UX inferior

#### Keeper (formerly KeeperTax) — 🔥 Key Competitor
- **AI-first approach** — most directly comparable to our vision
- Patented AI algorithm scans bank transactions for deductible expenses
- AI preps returns with 300+ automated checks
- AI tax assistant trained on tax law + human tax experts on standby
- Every return reviewed and signed by a CPA/EA
- **Pricing:** Standard $199/yr; Premium $399/yr; Business $1,199/yr
- **Target:** Self-employed, 1099 workers, complex individual returns
- **Moat:** Bank account linking, year-round expense tracking, AI+human hybrid model
- **Key learning for us:** Hybrid AI + human expert model is the market trend. Users want AI speed but human assurance.

#### Column Tax — Embedded E-Filing Platform
- White-label embedded tax filing API for fintechs and banks
- Partners with Cash App, MoneyLion, and other fintech platforms
- **API-first model** with white-labeled UI components
- SOC 2 certified, IRS Authorized e-file provider
- 99.999%+ historical uptime
- Claims "zero to accepted returns in one week" integration timeline
- **Key insight:** They're a B2B2C platform, not direct-to-consumer. Their UI comes bundled — doesn't work for AI-first custom UX.
- **Relevance to us:** Still the fastest path to e-filing if we can tolerate their UI overlay, but conflicts with our conversational AI approach. Could revisit as a fallback for e-filing only.

#### UsTaxes (Open Source)
- Free, open-source tax filing web app (React + TypeScript)
- Supports Federal 1040 for tax years 2020–2023
- Supported forms: W-2, 1099-INT, 1099-DIV, 1099-B, 1098-E, 1099-R, SSA-1099
- Schedules: 1, 2, 3, B, D, E, 8812, 8949, 8889, 8959, 8960
- State support: Only Illinois + no-income-tax states
- **Relevance:** Reference implementation for form calculations; their codebase could provide validation test cases. Client-side only (no server, data stays in browser localStorage).
- **Limitation:** Not updated for 2024/2025 tax years; community-driven, slow updates

#### IRS Free File Program (2026 Update)
- **AGI threshold raised to $89,000** for guided tax software eligibility
- Free File Fillable Forms still available for all income levels (no guidance)
- IRS partners include TaxSlayer, TaxAct, FreeTaxUSA, etc.
- **IRS Direct File** (the program we forked from): continuing to expand, but still limited to simple returns in select states
- **New for 2026:** IRS phasing out paper refund checks, pushing all taxpayers to electronic filing and direct deposit

### 1.2 What Users Actually Want (Sentiment Analysis)

Based on community sentiment from tax forums, review sites, and known pain points:

1. **"Just tell me what I owe / what I get back"** — Users want bottom-line answers fast, not 100+ screens of questions
2. **Document import that actually works** — Photo → data with high accuracy, no manual correction
3. **Tax optimization, not just filing** — "Am I leaving money on the table?" is the #1 question
4. **Year-round tax planning** — Not just Jan-April; estimated taxes, withholding adjustment
5. **Transparent pricing** — Fury at TurboTax's bait-and-switch pricing; willingness to pay fair price for transparent service
6. **Privacy** — Growing concern about sharing financial data; preference for local-first processing
7. **State tax integration** — Users hate having to pay extra for state filing
8. **Crypto/digital assets** — Massive confusion about reporting; willing to pay for clarity
9. **Amended returns** — Hate the complexity; want easy amendments
10. **Multi-year view** — "How does this decision affect next year's taxes?"

### 1.3 New IRS Rules for Tax Year 2025 (Filed in 2026)

The **One, Big, Beautiful Bill Act (OBBBA)**, signed July 4, 2025, is the biggest tax law change since TCJA 2017:

#### 🔴 Critical — Must Implement (Affects Our Engine)

| Provision | Details | Impact |
|-----------|---------|--------|
| **New Schedule 1-A** | Brand new schedule for OBBBA deductions | Must add new form/facts |
| **No Tax on Tips** | Up to $25K tip income deductible (2025-2028); phases out at AGI $150K/$300K | New deduction logic |
| **No Tax on Overtime** | Up to $12.5K/$25K overtime premium deductible (2025-2028); phases out at AGI $150K/$300K | New deduction logic |
| **No Tax on Car Loan Interest** | Up to $10K deductible for US-assembled cars (2025-2028); phases out at AGI $100K/$200K | New deduction logic |
| **Senior Deduction** | $6,000/person deduction for qualifying seniors, phases out at MAGI $75K (2025-2028) | New deduction + age check |
| **Enhanced Standard Deduction** | $31,500 MFJ / $23,625 HoH / $15,750 single (starting 2025) | Update constants |
| **Child Tax Credit** | Max increased to $2,200 in 2026, inflation-adjusted | Update CTC module |
| **SALT Cap Increase** | $40,000 for 2025, +1% annually through 2029; phases out at $500K+ income | Update SALT deduction |
| **Estate Tax Exemption** | $15M single / $30M joint (permanent) | Update estate module |
| **Itemized Deduction Cap** | Limited to 35 cents on dollar for top bracket taxpayers | New limitation logic |
| **Charitable Deduction Floor** | 0.5% floor on itemized charitable contributions | New floor logic |
| **Above-the-line Charitable** | $1,000/$2,000 permanent deduction even for non-itemizers | New deduction |
| **Form 1099-DA** | New form for digital asset broker transactions | Must parse new form |
| **1099-K Threshold** | Reverted to $20K + 200 transactions (not $600) | Update thresholds |
| **Trump Accounts** | New IRA-like accounts for children (trumpaccounts.gov) | Future feature |
| **EV Credit Repeal** | Several green energy credits repealed after 2025 | Remove/phase out credits |

#### Impact Assessment
- **P0:** Schedule 1-A, Standard Deduction update, SALT cap, CTC update, Senior deduction — these affect filing NOW
- **P1:** Tip/Overtime/Car loan deductions (large population), Charitable changes, 1099-DA
- **P2:** Estate tax update, Trump Accounts, EV credit removal

> ⚠️ **Critical:** Our Fact Graph engine forked from Direct File was built for pre-OBBBA law. Every module needs audit against the new provisions.

---

## 2. Document OCR/Parsing — Best Approaches

### 2.1 Provider Comparison

| Feature | Google Document AI | AWS Textract | Claude Vision | GPT-4o Vision | PaddleOCR 3.0 |
|---------|-------------------|-------------|--------------|----------------|---------------|
| **Type** | Cloud API | Cloud API | LLM Vision | LLM Vision | Open Source |
| **Tax Form Specialization** | W-2 parser ($0.30/doc) | Tax form examples in docs | General vision + reasoning | General vision + reasoning | General OCR, no tax-specific |
| **Accuracy (structured forms)** | ~95-98% on W-2s | ~95-97% | ~92-96% (reasoning helps) | ~91-95% | ~90-94% (text only) |
| **Key-Value Extraction** | Native (Form Parser) | Native (AnalyzeDocument) | Via prompt engineering | Via prompt engineering | Via PP-StructureV3 |
| **Pricing** | $0.30/W-2; $30/1K for Form Parser | $0.065/page (forms+tables) | ~$0.01-0.05/image (API) | ~$0.01-0.05/image (API) | Free (self-hosted) |
| **Handwriting** | Good | Good | Excellent | Good | Moderate |
| **Multi-language** | Yes | Yes | Yes | Yes | 100+ languages |
| **Latency** | ~1-3s | ~2-5s | ~3-10s | ~3-10s | ~0.5-2s (local) |
| **Privacy** | Cloud (Google stores data) | Cloud (AWS stores data) | Cloud (Anthropic) | Cloud (OpenAI) | Local (self-hosted) |

### 2.2 Recommended Approach: Hybrid Pipeline

**Best strategy: OCR layer + LLM extraction layer**

```
Photo/PDF → OCR Engine → Raw Text + Layout → LLM Extraction → Structured Data → Validation
```

1. **Primary OCR:** Google Document AI W-2 Parser for W-2s ($0.30/doc — purpose-built)
2. **Fallback OCR:** AWS Textract for other forms (1099s, K-1s) at $0.065/page
3. **LLM Extraction:** Claude Vision as the intelligence layer — takes OCR output + original image, extracts structured JSON with reasoning
4. **Validation:** Cross-check OCR output against LLM output; flag discrepancies for user review

**Why this hybrid approach:**
- OCR engines are fast and cheap for well-formatted forms
- LLM vision handles edge cases (handwritten notes, poor scans, unusual layouts)
- Cross-validation catches errors from either system
- Can fall back to LLM-only for forms without dedicated parsers

### 2.3 Open-Source Options

#### PaddleOCR 3.0 (January 2026 — Latest Release)
- **PaddleOCR-VL-1.5:** 0.9B parameter vision-language model achieving 94.5% on OmniDocBench v1.5
- Supports 111 languages, handles skew, warping, varied lighting
- PP-StructureV3 converts complex PDFs to Markdown/JSON preserving structure
- New MCP server integration for Claude Desktop
- **Best for:** Self-hosted OCR to avoid cloud costs, privacy-first approach
- **Limitation:** No tax-form-specific training; would need custom fine-tuning or LLM post-processing

#### Other Open Source
- **Tesseract 5:** Mature but lower accuracy than commercial offerings (~85-90% on forms)
- **EasyOCR:** Good for quick prototyping, supports 80+ languages
- **DocTR (doctr):** From Mindee, Apache 2.0, good on structured documents

### 2.4 Accuracy Considerations

Real-world accuracy on tax documents (community reports):
- **Clean digital PDF** (employer-generated): 98-99% with any OCR
- **Phone photo of W-2** (good lighting): 92-96% OCR, 96-99% with LLM post-processing
- **Phone photo (poor quality)**: 80-88% OCR, 90-95% with LLM correction
- **Handwritten portions**: 70-85% OCR, 85-92% with LLM
- **Key insight:** The difference-maker is the LLM validation/correction layer, not the raw OCR

### 2.5 Recommendation

| Priority | Action | Rationale |
|----------|--------|-----------|
| **P0** | Implement Claude Vision direct extraction for W-2, 1099 | We already use Claude; fastest to prototype; ~95%+ accuracy with good prompting |
| **P1** | Add Google Document AI W-2 parser as primary, Claude as validator | Better accuracy on standard W-2s; Claude catches edge cases |
| **P1** | Build validation pipeline with user confirmation step | No tax document should be filed without user confirming extracted values |
| **P2** | Evaluate PaddleOCR 3.0 for self-hosted option | Privacy-first alternative; needs testing on US tax forms |

---

## 3. Tax Optimization Engine Ideas

### 3.1 Optimization Strategies by Complexity

#### Tier 1: Low-Hanging Fruit (Auto-detect from return data) — P0

| Strategy | How It Works | Data Needed |
|----------|-------------|-------------|
| **Standard vs. Itemized Deduction** | Compare both, recommend higher | Schedule A data, standard deduction amount |
| **Filing Status Optimization** | MFS vs MFJ comparison for married couples | Both spouses' income data |
| **Dependent Credits** | Ensure all qualifying dependents claimed; CTC, ODC, EITC | Dependent info, income levels |
| **Education Credits** | AOC vs LLC comparison | 1098-T data |
| **HSA Contribution Check** | Flag if not maximizing HSA contributions | W-2 box 12 code W, HSA limits |
| **EITC Eligibility** | Many eligible taxpayers don't claim it | AGI, filing status, dependents |
| **Savers Credit** | Retirement savings credit for low-moderate income | AGI, retirement contributions |
| **Student Loan Interest** | Ensure 1098-E deduction taken | 1098-E data |

#### Tier 2: Investment Tax Optimization — P1

| Strategy | How It Works | Data Needed |
|----------|-------------|-------------|
| **Tax-Loss Harvesting Detection** | Analyze 1099-B for realized losses that offset gains; flag wash sale issues | 1099-B transactions |
| **Capital Gains Holding Period** | Flag short-term gains that could have been long-term with minor holding change | 1099-B with dates |
| **Qualified Dividend Optimization** | Ensure qualified dividends get preferential rate | 1099-DIV box 1b |
| **NII Tax (3.8%) Threshold Alert** | Alert when approaching MAGI threshold for Net Investment Income Tax | Total income + investment income |
| **Asset Location Advice** | Recommend which investments should be in tax-advantaged vs taxable accounts | Full portfolio + account type info |

#### Tier 3: Advanced Planning — P1/P2

| Strategy | How It Works | Data Needed |
|----------|-------------|-------------|
| **Roth Conversion Analysis** | Model optimal conversion amount based on current/future tax brackets | Current income, IRA balances, projected retirement income |
| **Charitable Bunching** | Model bunching deductions in alternate years vs. annual giving | Charitable giving history, standard deduction threshold |
| **Retirement Contribution Optimization** | 401(k) vs Roth 401(k) vs IRA vs backdoor Roth | Income, employer plan details, existing balances |
| **AMT Planning** | Predict AMT liability; optimize ISO exercise timing | ISOs, AMT preferences, regular tax |
| **Estimated Tax Optimization** | Annualized income installment method to minimize quarterly payments | Projected quarterly income |
| **QBI Deduction Optimization** | Optimize Section 199A deduction for pass-through income | Qualified business income, W-2 wages, UBIA |
| **SALT Cap Workaround** | PTE (pass-through entity) election where available | State-specific PTE rules |

#### Tier 4: OBBBA-Specific New Opportunities — P0

| Strategy | How It Works | Data Needed |
|----------|-------------|-------------|
| **Tip Income Deduction** | Verify if in qualifying tipped industry; calculate deduction | Occupation, tip income, AGI |
| **Overtime Deduction** | Calculate deductible overtime premium | W-2 overtime data, AGI |
| **Car Loan Interest Deduction** | Check vehicle assembly location; calculate deduction | Loan interest, vehicle info, AGI |
| **Senior Deduction** | Verify age qualification; apply $6,000 deduction | Age, MAGI |
| **Enhanced SALT Strategy** | With $40K cap, re-evaluate itemize vs. standard | SALT taxes, new cap |

### 3.2 Tax Planning APIs & Tools

| Tool | Type | Use Case | Cost |
|------|------|----------|------|
| **Holistiplan** | SaaS for advisors | Tax return analysis, tax planning scenarios | ~$500/yr per advisor |
| **Income Lab** | Tax planning API | Retirement income projections with tax modeling | Enterprise pricing |
| **Covisum Tax Clarity** | Tax planning software | Side-by-side scenario comparison | ~$1,500/yr |
| **Open Tax Solver** | Open source (C) | Federal + state tax calculation | Free |
| **TAXSIM (NBER)** | Research API | Marginal tax rate calculations, policy modeling | Free for research |

### 3.3 Recommendation

| Priority | Action | Impact |
|----------|--------|--------|
| **P0** | Implement Tier 1 auto-detections (standard vs itemized, HSA max, EITC, dependents) | Immediately adds value for every user |
| **P0** | Implement OBBBA new deduction checks (tips, overtime, car loan, senior) | Required for 2025 returns |
| **P1** | Build tax-loss harvesting detector from 1099-B data | High value for investment-heavy users |
| **P1** | Build Roth conversion scenario modeler | Major planning feature differentiator |
| **P2** | Build charitable bunching calculator | Nice-to-have for itemizers |
| **P2** | Integrate NBER TAXSIM for marginal rate lookups | Useful for planning scenarios |

---

## 4. MeF E-Filing Alternatives

### 4.1 Current Landscape of E-Filing APIs

| Provider | Model | Status | Cost | Notes |
|----------|-------|--------|------|-------|
| **Column Tax** | Embedded white-label | Active, IRS authorized | Per-return pricing (varies) | UI-bundled; doesn't work for API-only; requires partnership |
| **Drake Software** | Desktop + API | Active, established | ~$400-1500/yr for software | Primarily for tax professionals; has XML generation |
| **TaxSlayer Pro** | Web-based for preparers | Active | Per-return pricing | Professional preparer focused |
| **CrossLink** | Professional tax software | Active | Enterprise pricing | MeF XML generation capability |
| **Wolters Kluwer CCH** | Enterprise tax platform | Active | Enterprise pricing | Full MeF integration |
| **UltraTax CS** | Thomson Reuters | Active | Enterprise pricing | Full MeF integration |
| **Free File Fillable Forms** | IRS direct | Active | Free | Very basic; no guidance; any income level |

### 4.2 Realistic E-Filing Paths

#### Path A: Partner with an ERO (Recommended for Year 1) — P0
- Find a licensed ERO (Electronic Return Originator) with EFIN willing to transmit on our behalf
- We generate the return data; they handle MeF XML submission
- **Timeline:** 1-3 months to establish partnership
- **Cost:** Per-return fee ($5-25/return)
- **Pros:** Fastest path; no EFIN needed; proven compliance
- **Cons:** Dependent on partner; revenue share; less control

#### Path B: Use Existing Software's API/SDK — P1
- Several professional tax software packages can accept data via import and generate MeF XML
- Drake Software has XML import capability
- CCH Axcess has API integration
- **Timeline:** 2-4 months for integration
- **Cost:** Software license + per-return
- **Pros:** Proven MeF compliance; handles edge cases
- **Cons:** Cost; complexity; not designed for consumer use

#### Path C: Get Our Own EFIN — P1 (Start Now, Use in Year 2+)
Based on IRS documentation:
1. **Application:** Via IRS e-services portal
2. **Requirements:**
   - Business entity (LLC/Corp with EIN)
   - Responsible Official(s) identified
   - Fingerprinting via IRS-authorized Livescan vendor (if not CPA/EA/Attorney)
   - Suitability check (credit, tax compliance, criminal background)
3. **Timeline:** Up to **45 days** from submission for IRS approval (could be faster)
4. **Cost:** **Free** — no fee for EFIN itself
5. **Additional requirements for software developers:**
   - Must pass IRS Assurance Testing System (ATS) testing
   - Submit test returns that pass IRS validation
   - Annual retesting for each tax year
   - Must comply with Publication 3112 requirements

**Revised assessment:** Getting an EFIN is simpler than initially thought (45 days, no fee). The hard part is passing ATS testing for your software to generate valid MeF XML. This requires:
- Implementing IRS MeF XML schemas correctly
- Passing all ATS test scenarios
- Maintaining compliance annually

#### Path D: IRS Free File Alliance Partnership — P2
- Could apply to join the Free File Alliance
- Requirements: Must offer free filing for taxpayers under AGI threshold ($89,000)
- **Pros:** IRS partnership, credibility, marketing on IRS.gov
- **Cons:** Must offer free tier; extensive compliance requirements; takes 1+ years

### 4.3 Recommendation

| Priority | Action | Timeline |
|----------|--------|----------|
| **P0** | Start EFIN application NOW (45 days, free, no downside) | Feb 2026 |
| **P0** | Research ERO partnership for Year 1 filing (fastest path to e-file) | Feb-Mar 2026 |
| **P1** | Begin MeF XML schema implementation alongside tax engine | Q1-Q2 2026 |
| **P1** | Identify and partner with a CPA/EA firm willing to be our ERO | Q1 2026 |
| **P2** | Evaluate Free File Alliance application for 2027 season | Q3 2026 |

---

## 5. Technical Improvements

### 5.1 Web UI Framework

| Framework | Pros | Cons | Best For |
|-----------|------|------|----------|
| **Streamlit** | Fastest to prototype; Python-native; good for data apps | Limited customization; slow for complex UIs; stateful model is weird | Quick MVP / internal testing |
| **Gradio** | Great for AI demos; chat interface built-in; Hugging Face ecosystem | Limited for production apps; not great for complex forms | AI chatbot prototype |
| **React (Next.js)** | Full control; best for production; component ecosystem; SSR | Higher dev effort; needs separate backend | Production consumer app |
| **React + shadcn/ui** | Beautiful defaults; accessible; copy-paste components | Need React expertise | Production with great UX |

**Recommendation:** **P1 — Start with Gradio for AI chat prototype → P0 for production: Next.js + shadcn/ui**

Rationale:
- Our core UX is conversational (chat-based), not form-based
- Gradio has excellent chat interface components and works well for AI prototypes
- For production, React gives full control over the tax filing experience
- Next.js provides SSR (important for SEO/performance), API routes, and great DX

### 5.2 Multi-Year Tax Planning

**Approach: Projection Engine**

```python
class TaxProjection:
    """Model projected taxes for 2026+ based on assumptions"""
    
    def project_year(self, base_year_data, year, assumptions):
        """
        Assumptions include:
        - Income growth rate
        - Inflation adjustments (IRS publishes these annually)
        - Known law changes (OBBBA provisions sunset dates)
        - Planned life changes (retirement, job change, etc.)
        """
        # Apply inflation adjustments to brackets, deductions
        # Apply income growth assumptions
        # Calculate projected tax under current law
        # Compare scenarios (Roth conversion, bunching, etc.)
```

Key features to model:
1. **OBBBA Sunset Tracking:** Several provisions expire after 2028 — model pre/post impact
2. **Bracket Creep Analysis:** Show inflation-adjusted bracket changes
3. **Roth Conversion Ladder:** Multi-year optimal conversion modeling
4. **Social Security Optimization:** When to claim (age 62 vs 67 vs 70) tax implications
5. **RMD Planning:** Required minimum distributions starting at 73/75

**Priority: P2** — Important but complex; implement after core filing works

### 5.3 State Tax Engine — Expansion Strategy

| Priority | States | Rationale |
|----------|--------|-----------|
| **Already Built** | Massachusetts | Jason's state; first user |
| **P1** | No-income-tax states (FL, TX, WA, NV, TN, WY, SD, AK, NH) | Easy — no state return needed (just federal); covers ~25% of US filers |
| **P1** | California | Largest state by filers; complex but high demand |
| **P1** | New York | Second-largest by revenue; NYC has additional city tax |
| **P2** | New Jersey, Connecticut, Illinois | High-income NE corridor states; common for MA workers |
| **P2** | Pennsylvania, Virginia, Maryland | DC metro area states; relatively simple flat tax (PA) |
| **P2** | Colorado, Washington (new CG tax) | Growing tech hubs |

**State tax engine architecture:**
- Each state as a separate module with its own fact graph
- Common interface: takes federal AGI + state adjustments → state tax liability
- Start with states that reference federal AGI (most states) vs. states with significant decoupling (CA, NY)

**Priority: P1** — No-income-tax state support is trivial and expands market 25%. California and New York should be next.

### 5.4 Crypto Tax Reporting

#### Why It's Worth Adding

The landscape has changed dramatically for tax year 2025:
- **New Form 1099-DA** (Digital Asset Proceeds from Broker Transactions) — first year brokers are REQUIRED to report
- Crypto exchanges (Coinbase, Kraken, etc.) now issuing 1099-DAs to IRS
- IRS digital asset question is mandatory on Form 1040
- Users must report: sales, exchanges, mining income, staking rewards, airdrops, DeFi transactions

#### Complexity Levels

| Level | Scenario | Difficulty |
|-------|----------|------------|
| **Easy** | Single exchange, few trades, 1099-DA provided | Parse 1099-DA → Form 8949 |
| **Medium** | Multiple exchanges, DeFi, cost basis reconciliation | Need transaction history imports |
| **Hard** | Cross-chain DeFi, liquidity pools, wrapped tokens, NFTs | Requires specialized engines |

#### Integration Options

| Tool | Type | What It Does | Cost |
|------|------|-------------|------|
| **CoinTracker** | SaaS | Transaction import, cost basis, Form 8949 generation | $59-199/yr |
| **CoinLedger** | SaaS | Similar to CoinTracker | $49-299/yr |
| **TaxBit** | Enterprise API | Crypto tax calculation engine (powers TurboTax crypto) | Enterprise pricing |
| **Koinly** | SaaS | International + US crypto tax | $49-279/yr |
| **ZenLedger** | SaaS | Crypto + DeFi tax | $49-399/yr |

#### Recommendation

| Priority | Action |
|----------|--------|
| **P1** | Support 1099-DA parsing → Form 8949 generation (simple case) |
| **P2** | Integrate with CoinTracker/CoinLedger API for complex crypto portfolios |
| **P2** | Build DeFi transaction analysis (if demand justifies) |

**Rationale:** 1099-DA is brand new and users are confused. Being good at parsing the new form + generating Form 8949 is a market differentiator. Complex DeFi tracking should leverage existing tools via API rather than building from scratch.

---

## 6. Priority Summary & Roadmap

### P0 — Critical / Do Now

| # | Item | Category | Est. Effort | Impact |
|---|------|----------|-------------|--------|
| 1 | **Update engine for OBBBA provisions** (Schedule 1-A, new deductions, SALT cap, CTC, standard deduction) | Engine | 2-3 weeks | Blocking — returns are wrong without this |
| 2 | **Start EFIN application** | E-Filing | 1 day + 45 day wait | Free; no downside; enables future e-filing |
| 3 | **Implement Claude Vision document extraction** for W-2 and 1099 | OCR | 1 week | Enables core document upload flow |
| 4 | **Find ERO partner for Year 1 e-filing** | E-Filing | 2-4 weeks outreach | Enables actual filing capability |
| 5 | **Auto-optimization checks** (standard vs itemized, EITC, HSA max, OBBBA deductions) | Optimization | 1-2 weeks | Core value prop — "AI finds savings" |

### P1 — Important / Next Quarter

| # | Item | Category | Est. Effort | Impact |
|---|------|----------|-------------|--------|
| 6 | Add Google Document AI as primary W-2 parser with Claude validation | OCR | 1 week | Better accuracy, hybrid approach |
| 7 | Build Gradio chat prototype for conversational filing | UI | 1-2 weeks | User-facing prototype |
| 8 | Support no-income-tax states (FL, TX, WA, etc.) | Engine | 1-2 days | +25% market coverage for free |
| 9 | Tax-loss harvesting detector from 1099-B data | Optimization | 1 week | High value for investors |
| 10 | Roth conversion scenario modeler | Optimization | 2 weeks | Major planning differentiator |
| 11 | 1099-DA / Form 8949 crypto reporting (simple) | Engine | 1-2 weeks | New form, market confusion = opportunity |
| 12 | California state tax module | Engine | 2-3 weeks | Largest state by filers |
| 13 | Begin MeF XML schema implementation | E-Filing | 4-6 weeks | Required for own EFIN |
| 14 | Production UI in Next.js + shadcn/ui | UI | 4-6 weeks | Production-ready consumer app |

### P2 — Future / Backlog

| # | Item | Category | Est. Effort | Impact |
|---|------|----------|-------------|--------|
| 15 | Multi-year tax projection engine | Optimization | 4-6 weeks | Advanced planning feature |
| 16 | Charitable bunching calculator | Optimization | 1 week | Nice-to-have for itemizers |
| 17 | PaddleOCR self-hosted evaluation | OCR | 1-2 weeks | Privacy-first option |
| 18 | New York state tax module | Engine | 2-3 weeks | Second-largest state |
| 19 | CoinTracker/CoinLedger API integration | Crypto | 2 weeks | Complex crypto support |
| 20 | Free File Alliance application | E-Filing | Ongoing | 2027 filing season |
| 21 | Amended return support (Form 1040-X) | Engine | 2-3 weeks | User-requested feature |
| 22 | Crypto DeFi transaction analysis | Engine | 4+ weeks | Niche but growing |

### Immediate Next Steps (This Week)

1. ⚡ **File EFIN application** — it's free, takes 1 day to submit, 45 days to process
2. ⚡ **Audit every fact/module against OBBBA** — create checklist of what needs updating
3. ⚡ **Prototype Claude Vision W-2 extraction** — take a photo of a W-2, extract to JSON
4. 📞 **Start reaching out to ERO/CPA partners** for e-filing partnership
5. 📝 **Track OBBBA sunset dates** — several provisions expire 2028, need timeline tracking

---

## Appendix: Key Sources

- IRS 2026 Filing Season Announcement: https://www.irs.gov/newsroom/irs-opens-2026-filing-season
- OBBBA Provisions: https://www.irs.gov/newsroom/one-big-beautiful-bill-provisions
- Tax Foundation OBBBA Analysis: https://taxfoundation.org/research/all/federal/big-beautiful-bill-senate-gop-tax-plan/
- EFIN Application: https://www.irs.gov/e-file-providers/become-an-authorized-e-file-provider
- IRS Free File: https://www.irs.gov/e-file-do-your-taxes-for-free
- Column Tax Platform: https://www.columntax.com/platform
- Keeper Tax: https://www.keepertax.com
- UsTaxes Open Source: https://github.com/ustaxes/UsTaxes
- PaddleOCR 3.0: https://github.com/PaddlePaddle/PaddleOCR
- Google Document AI Pricing: https://cloud.google.com/document-ai/pricing
- AWS Textract Pricing: https://aws.amazon.com/textract/pricing/
- IRS Digital Assets: https://www.irs.gov/filing/digital-assets
- Form 1099-DA: https://www.irs.gov/businesses/understanding-your-form-1099-da
