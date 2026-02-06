# Publishing TaxForge to PyPI

## One-time setup

1. **Create PyPI account**
   - Go to https://pypi.org/account/register/
   - Verify email
   - Enable 2FA (required for new accounts)

2. **Create API token**
   - Go to https://pypi.org/manage/account/token/
   - Create token with scope "Entire account" (first upload) or "taxforge" (after first upload)
   - Save the token somewhere safe (starts with `pypi-`)

## Build and upload

```bash
cd ~/Downloads/ai-tax

# Install build tools
pip install build twine

# Build the package
python -m build

# This creates:
#   dist/taxforge-0.9.0-py3-none-any.whl
#   dist/taxforge-0.9.0.tar.gz

# Upload to PyPI
twine upload dist/*
# Enter username: __token__
# Enter password: pypi-YOUR_API_TOKEN
```

## After publishing

Users can install with:
```bash
pip install taxforge
taxforge
# Opens http://localhost:3000
```

## Updating

1. Edit version in:
   - `pyproject.toml` (version = "X.Y.Z")
   - `ui/aitax/__init__.py` (__version__)
   - `ui/aitax/cli.py` (__version__)

2. Rebuild and upload:
```bash
rm -rf dist/
python -m build
twine upload dist/*
```

Users update with:
```bash
pip install --upgrade taxforge
```

## Version scheme

- 0.9.x = Beta (current)
- 1.0.0 = First stable release
- Bump patch (0.9.1) for bug fixes
- Bump minor (0.10.0) for new features
