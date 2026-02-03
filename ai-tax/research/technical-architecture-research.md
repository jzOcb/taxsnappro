# AI Tax Project — Technical Architecture Research
**Date:** 2026-02-03
**Status:** Initial Research Complete

---

## Part 1: Column Tax API Research

### Overview
Column Tax (columntax.com) is the **first IRS-authorized API-first tax filing product**. They provide white-label, embedded tax filing solutions designed primarily for fintech companies, neobanks, and financial apps.

### Business Model
- **B2B2C embedded model** — Column Tax embeds inside partner apps (banks, fintechs)
- **Revenue share / per-filing pricing** — exact pricing not public, requires sales demo
- **No public API docs** — all integration is gated behind a sales/partnership process
- **Contact:** Sales inquiry form at columntax.com/contact-us (no self-serve signup)

### Key Product Features
| Feature | Details |
|---------|---------|
| **White-label UI** | Pre-built UI that can be embedded in partner apps, mobile + desktop optimized |
| **Pre-filling** | Ingests partner data (bank transactions, W-2s, etc.) to pre-populate returns |
| **Expert Review** | Premium upsell — CPA reviews returns before filing (53% of taxpayers still use CPAs) |
| **Customer Support** | Column handles all tax-related CS, can integrate into partner's support platform |
| **Guarantees** | Max Refund Guarantee, Accuracy Guarantee, Audit Assistance included |
| **Compliance** | "Compliance in a box" — IRS compliance handled by Column |

### Integration Architecture
Based on marketing materials (no public developer docs available):

```
Partner App (Your App)
    ↓ embed (iframe / SDK / "few lines of code")
Column Tax White-Label UI
    ↓ API calls
Column Tax Backend
    ↓ MeF submission
IRS e-File System
```

**Key integration claims:**
- "Zero to accepted returns in one week or less"
- "Just a few lines of code" to integrate
- IRS Authorized e-File Provider
- SOC 2 certified, bank-grade encryption
- 99.999%+ historical uptime

### Business Metrics (from their site)
- 99% of tax refunds deposited to embedded partners' accounts
- 10-25% of users switch direct deposits after filing
- 20-35% higher customer retention for partners
- Partners include: **MoneyLion** (confirmed), likely others in fintech space

### Known Clients / Partners
- MoneyLion (CMO quoted on site)
- Targeting: banks, neobanks, payroll companies, gig economy platforms, budgeting tools

### What We Can't Determine Without Sales Contact
- ❌ Actual API endpoint documentation
- ❌ Pricing per filing / revenue share model
- ❌ Supported tax forms (likely W-2, 1099 variants, but specifics unknown)
- ❌ State filing support
- ❌ SDK/iframe technical details
- ❌ Data formats (JSON? XML?)
- ❌ Onboarding requirements (EFIN needed? MeF credentials?)

### Assessment for AI Tax Project
**Pros:**
- Fastest path to market — could integrate in ~1 week
- Compliance/IRS authorization handled
- Built-in guarantees reduce liability
- Customer support included

**Cons:**
- Black box — no public API docs, no transparency
- Revenue share likely eats into margins significantly
- No AI/LLM integration surface — their UI is fixed
- Can't differentiate on the tax engine itself
- Complete dependency on a third party
- Not clear if they support our target use case (AI-guided filing vs traditional interview)

**Verdict:** Column Tax is a **competitor/reference point**, not an integration partner for an AI-first approach. Their model assumes the partner just embeds their UI. An AI Tax product that wants to fundamentally reimagine the filing experience would conflict with Column's white-label approach. However, studying their "pre-filling" approach and "compliance in a box" claims is valuable for understanding what the market expects.

---

## Part 2: IRS Direct File Open Source Code Research

### Repository Overview
- **URL:** https://github.com/IRS-Public/direct-file
- **License:** Public domain (federal government work)
- **Tax Year:** 2024 (current as of release)
- **Legal basis:** Source Code SHARE Act of 2024 (Public Law 118-187)
- **Developed by:** IRS in-house team + USDS + GSA + vendors (TrussWorks, Coforma, ATI)

