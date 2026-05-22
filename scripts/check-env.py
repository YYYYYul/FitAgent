#!/usr/bin/env python
"""
FitAgent Environment Check — verifies local setup before first run.

Usage:
  python scripts/check-env.py        # from project root

Checks Python, Node, DB, config, ports and prints a summary with
actionable next steps. This script does NOT modify anything.
"""

import os
import sys
import subprocess
import platform

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")
ENV_FILE = os.path.join(BACKEND_DIR, ".env")
DB_FILE = os.path.join(BACKEND_DIR, "fitagent.db")


def ok(msg):
    print(f"  [OK]    {msg}")


def warn(msg):
    print(f"  [WARN]  {msg}")


def err(msg):
    print(f"  [ERROR] {msg}")


def info(msg):
    print(f"         {msg}")


def run(cmd, cwd=None):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd, timeout=15)
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return -1, "", str(e)


def main():
    print("=" * 55)
    print(" FitAgent Environment Check")
    print(f" Platform: {platform.system()} | Project: {PROJECT_ROOT}")
    print("=" * 55)

    errors = 0
    warnings = 0

    # ---- 1. Directories ----
    print("\n[1] Project directories")
    if os.path.isdir(BACKEND_DIR):
        ok(f"backend/ found")
    else:
        err(f"backend/ not found at {BACKEND_DIR}")
        errors += 1
    if os.path.isdir(FRONTEND_DIR):
        ok(f"frontend/ found")
    else:
        err(f"frontend/ not found at {FRONTEND_DIR}")
        errors += 1

    # ---- 2. Python ----
    print("\n[2] Python")
    code, out, _ = run("python --version")
    if code == 0:
        ok(f"Python: {out}")
        # Check version >= 3.10
        try:
            ver_str = out.split()[1]
            major, minor = map(int, ver_str.split(".")[:2])
            if (major, minor) >= (3, 10):
                ok(f"Python {major}.{minor} >= 3.10")
            else:
                err(f"Python {major}.{minor} is too old. Requires 3.10+")
                errors += 1
        except:
            warn("Could not parse Python version")
            warnings += 1
    else:
        err("Python not found on PATH")
        errors += 1

    # ---- 3. Node.js ----
    print("\n[3] Node.js")
    code, out, _ = run("node --version")
    if code == 0:
        ok(f"Node.js: {out}")
        try:
            ver_str = out.lstrip("v")
            major = int(ver_str.split(".")[0])
            if major >= 20:
                ok(f"Node {major} >= 20")
            elif major >= 18:
                warn(f"Node {major} < 20. Next.js 15 may need downgrade (already done).")
                warnings += 1
            else:
                err(f"Node {major} too old. Requires 18+")
                errors += 1
        except:
            warn("Could not parse Node version")
            warnings += 1
    else:
        err("Node.js not found on PATH")
        errors += 1

    # ---- 4. npm ----
    print("\n[4] npm")
    code, out, _ = run("npm --version")
    if code == 0:
        ok(f"npm: {out}")
    else:
        warn("npm not found. Frontend cannot be installed.")
        warnings += 1

    # ---- 4b. Conda Environment ----
    print("\n[4b] Python environment (Conda)")
    in_conda = "conda" in sys.executable.lower() or "anaconda" in sys.executable.lower()
    env_name = os.environ.get("CONDA_DEFAULT_ENV", "")
    in_base = env_name == "base"

    if in_conda:
        if not env_name:
            warn("Running in Conda but env not activated via 'conda activate'.")
            info("The Python binary is in Anaconda. You may be in base environment.")
            info("Create the fitagent env: conda env create -f environment.yml")
            info("Then: conda activate fitagent")
            warnings += 1
        elif in_base:
            err(f"Conda base environment active. Switch to 'fitagent' instead.")
            info("Run: conda activate fitagent")
            errors += 1
        elif env_name == "fitagent":
            ok(f"Conda env 'fitagent' active")
        elif env_name:
            warn(f"Conda env '{env_name}' active (expected 'fitagent')")
            info("Run: conda activate fitagent")
            warnings += 1
        else:
            ok("Conda environment active")
    else:
        in_venv = sys.prefix != sys.base_prefix
        if in_venv:
            ok(f".venv active (fallback): {sys.prefix}")
        else:
            warn("No environment isolation. Create: conda env create -f environment.yml")
            info("Then: conda activate fitagent")
            warnings += 1

    # Check Python 3.11
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
    if sys.version_info >= (3, 11) and sys.version_info < (3, 12):
        ok(f"Python {py_ver} (recommended 3.11)")
    elif sys.version_info >= (3, 10):
        warn(f"Python {py_ver} OK but 3.11 recommended for full compatibility")
    else:
        err(f"Python {py_ver} too old. Requires 3.10+")
        errors += 1

    # ---- 5. Config files ----
    print("\n[5] Configuration")
    if os.path.isfile(os.path.join(PROJECT_ROOT, ".gitignore")):
        ok(".gitignore found")
    else:
        warn(".gitignore not found. Virtual environment may be accidentally committed.")
        warnings += 1
    if os.path.isfile(os.path.join(BACKEND_DIR, "requirements.txt")):
        ok("backend/requirements.txt found")
    else:
        err("requirements.txt missing")
        errors += 1
    if os.path.isfile(os.path.join(BACKEND_DIR, "requirements-dev.txt")):
        ok("backend/requirements-dev.txt found")
    else:
        info("requirements-dev.txt not found (optional, for development)")
    if os.path.isfile(os.path.join(FRONTEND_DIR, "package.json")):
        ok("frontend/package.json found")
    else:
        err("package.json missing")
        errors += 1
    if os.path.isfile(ENV_FILE):
        ok(".env found")
    else:
        warn(".env not found. Copy .env.example → .env or create one.")
        warnings += 1

    # ---- 6. .env contents ----
    if os.path.isfile(ENV_FILE):
        print("\n[6] Environment variables")
        env_vars = {}
        with open(ENV_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env_vars[k.strip()] = v.strip()

        # DATABASE_URL
        if env_vars.get("DATABASE_URL"):
            db_url = env_vars["DATABASE_URL"]
            if "sqlite" in db_url:
                ok(f"DATABASE_URL: SQLite mode (no Docker needed)")
            elif "postgresql" in db_url:
                warn(f"DATABASE_URL: PostgreSQL mode. Ensure PG is running.")
                warnings += 1
        else:
            warn("DATABASE_URL not set. Default SQLite will be used.")
            warnings += 1

        # LLM_API_KEY
        api_key = env_vars.get("LLM_API_KEY", "")
        if api_key and api_key not in ("your-api-key-here", ""):
            ok("LLM_API_KEY: configured (LLM mode)")
        else:
            warn("LLM_API_KEY: not set or placeholder. System runs in fallback mode.")
            warnings += 1

        # MCP_DEMO_USER_ID
        if env_vars.get("MCP_DEMO_USER_ID"):
            ok("MCP_DEMO_USER_ID: configured")
        else:
            warn("MCP_DEMO_USER_ID: not set. MCP tools that need user_id will fail.")
            warnings += 1

    # ---- 7. Database ----
    print("\n[7] Database")
    if os.path.isfile(DB_FILE):
        size_kb = os.path.getsize(DB_FILE) // 1024
        ok(f"fitagent.db found ({size_kb} KB)")
    else:
        warn("fitagent.db not found. Run 'cd backend && alembic upgrade head'")
        warnings += 1

    # ---- 8. Alembic ----
    print("\n[8] Alembic (migration tool)")
    code, out, _ = run("python -m alembic --version", cwd=BACKEND_DIR)
    if code == 0:
        ok(f"Alembic: {out}")
    else:
        warn("Alembic not available. Run 'pip install alembic'")
        warnings += 1

    # ---- 9. Ports ----
    print("\n[9] Port availability")
    for port, name in [(8001, "Backend"), (3000, "Frontend")]:
        if platform.system() == "Windows":
            code, out, _ = run(f"netstat -ano | findstr :{port} | findstr LISTENING")
        else:
            code, out, _ = run(f"lsof -i :{port} 2>/dev/null")
        if code != 0:
            ok(f"Port {port} ({name}): free")
        else:
            warn(f"Port {port} ({name}): in use. Run: scripts\\dev-stop.bat")
            warnings += 1

    # ---- 10. MCP import ----
    print("\n[10] MCP Server import")
    code, out, _ = run(
        'python -c "from app.mcp.server import SERVER_NAME; print(SERVER_NAME)"',
        cwd=BACKEND_DIR
    )
    if code == 0:
        ok(f"MCP Server: {out}")
    else:
        warn(f"MCP Server import failed: {out[:100]}")
        warnings += 1

    # ---- Summary ----
    print("\n" + "=" * 55)
    if errors == 0 and warnings == 0:
        print(" RESULT: Ready to start. Run scripts/start-dev.bat (or .sh)")
    elif errors == 0:
        print(f" RESULT: Ready with {warnings} warning(s). Review warnings above.")
    else:
        print(f" RESULT: {errors} error(s), {warnings} warning(s). Fix errors first.")
    print("=" * 55)

    if errors > 0:
        print("\nFix the [ERROR] items above, then re-run this script.")
    if warnings > 0:
        print("Some [WARN] items are OK to skip — the system has fallbacks.")

    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
