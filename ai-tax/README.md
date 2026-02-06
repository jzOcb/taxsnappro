# TaxSnapPro 🧾

AI-powered tax preparation tool. Upload your tax documents, let AI extract the data, and get instant tax calculations.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![PyPI](https://img.shields.io/pypi/v/taxsnappro.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## Features

- 📄 **Document Upload** - Drag & drop W-2, 1099, 1098, 5498-SA forms (PDF/images)
- 🤖 **AI Extraction** - Gemini 2.0 Flash automatically extracts all tax data
- ✏️ **Manual Entry** - Add rental properties, business income, dependents
- 📊 **Real-time Calculation** - See tax estimates update as you add data
- ☑️ **Include/Exclude** - Toggle documents to compare different scenarios
- 🎯 **Accuracy** - Validated against CPA returns (0.05% difference)

## Supported Forms

| Form | Description |
|------|-------------|
| W-2 | Wages and Tax Statement |
| 1099-INT | Interest Income |
| 1099-DIV | Dividend Income |
| 1099-B | Capital Gains |
| 1099-NEC | Nonemployee Compensation |
| 1099-MISC | Miscellaneous Income |
| 1098 | Mortgage Interest |
| 5498-SA | HSA Contributions |

## Quick Start

```bash
# Install
pip install taxsnappro

# Run
taxsnappro
```

Then open http://localhost:3000 in your browser.

## Requirements

- Python 3.10+
- [Gemini API Key](https://aistudio.google.com/apikey) (free tier: 1500 requests/day)

## Configuration

1. Launch TaxSnapPro: `taxsnappro`
2. Go to **Settings**
3. Enter your Gemini API key
4. Start uploading documents!

## How It Works

1. **Upload** - Drop your tax documents on the Upload page
2. **Process** - Select files and click "AI Process" to extract data
3. **Review** - Check extracted data, toggle documents to include/exclude
4. **Calculate** - See real-time tax calculations based on included documents

## Tax Calculations

TaxSnapPro calculates:
- Federal income tax (all brackets for 2024)
- Standard vs. Itemized deductions
- Self-employment tax (Schedule SE)
- Child Tax Credit / Other Dependent Credit
- Additional Medicare Tax (0.9%)
- Net Investment Income Tax (3.8%)
- Capital gains tax (0%, 15%, 20% tiers)
- HSA deductions
- SALT cap ($10,000)

## Privacy & Security

- All data stays on your local machine
- Documents are processed via Gemini API (encrypted)
- No data is stored on any server
- API keys are stored locally with encryption

## Development

```bash
# Clone
git clone https://github.com/jzOcb/taxsnappro.git
cd taxsnappro

# Install dependencies
pip install -e .

# Run in development mode
cd ui && reflex run
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Disclaimer

TaxSnapPro is for educational and estimation purposes only. Always consult a qualified tax professional for official tax filing. The authors are not responsible for any errors in tax calculations.
