"""
TaxForge CLI - Launch the tax preparation app
"""
import subprocess
import sys
import os
import shutil
from pathlib import Path


__version__ = "0.9.31"

RXCONFIG_CONTENT = '''"""Reflex config for TaxForge."""
import reflex as rx

config = rx.Config(
    app_name="aitax",
    plugins=[]
)
'''


def setup_app_dir() -> Path:
    """Create app directory with necessary files."""
    # Use ~/.taxforge as the app directory
    app_dir = Path.home() / ".taxforge"
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


def main():
    """Main entry point for taxforge command."""
    args = sys.argv[1:]
    
    if args and args[0] in ("--version", "-v"):
        print(f"TaxForge v{__version__}")
        return 0
    
    if args and args[0] in ("--help", "-h"):
        print(f"""TaxForge v{__version__} - AI-powered tax preparation

Usage:
  taxforge [run]     Launch the web UI (default)
  taxforge --version Show version
  taxforge --help    Show this help
  taxforge --reset   Reset app directory (clear cache)

After running, open http://localhost:3000 in your browser.
Go to Settings to configure your Gemini API key first.
""")
        return 0
    
    if args and args[0] == "--reset":
        app_dir = Path.home() / ".taxforge"
        if app_dir.exists():
            shutil.rmtree(app_dir)
            print(f"✓ Removed {app_dir}")
        return 0
    
    # Setup app directory
    print(f"🔨 TaxForge v{__version__}")
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
        print("\n👋 TaxForge stopped")
        return 0
    except FileNotFoundError:
        print("Error: Reflex not installed. Run: pip install reflex")
        return 1


if __name__ == "__main__":
    sys.exit(main())