### Repository Structure

```
direct-file/
├── README.md
├── ONBOARDING.md
├── LICENSE
├── docs/
│   ├── adr/                    # Architecture Decision Records (gold mine!)
│   │   ├── adr-fact-modules.md
│   │   ├── adr-fact-dictionary-tests.md
│   │   ├── adr-frontend-client.md
│   │   ├── adr-language.md
│   │   ├── 2023-08-21_encrypting-taxpayer-artifacts.md
│   │   └── ...
│   ├── design/
│   ├── engineering/
│   ├── product/
│   ├── rfc/
│   └── testing/
└── direct-file/
    ├── fact-graph-scala/       # ⭐ The crown jewel — tax rules engine
    │   ├── shared/             # Cross-platform Scala code
    │   ├── js/                 # Scala.js transpilation target
    │   ├── jvm/                # JVM-specific code
    │   └── build.sbt           # SBT build config
    ├── js-factgraph-scala/     # JS bridge for frontend
    ├── backend/                # Java/Spring Boot API server
    ├── df-client/              # React frontend
    ├── submit/                 # MeF submission service
    ├── status/                 # MeF status polling service
    ├── email-service/          # SMTP relay
    ├── state-api/              # State tax data transfer API
    ├── libs/                   # Shared dependencies
    ├── config/
    ├── monitoring/             # OpenTelemetry + Prometheus + Grafana
    └── docker-compose.yaml     # Full local dev environment
```

### The Fact Graph Engine (Most Important Component)

#### Architecture
The Fact Graph is a **declarative, XML-based knowledge graph** that reasons about incomplete information (partially completed tax returns). Think of it like a spreadsheet:

- **Writable Facts:** User-entered data (name, income, etc.)
- **Derived Facts:** Calculated values based on other facts (AGI, tax owed, etc.)
- **Modules:** Logical groupings (EITC, spouse info, deductions, etc.)

#### Technical Stack
```
Language: Scala 3.3.3
Build: SBT
Platforms: 
  - JVM (backend, Java 21)
  - JavaScript (frontend, via Scala.js transpilation)
Output: ~1MB CommonJS module (closure-compiled from ~4MB ESModules)
Dependencies:
  - scala-java-time (date handling, ~200KB)
  - upickle 3.1.0 (JSON serialization)
  - scalatest 3.2.15 (testing)
```

#### Fact Dictionary XML Format
Facts are defined in XML modules. Example from the ADR:

```xml
<!-- spouse.xml -->
<Fact path="/writableLivedApartAllYear">
  <Name>Writable lived apart from spouse the whole year</Name>
  <Writable>
    <Boolean />
  </Writable>
</Fact>

<Fact path="/livedApartAllYear">
  <Name>Lived apart from spouse the whole year</Name>
  <Export downstreamFacts="true" />
  <Derived>
    <All>
      <Dependency path="/writableLivedApartAllYear" />
      <Dependency path="/livedApartLastSixMonths" />
    </All>
  </Derived>
</Fact>

<!-- eitc.xml — cross-module dependency -->
<Fact path="/eligibleForEitc">
  <Dependency module="spouse" path="/livedApartAllYear" />
</Fact>
```

#### Module System
As of late 2023, the fact dictionary was refactored from a monolithic file into **modules**:
- Each module = one XML file (e.g., `eitc.xml`, `spouse.xml`)
- Facts are **private by default** within their module
- Facts can be **exported** for `downstreamFacts` or `mef` use
- Build-time checks prevent cross-module private fact access
- At the time of the ADR: **451 derived facts + 261 writable facts** = 712 total

#### How the Fact Graph Runs on Frontend
```
Scala source code
    ↓ sbt fastOptJS / fullOptJS
Transpiled JavaScript (CommonJS, ~1MB)
    ↓ npm run copy-transpiled-js  
df-client React app (loaded in browser)
    ↓ debugFactGraphScala.* (browser console API)
Live tax calculation in-browser
```

