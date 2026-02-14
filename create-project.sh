# 1. Create the Python package directory
mkdir -p git_evolve tests

# 2. Create the main analyzer file
cat > git_evolve/analyzer.py << 'ENDOFFILE'
import subprocess
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List, Tuple, Optional
import os

def run_git_command(cmd, cwd=None):
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, check=True)
    return result.stdout

def get_repository_root():
    return run_git_command(["git", "rev-parse", "--show-toplevel"]).strip()

def resolve_commit(base_commit):
    return run_git_command(["git", "rev-parse", base_commit]).strip()

def get_tracked_files(repo_root):
    return [f for f in run_git_command(["git", "ls-files"], cwd=repo_root).splitlines() if f.strip()]

def analyze_file_blame_optimized(file_path, base_commit, repo_root):
    try:
        output = run_git_command(["git", "blame", "-w", "--porcelain", file_path], cwd=repo_root)
        total_lines = base_lines = 0
        current_commit = None
        for line in output.splitlines():
            if line.startswith("\t"):
                total_lines += 1
                if current_commit and current_commit.startswith(base_commit[:7]):
                    base_lines += 1
            elif not line.startswith(" ") and not line.startswith("\t"):
                parts = line.split()
                if parts:
                    current_commit = parts[0]
        return (file_path, total_lines, base_lines)
    except Exception:
        return (file_path, 0, 0)

def analyze_parallel(files, base_commit, repo_root, max_workers=4):
    results = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(analyze_file_blame_optimized, f, base_commit, repo_root): f for f in files}
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                print(f"Warning: Failed to analyze {futures[future]}: {e}")
    return results

def analyze(base_commit, file_breakdown=False, timeline=False, parallel=True, max_workers=4):
    repo_root = get_repository_root()
    base_full = resolve_commit(base_commit)
    files = get_tracked_files(repo_root)
    
    if not files:
        return {"error": "No tracked files found", "evolution_percent": 0.0}
    
    if parallel and len(files) > 10:
        results = analyze_parallel(files, base_full, repo_root, max_workers)
    else:
        results = [analyze_file_blame_optimized(f, base_full, repo_root) for f in files]
    
    total_lines = sum(r[1] for r in results)
    base_lines = sum(r[2] for r in results)
    manual_lines = total_lines - base_lines
    evolution_percent = ((manual_lines / total_lines) * 100) if total_lines > 0 else 0
    
    result = {
        "base_commit": base_full,
        "total_lines": total_lines,
        "base_lines_surviving": base_lines,
        "manual_or_modified_lines": manual_lines,
        "evolution_percent": round(evolution_percent, 2),
        "survival_percent": round(100 - evolution_percent, 2),
        "files_analyzed": len(files),
        "repository": os.path.basename(repo_root)
    }
    
    if file_breakdown:
        file_stats = []
        for file_path, file_total, file_base in results:
            if file_total > 0:
                file_evolution = ((file_total - file_base) / file_total) * 100
                file_stats.append({
                    "file": file_path,
                    "total_lines": file_total,
                    "evolved_lines": file_total - file_base,
                    "evolution_percent": round(file_evolution, 2)
                })
        file_stats.sort(key=lambda x: x["evolution_percent"], reverse=True)
        result["file_breakdown"] = file_stats[:20]
    
    return result
ENDOFFILE

# 3. Create the CLI file
cat > git_evolve/cli.py << 'ENDOFFILE'
"""CLI interface."""
import argparse
import json
import sys
from .analyzer import analyze

def create_ascii_bar(percentage, width=50):
    filled = int(width * percentage / 100)
    return f"[{'█' * filled}{'░' * (width - filled)}]"

def format_number(num):
    return f"{num:,}"

def print_header(text):
    print(f"\n{'─' * 60}\n  {text}\n{'─' * 60}")

