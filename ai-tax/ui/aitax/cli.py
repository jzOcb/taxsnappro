"""
TaxSnapPro CLI - Launch the tax preparation app
"""
import subprocess
import sys
import os
import shutil
from pathlib import Path


__version__ = "1.1.0"

RXCONFIG_CONTENT = '''"""Reflex config for TaxSnapPro."""
import reflex as rx

config = rx.Config(
    app_name="aitax",
    plugins=[]
)
'''


def setup_app_dir() -> Path:
    """Create app directory with necessary files."""
    # Use ~/.taxsnappro as the app directory
    app_dir = Path.home() / ".taxsnappro"
    app_dir.mkdir(exist_ok=True)
    
    # Create rxconfig.py
    rxconfig = app_dir / "rxconfig.py"
    if not rxconfig.exists():
        rxconfig.write_text(RXCONFIG_CONTENT)
    
    # Create aitax package symlink/copy
    aitax_dir = app_dir / "aitax"
    if not aitax_dir.exists():
        # Get the installed package location
        import aitax
        src_dir = Path(aitax.__file__).parent
        # Copy the package files
        shutil.copytree(src_dir, aitax_dir)
    
    return app_dir


def upgrade():
    """Upgrade TaxSnapPro to the latest version."""
    print("🔄 Checking for updates...")
    
    # Get current version
    current = __version__
    
    # Clear pip cache and upgrade
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "--no-cache-dir", "taxsnappro"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"❌ Upgrade failed: {result.stderr}")
        return 1
    
    # Clear cached app directory so new code gets loaded
    app_dir = Path.home() / ".taxsnappro"
    aitax_dir = app_dir / "aitax"
    if aitax_dir.exists():
        shutil.rmtree(aitax_dir)
    
    # Get new version from fresh subprocess (avoids module cache)
    result = subprocess.run(
        [sys.executable, "-c", "import importlib.util; spec = importlib.util.find_spec('aitax'); import aitax; print(aitax.__version__)"],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    )
    new_version = result.stdout.strip() if result.returncode == 0 else "unknown"
    
    if new_version == current:
        print(f"✅ Already on latest version (v{current})")
    else:
        print(f"✅ Upgraded: v{current} → v{new_version}")
    print("   Run 'taxsnappro' to start with the new version")
    return 0


def main():
    """Main entry point for taxsnappro command."""
    args = sys.argv[1:]
    
    if args and args[0] in ("--version", "-v"):
        print(f"TaxSnapPro v{__version__}")
        return 0
    
    if args and args[0] in ("--help", "-h"):
        print(f"""TaxSnapPro v{__version__} - AI-powered tax preparation

Usage:
  taxsnappro [run]     Launch the web UI (default)
  taxsnappro upgrade   Check for and install updates
  taxsnappro --version Show version
  taxsnappro --help    Show this help
  taxsnappro --reset   Reset app directory (clear cache)

After running, open http://localhost:3000 in your browser.
Go to Settings to configure your Gemini API key first.
""")
        return 0
    
    if args and args[0] == "upgrade":
        return upgrade()
    
    if args and args[0] == "--reset":
        app_dir = Path.home() / ".taxsnappro"
        if app_dir.exists():
            shutil.rmtree(app_dir)
            print(f"✓ Removed {app_dir}")
        return 0
    
    # Setup app directory
    print(f"🔨 TaxSnapPro v{__version__}")
    print("   Setting up app directory...")
    
    try:
        app_dir = setup_app_dir()
    except Exception as e:
        print(f"Error setting up app: {e}")
        return 1
    
    print(f"   Directory: {app_dir}")
    print(f"   Open http://localhost:3000 after startup")
    print()
    
    os.chdir(app_dir)
    
    # Run reflex
    try:
        result = subprocess.run(
            [sys.executable, "-m", "reflex", "run"],
            cwd=app_dir,
        )
        return result.returncode
    except KeyboardInterrupt:
        print("\n👋 TaxSnapPro stopped")
        return 0
    except FileNotFoundError:
        print("Error: Reflex not installed. Run: pip install reflex")
        return 1


if __name__ == "__main__":
    sys.exit(main())
