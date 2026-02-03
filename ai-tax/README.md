# AI Tax — AI-Powered Tax Preparation

An AI-powered tax preparation system that aims to simplify tax filing through document parsing, conversational UI, and proactive tax optimization.

## Vision

Make tax filing as simple as having a conversation — upload your documents, answer a few questions, file electronically.

## Architecture

```
┌─────────────────────────────────────────────┐
│                   User Interface             │
│         (Conversational / Chat-based)        │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│              AI Orchestrator                 │
│  - Document parsing (OCR + LLM extraction)  │
│  - Conversational interview engine          │
│  - Tax optimization suggestions             │
│  - Error detection & validation             │
└──────────┬───────────────┬──────────────────┘
           │               │
┌──────────▼─────┐  ┌──────▼──────────────────┐
│  Tax Engine    │  │  Document Parser         │
│  (Calculation) │  │  (W-2, 1099, K-1, etc.) │
│                │  │                          │
│  Option A:     │  │  - Cloud OCR APIs        │
│  Column Tax    │  │  - LLM extraction        │
│  White-label   │  │  - Validation layer      │
│                │  │                          │
│  Option B:     │  │                          │
│  Custom engine │  │                          │
│  (Direct File  │  │                          │
│   reference)   │  │                          │
└──────────┬─────┘  └──────────────────────────┘
           │
┌──────────▼──────────────────────────────────┐
│           IRS MeF E-Filing                   │
│  - XML schema generation                    │
│  - A2A transmission                         │
│  - Acknowledgement handling                 │
└─────────────────────────────────────────────┘
```

## Project Structure

```
ai-tax/
├── README.md              # This file
├── STATUS.md              # Project status (source of truth)
├── config/                # Configuration files
├── docs/                  # Documentation
├── research/              # Research reports
├── src/
│   ├── core/              # Tax calculation engine & data models
│   ├── api/               # API layer (Column Tax integration or custom)
│   ├── parsers/           # Document parsing (W-2, 1099, etc.)
│   └── ui/                # Conversational UI / interview engine
└── tests/                 # Test suite
```

## Tech Stack (Planned)

- **Language:** Python 3.12+
- **Tax Engine:** Column Tax API (Year 1) → Custom engine (Year 2+)
- **Document Parsing:** Google Cloud Document AI / AWS Textract
- **AI/LLM:** Claude API for conversational interface + optimization
- **E-Filing:** IRS MeF A2A (when ready for direct filing)
- **Security:** AES-256 encryption, SOC 2 practices from day 1

## Current Phase: Planning & Architecture

See STATUS.md for current progress and next steps.