**Key insight:** The fact graph runs **both** on the server (JVM) and in the browser (JS). This means tax calculations happen client-side for responsiveness, with server-side validation.

### What's Included vs. Stripped Out

#### ✅ INCLUDED (reusable)
- **Fact Graph engine** — the complete Scala rules engine
- **Fact Dictionary XML** — all tax rules as declarative XML (TY2024)
- **Test cases and scenarios** — validated against IRS Office of Chief Counsel
- **Frontend React app** — interview-based UI flow
- **Backend API** — Spring Boot Java services
- **State API** — for transferring federal return data to state systems
- **Docker Compose** — full local dev environment
- **Architecture Decision Records** — detailed reasoning for all major decisions
- **MeF submission/status services** — code structure (but credentials stripped)

#### ❌ EXEMPTED (stripped out)
- **PII (Personally Identifiable Information)** — any real taxpayer data
- **FTI (Federal Tax Information)** — protected tax data
- **SBU (Sensitive But Unclassified)** — security-sensitive code
- **NSS code** — National Security Systems components
- **MeF credentials** — EFIN, ETIN, ASID, keystore files (replaced with placeholders)
- **TIN validation service** — can be disabled (`DF_TIN_VALIDATION_ENABLED=false`)
- **Email validation service** — can be disabled (`DF_EMAIL_VALIDATION_ENABLED=false`)
- **Authentication provider integration** — replaced with CSP simulator for local dev

### MeF Integration Architecture

#### How MeF Works in the Codebase

```
User completes return (Fact Graph)
    ↓ 
Backend API serializes to MeF XML format
    ↓
direct-file/submit/ service
    ↓ SOAP/XML via MeF API
IRS Modernized e-File (MeF) system
    ↓ acknowledgement
direct-file/status/ service (polls for ACK)
    ↓
Email notification to taxpayer
```

**Key MeF integration details:**
- Submit and Status are **separate Spring Boot services** (not in default docker-compose)
- Requires MeF credentials: `MEF_SOFTWARE_ID`, `STATUS_ASID`, `STATUS_EFIN`, `STATUS_ETIN`
- Uses keystore for authentication: `STATUS_KEYSTOREALIAS`, `STATUS_KEYSTOREBASE64`, `STATUS_KEYSTOREPASSWORD`
- MeF Software Version: `2023.0.1` (in example config)
- Submit service uses `SUBMIT_ID_VAR_CHARS="zz"` for test submissions
- MeF is a **public API** available to authorized e-file providers

**To become an authorized e-file provider:**
1. Apply for EFIN (Electronic Filing Identification Number) from IRS
2. Pass suitability checks
3. Get MeF Software ID approved
4. Obtain digital certificate for keystore
5. Pass IRS Assurance Testing System (ATS) — test submissions

### What We Can Realistically Reuse

#### 🟢 HIGH VALUE — Direct Reuse
1. **Fact Graph Engine (Scala)**
   - The entire rules engine is domain-agnostic
   - Can define our own fact dictionaries
   - Already handles incomplete information (perfect for AI-guided partial filing)
   - Runs on both JVM and browser via Scala.js
   - **Effort:** Medium — need Scala/SBT expertise

2. **Tax Rules / Fact Dictionary XML**
   - 712+ facts covering federal tax law for TY2024
   - Validated by IRS Office of Chief Counsel
   - Modular structure allows selective use
   - **Effort:** Low to reference, medium to adapt

3. **Architecture Decision Records**
   - Invaluable documentation of design choices
   - Module system, testing strategies, encryption approaches
   - **Effort:** Just reading

4. **Test Cases / Scenarios**
   - IRS-validated test scenarios
   - Can use as golden test suite for our own engine
   - **Effort:** Low

#### 🟡 MEDIUM VALUE — Partial Reuse
5. **MeF Integration Code (submit/status)**
   - Shows exact MeF XML format and submission flow
   - We'd need our own EFIN/credentials
   - Code is there but stripped of auth — need to rebuild auth layer
   - **Effort:** High — need IRS authorization process

