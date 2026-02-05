# AI Tax UI

Mercury-style dark theme UI for AI Tax.

## Quick Start

```bash
# Install dependencies
pip install reflex

# Navigate to UI directory
cd ai-tax/ui

# Initialize (first time only)
reflex init

# Run development server
reflex run

# Open http://localhost:3000
```

## Features

- **Dashboard** - Overview of tax data, stats, and documents
- **Upload** - Drag & drop tax documents (W-2, 1099, etc.)
- **Review** - Edit and verify extracted tax data
- **Settings** - API keys, filing options, data management

## Design

Inspired by Mercury (mercury.com):
- Dark slate/navy background
- Gradient accent buttons (blue → purple)
- Glass card effects
- Inter font family
- Clean, minimal interface

## Structure

```
ui/
├── aitax/
│   ├── __init__.py
│   ├── aitax.py       # Main app and pages
│   ├── state.py       # Application state
│   └── components.py  # Reusable UI components
├── rxconfig.py        # Reflex configuration
├── preview.html       # Static HTML preview
└── README.md
```

## Integration

The UI integrates with the ai-tax backend:
- `src/core/tax_engine.py` - Tax calculations
- `src/core/fact_graph.py` - IRS Fact Graph
- `src/parsers/` - Document parsing

## Requirements

- Python 3.10+
- Reflex 0.8+
- Node.js 18+ (for Reflex frontend)
