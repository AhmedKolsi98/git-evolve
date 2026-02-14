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
