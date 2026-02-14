"""Code evolution analysis using git blame statistics."""
import subprocess
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List, Tuple, Optional
import os


def run_git_command(cmd: List[str], cwd: Optional[str] = None) -> str:
    """Execute a git command and return its output.
    
    Args:
        cmd: List of command arguments to pass to git
        cwd: Working directory for the command (optional)
    
    Returns:
        Standard output from the git command
    
    Raises:
        subprocess.CalledProcessError: If the git command fails
        FileNotFoundError: If git is not installed or not found
    """
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, check=True)
    return result.stdout



def get_repository_root() -> str:
    """Get the root directory of the current git repository.
    
    Returns:
        Absolute path to the repository root
    
    Raises:
        subprocess.CalledProcessError: If not in a git repository
    """
    return run_git_command(["git", "rev-parse", "--show-toplevel"]).strip()


def resolve_commit(base_commit: str) -> str:
    """Resolve a commit reference to its full hash.
    
    Args:
        base_commit: Commit reference (hash, tag, branch, or relative ref)
    
    Returns:
        Full 40-character commit hash
    
    Raises:
        subprocess.CalledProcessError: If the commit reference is invalid
    """
    return run_git_command(["git", "rev-parse", base_commit]).strip()


def get_tracked_files(repo_root: str) -> List[str]:
    """Get all tracked files in the repository.
    
    Args:
        repo_root: Root directory of the repository
    
    Returns:
        List of file paths relative to repository root
    """
    return [f for f in run_git_command(["git", "ls-files"], cwd=repo_root).splitlines() if f.strip()]




def analyze_file_blame_optimized(file_path: str, base_commit: str, repo_root: str) -> Tuple[str, int, int]:
    """Analyze a single file using git blame to count evolved lines.
    
    Compares lines against a base commit to determine which lines have changed
    or been added since that point.
    
    Args:
        file_path: Path to file relative to repo root
        base_commit: Full commit hash to compare against
        repo_root: Root directory of the repository
    
    Returns:
        Tuple of (file_path, total_lines, base_lines_surviving)
        - total_lines: Total number of lines in the file
        - base_lines_surviving: Lines unchanged since base_commit
    """
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


def analyze_parallel(
    files: List[str],
    base_commit: str,
    repo_root: str,
    max_workers: int = 4
) -> List[Tuple[str, int, int]]:
    """Analyze multiple files in parallel using process pool.
    
    Args:
        files: List of file paths to analyze
        base_commit: Full commit hash to compare against
        repo_root: Root directory of the repository
        max_workers: Number of parallel workers (default: 4)
    
    Returns:
        List of tuples (file_path, total_lines, base_lines_surviving)
    """
    results = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(analyze_file_blame_optimized, f, base_commit, repo_root): f for f in files}
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                print(f"Warning: Failed to analyze {futures[future]}: {e}")
    return results




def analyze(
    base_commit: str,
    file_breakdown: bool = False,
    timeline: bool = False,
    parallel: bool = True,
    max_workers: int = 4
) -> Dict[str, any]:
    """Analyze code evolution since a base commit.
    
    Calculates metrics about how much the codebase has changed since a specified
    commit by examining line histories and counting modified/new lines.
    
    Args:
        base_commit: Commit reference (hash, tag, branch, or relative ref)
        file_breakdown: Include per-file statistics (default: False)
        timeline: Include timeline data (default: False, not yet implemented)
        parallel: Use parallel processing for large repositories (default: True)
        max_workers: Number of parallel workers (default: 4)
    
    Returns:
        Dictionary containing:
        - base_commit: Full commit hash
        - total_lines: Total lines in repository
        - base_lines_surviving: Unchanged lines since base
        - manual_or_modified_lines: Changed/new lines
        - evolution_percent: Percentage of code that has changed
        - survival_percent: Percentage of code that hasn't changed
        - files_analyzed: Number of files processed
        - repository: Repository name
        - file_breakdown: Per-file stats (if requested)
        - error: Error message (if operation failed)
    """
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