6. **State API Design**
   - Shows how to transfer federal data to state systems
   - JSON + MeF XML dual format approach
   - **Effort:** Medium

7. **Frontend Interview Flow**
   - React-based, mobile-first design
   - Shows how to map Fact Graph to UI questions
   - We'd replace with AI conversation, but flow logic is reusable
   - **Effort:** Medium to adapt

#### 🔴 LOW VALUE — Reference Only
8. **Backend API (Spring Boot/Java)**
   - Monolithic, tightly coupled to their auth system
   - We'd likely use a different tech stack
   - **Effort:** High to adapt, better to rewrite

9. **Authentication / CSP Integration**
   - Specific to IRS's identity provider (ID.me/Login.gov)
   - Not applicable to our auth model
   - **Effort:** N/A

---

## Part 3: Actionable Conclusions

### Recommended Architecture Strategy

```
┌──────────────────────────────────────────────┐
│              AI Tax Architecture             │
├──────────────────────────────────────────────┤
│                                              │
│  AI Conversation Layer (LLM)                 │
│  - Natural language tax interview            │
│  - Replaces traditional Q&A flow             │
│  - Maps user responses to Fact Graph inputs  │
│                                              │
│  ┌────────────────────────────────────────┐   │
│  │  Fact Graph Engine (from Direct File)  │   │
│  │  - Scala rules engine (reused)        │   │
│  │  - Tax law XML definitions (adapted)  │   │
│  │  - Completeness tracking              │   │
│  │  - Runs in-browser via Scala.js       │   │
│  └────────────────────────────────────────┘   │
│                                              │
│  MeF Submission Layer                        │
│  - Option A: Own EFIN (6-12 month process)   │
│  - Option B: Partner with e-file provider    │
│  - Option C: Initially generate PDF only     │
│                                              │
│  Compliance & Review                         │
│  - Accuracy validation (from Fact Graph)     │
│  - Optional CPA review (like Column Tax)     │
│  - Audit trail / explainability              │
│                                              │
└──────────────────────────────────────────────┘
```

### Key Technical Decisions Needed

1. **Fact Graph adoption:** Fork Direct File's Scala Fact Graph, or reimplement in Python/TypeScript?
   - **Recommendation:** Fork the Scala engine. It's battle-tested at IRS scale, handles incomplete info natively, and the modular XML fact definitions are clean. The Scala.js transpilation is a unique advantage for client-side tax calculation.

2. **MeF filing strategy:** Getting an EFIN takes months.
   - **Recommendation:** Phase 1 — generate MeF XML locally, let users file via Free File/IRS. Phase 2 — partner with existing e-file provider. Phase 3 — own EFIN.

3. **Column Tax as alternative:** Use their API instead of building?
   - **Recommendation:** No — their model is white-label UI embedding, incompatible with AI-first approach. But study their UX patterns and compliance model.

4. **AI integration point:** Where does the LLM sit?
   - **Recommendation:** The LLM replaces the static interview flow (df-client). It reads the Fact Graph state, determines what info is missing, and asks natural language questions. The Fact Graph remains the source of truth for tax calculations.

### Immediate Next Steps

1. **Clone and run Direct File locally** — `docker compose up -d --build` 
2. **Study the Fact Graph XML modules** — understand the tax rules format
3. **Prototype LLM ↔ Fact Graph integration** — can an LLM read fact graph state and generate appropriate questions?
4. **Research EFIN application process** — start the 6-12 month timeline early
5. **Contact Column Tax for competitive intelligence** — understand their pricing model even if we don't integrate

### Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Direct File repo becomes unmaintained (political risk under current administration) | High | Fork immediately, maintain independently |
| EFIN application rejected or delayed | Medium | Partner with existing provider as backup |
| Fact Graph too complex to integrate with LLM | Medium | Prototype early, consider simpler subset |
| Tax law changes break forked rules | Medium | Annual update cycle, track IRS publications |
| Liability for incorrect AI-guided returns | High | Accuracy guarantees, CPA review option, clear disclaimers |