def print_visual_report(result):
    repo = result.get("repository", "Unknown")
    base = result.get("base_commit", "Unknown")[:8]
    
    print_header(f"🧬 Git Evolve Report: {repo}")
    print(f"  Base commit: {base}\n")
    
    total = result.get("total_lines", 0)
    base_lines = result.get("base_lines_surviving", 0)
    manual = result.get("manual_or_modified_lines", 0)
    evolution = result.get("evolution_percent", 0)
    survival = result.get("survival_percent", 0)
    
    print("  📊 Code Statistics")
    print(f"  {'─' * 40}")
    print(f"  {'Total Lines':<25} {format_number(total)}")
    print(f"  {'Base Lines Surviving':<25} {format_number(base_lines)}")
    print(f"  {'Evolved Lines':<25} {format_number(manual)}")
    print(f"  {'Files Analyzed':<25} {format_number(result.get('files_analyzed', 0))}")
    
    print(f"\n  📈 Evolution: {evolution}% | Survival: {survival}%")
    print(f"  {create_ascii_bar(evolution)}")
    
    if "file_breakdown" in result and result["file_breakdown"]:
        print()
        print_header("📁 Top Evolved Files")
        for i, stat in enumerate(result["file_breakdown"][:10], 1):
            fname = stat["file"]
            if len(fname) > 40:
                fname = "..." + fname[-37:]
            evo = stat["evolution_percent"]
            bar = "█" * int(evo / 5) + "░" * (20 - int(evo / 5))
            print(f"  {i:2}. {fname:<40}")
            print(f"      {bar} {evo}% ({format_number(stat['evolved_lines'])} lines)")
    
    print(f"\n{'─' * 60}\n")

def main():
    parser = argparse.ArgumentParser(
        description="🧬 Analyze code evolution from a base commit.",
        epilog="Examples: git-evolve --base v1.0.0 | git-evolve --base HEAD~20 --files --timeline"
    )
    parser.add_argument("--base", required=True, help="Base commit hash, tag, or reference")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--files", action="store_true", dest="file_breakdown", help="Show per-file breakdown")
    parser.add_argument("--timeline", action="store_true", help="Show timeline")
    parser.add_argument("--no-parallel", action="store_true", help="Disable parallel processing")
    parser.add_argument("--workers", type=int, default=4, help="Number of workers (default: 4)")
    parser.add_argument("--quiet", action="store_true", help="Minimal output")
    
    args = parser.parse_args()
    
    try:
        result = analyze(
            base_commit=args.base,
            file_breakdown=args.file_breakdown,
            timeline=args.timeline,
            parallel=not args.no_parallel,
            max_workers=args.workers
        )
        
        if args.json:
            print(json.dumps(result, indent=2))
        elif args.quiet:
            print(f"{result['evolution_percent']}%")
        else:
            print_visual_report(result)
            
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted", file=sys.stderr)
        sys.exit(130)

if __name__ == "__main__":
    main()
ENDOFFILE

# 4. Create the __init__.py file
cat > git_evolve/__init__.py << 'ENDOFFILE'
"""git-evolve: CLI tool for code evolution analysis."""
__version__ = "0.2.0"
__author__ = "Ahmed Kolsi"
from .analyzer import analyze
__all__ = ["analyze"]
ENDOFFILE

# 5. Create pyproject.toml
cat > pyproject.toml << 'ENDOFFILE'
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "git-evolve"
version = "0.2.0"
description = "CLI tool to measure code evolution from a base commit"
readme = "README.md"
license = "MIT"
authors = [{name = "Ahmed Kolsi", email = "your.email@example.com"}]
keywords = ["git", "analytics", "cli", "code-evolution"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Environment :: Console",
    "Intended Audience :: Developers",
    "Programming Language :: Python :: 3",
    "Topic :: Software Development :: Version Control :: Git",
]
requires-python = ">=3.8"
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=7.0", "black>=22.0", "flake8>=4.0", "mypy>=0.950"]

[project.scripts]
git-evolve = "git_evolve.cli:main"

[project.urls]
Homepage = "https://github.com/yourusername/git-evolve"
Repository = "https://github.com/yourusername/git-evolve"

[tool.setuptools.packages.find]
where = ["."]
include = ["git_evolve*"]
ENDOFFILE

# 6. Create README.md
cat > README.md << 'ENDOFFILE'
# 🧬 git-evolve

> Measure code evolution from any base commit.

## 🚀 What is git-evolve?

CLI tool that analyzes how much your codebase has evolved from a specific starting point.

## 📦 Installation

```bash
pip install -e .