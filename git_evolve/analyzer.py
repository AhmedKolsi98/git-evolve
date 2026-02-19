"""Code evolution analysis using git blame statistics."""
import subprocess
import os
import fnmatch
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List, Tuple, Optional, TypedDict
from datetime import datetime


class AnalysisResult(TypedDict):
    """Type definition for analysis result dictionary."""
    base_commit: str
    total_lines: int
    base_lines_surviving: int
    manual_or_modified_lines: int
    evolution_percent: float
    survival_percent: float
    files_analyzed: int
    repository: str
    file_breakdown: Optional[List[Dict[str, any]]]
    timeline: Optional[List[Dict[str, str]]]
    error: Optional[str]


class GitCommandError(Exception):
    """Raised when a git command fails."""
    pass


class InvalidCommitError(GitCommandError):
    """Raised when an invalid commit reference is provided."""
    pass


class NotAGitRepositoryError(GitCommandError):
    """Raised when not in a git repository."""
    pass


def run_git_command(cmd: List[str], cwd: Optional[str] = None) -> str:
    """Execute a git command and return its output.
    
    Args:
        cmd: List of command arguments to pass to git
        cwd: Working directory for the command (optional)
    
    Returns:
        Standard output from the git command
    
    Raises:
        GitCommandError: If the git command fails
        FileNotFoundError: If git is not installed or not found
    """
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() if e.stderr else str(e)
        raise GitCommandError(f"Git command failed: {' '.join(cmd)}\n{error_msg}") from e
    except FileNotFoundError:
        raise GitCommandError("Git is not installed or not found in PATH") from None


def get_repository_root() -> str:
    """Get the root directory of the current git repository.
    
    Returns:
        Absolute path to the repository root
    
    Raises:
        GitCommandError: If not in a git repository or git command fails
    """
    try:
        return run_git_command(["git", "rev-parse", "--show-toplevel"]).strip()
    except GitCommandError as e:
        if "not a git repository" in str(e).lower():
            raise NotAGitRepositoryError(
                "Current directory is not a git repository. "
                "Please run this command from within a git repository."
            ) from e
        raise


def resolve_commit(base_commit: str) -> str:
    """Resolve a commit reference to its full hash.
    
    Args:
        base_commit: Commit reference (hash, tag, branch, or relative ref)
    
    Returns:
        Full 40-character commit hash
    
    Raises:
        InvalidCommitError: If the commit reference is invalid
    """
    try:
        result = run_git_command(["git", "rev-parse", base_commit]).strip()
        if len(result) != 40:
            raise InvalidCommitError(f"Could not resolve commit: {base_commit}")
        return result
    except GitCommandError as e:
        raise InvalidCommitError(f"Invalid commit reference: {base_commit}") from e


def get_tracked_files(
    repo_root: str,
    exclude_patterns: Optional[List[str]] = None
) -> List[str]:
    """Get all tracked files in the repository.
    
    Args:
        repo_root: Root directory of the repository
        exclude_patterns: List of glob patterns to exclude
    
    Returns:
        List of file paths relative to repository root
    """
    files = run_git_command(["git", "ls-files"], cwd=repo_root).splitlines()
    
    # Filter empty lines
    files = [f for f in files if f.strip()]
    
    # Apply exclusion patterns
    if exclude_patterns:
        filtered_files = []
        for filepath in files:
            excluded = False
            for pattern in exclude_patterns:
                if fnmatch.fnmatch(filepath, pattern) or fnmatch.fnmatch(os.path.basename(filepath), pattern):
                    excluded = True
                    break
            if not excluded:
                filtered_files.append(filepath)
        return filtered_files
    
    return files


def is_binary_file(file_path: str, repo_root: str) -> bool:
    """Check if a file is binary.
    
    Args:
        file_path: Path to file relative to repo root
        repo_root: Root directory of the repository
    
    Returns:
        True if file is binary, False otherwise
    """
    try:
        result = subprocess.run(
            ["git", "check-attr", "binary", "--", file_path],
            capture_output=True,
            text=True,
            cwd=repo_root
        )
        return "binary" in result.stdout and "set" in result.stdout
    except subprocess.CalledProcessError:
        return False


def get_commit_timeline(
    repo_root: str,
    base_commit: str,
    limit: int = 20
) -> List[Dict[str, str]]:
    """Get commit timeline from base to HEAD.
    
    Args:
        repo_root: Root directory of the repository
        base_commit: Full commit hash to start from
        limit: Maximum number of commits to return
    
    Returns:
        List of dictionaries with commit info (hash, date, message)
    """
    try:
        # Get commits between base and HEAD
        cmd = [
            "git", "log", 
            f"{base_commit}..HEAD",
            "--format=%H|%ai|%s",
            "-n", str(limit)
        ]
        output = run_git_command(cmd, cwd=repo_root)
        
        timeline = []
        for line in output.splitlines():
            if "|" in line:
                parts = line.split("|", 2)
                if len(parts) == 3:
                    timeline.append({
                        "hash": parts[0],
                        "date": parts[1],
                        "message": parts[2]
                    })
        
        return timeline
    except GitCommandError:
        return []


def analyze_file_blame_optimized(file_path: str, base_commit: str, repo_root: str) -> Tuple[str, int, int]:
    """Analyze a single file using git blame to count evolved lines.
    
    Compares lines against a base commit to determine which lines have changed
    or been added since that point. Uses git blame porcelain format for accurate
    commit hash extraction.
    
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
        # Skip binary files
        if is_binary_file(file_path, repo_root):
            return (file_path, 0, 0)
            
        output = run_git_command(
            ["git", "blame", "-w", "--porcelain", "--", file_path], 
            cwd=repo_root
        )
        
        if not output.strip():
            return (file_path, 0, 0)
            
        total_lines = 0
        base_lines = 0
        base_prefix = base_commit[:7]
        
        for line in output.splitlines():
            # In porcelain format, each line starts with commit hash info or space
            # Format: <40-char hash> ... \t<actual code>
            # Continuation lines start with space: <space><40-char hash> ...
            if line.startswith("\t"):
                # This is the actual code line content
                total_lines += 1
            elif line.startswith(" "):
                # Continuation line - extract commit hash after the space
                parts = line.split()
                if parts and len(parts[0]) >= 7:
                    commit_hash = parts[0]
                    if commit_hash.startswith(base_prefix):
                        base_lines += 1
                    total_lines += 1
            elif not line.startswith(" ") and not line.startswith("\t"):
                # First occurrence line - extract commit hash from start
                parts = line.split()
                if parts and len(parts[0]) >= 7:
                    commit_hash = parts[0]
                    if commit_hash.startswith(base_prefix):
                        base_lines += 1
                    total_lines += 1
        
        return (file_path, total_lines, base_lines)
    except GitCommandError:
        # Skip files that can't be blamed (e.g., deleted, unmerged)
        return (file_path, 0, 0)
    except Exception:
        return (file_path, 0, 0)


def analyze_parallel(
    files: List[str],
    base_commit: str,
    repo_root: str,
    max_workers: int = 4,
    show_progress: bool = False
) -> List[Tuple[str, int, int]]:
    """Analyze multiple files in parallel using process pool.
    
    Args:
        files: List of file paths to analyze
        base_commit: Full commit hash to compare against
        repo_root: Root directory of the repository
        max_workers: Number of parallel workers (default: 4)
        show_progress: Whether to show progress (default: False)
    
    Returns:
        List of tuples (file_path, total_lines, base_lines_surviving)
    """
    results = []
    total_files = len(files)
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(analyze_file_blame_optimized, f, base_commit, repo_root): f 
            for f in files
        }
        
        completed = 0
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception:
                # Skip failed files
                pass
            
            completed += 1
            if show_progress and completed % 10 == 0:
                print(f"  Progress: {completed}/{total_files} files...", end="\r")
    
    if show_progress:
        print(f"  Progress: {total_files}/{total_files} files... Done!")
        
    return results


def analyze(
    base_commit: str,
    file_breakdown: bool = False,
    timeline: bool = False,
    parallel: bool = True,
    max_workers: int = 4,
    exclude_patterns: Optional[List[str]] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    show_progress: bool = False
) -> AnalysisResult:
    """Analyze code evolution since a base commit.
    
    Calculates metrics about how much the codebase has changed since a specified
    commit by examining line histories and counting modified/new lines.
    
    Args:
        base_commit: Commit reference (hash, tag, branch, or relative ref)
        file_breakdown: Include per-file statistics (default: False)
        timeline: Include timeline data (default: False)
        parallel: Use parallel processing for large repositories (default: True)
        max_workers: Number of parallel workers (default: 4)
        exclude_patterns: List of glob patterns to exclude from analysis
        since: Only analyze commits after this date (ISO format)
        until: Only analyze commits before this date (ISO format)
        show_progress: Show progress for large repositories (default: False)
    
    Returns:
        AnalysisResult dictionary containing:
        - base_commit: Full commit hash
        - total_lines: Total lines in repository
        - base_lines_surviving: Unchanged lines since base
        - manual_or_modified_lines: Changed/new lines
        - evolution_percent: Percentage of code that has changed
        - survival_percent: Percentage of code that hasn't changed
        - files_analyzed: Number of files processed
        - repository: Repository name
        - file_breakdown: Per-file stats (if requested)
        - timeline: Commit timeline (if requested)
        - error: Error message (if operation failed)
    """
    try:
        repo_root = get_repository_root()
        base_full = resolve_commit(base_commit)
        files = get_tracked_files(repo_root, exclude_patterns)
        
        if not files:
            return AnalysisResult(
                error="No tracked files found",
                evolution_percent=0.0,
                base_commit="",
                total_lines=0,
                base_lines_surviving=0,
                manual_or_modified_lines=0,
                survival_percent=0.0,
                files_analyzed=0,
                repository=os.path.basename(repo_root),
                file_breakdown=None,
                timeline=None
            )
        
        if parallel and len(files) > 10:
            results = analyze_parallel(
                files, base_full, repo_root, max_workers, show_progress
            )
        else:
            results = [
                analyze_file_blame_optimized(f, base_full, repo_root) 
                for f in files
            ]
        
        total_lines = sum(r[1] for r in results)
        base_lines = sum(r[2] for r in results)
        manual_lines = total_lines - base_lines
        evolution_percent = round((manual_lines / total_lines) * 100, 2) if total_lines > 0 else 0
        
        result: AnalysisResult = {
            "base_commit": base_full,
            "total_lines": total_lines,
            "base_lines_surviving": base_lines,
            "manual_or_modified_lines": manual_lines,
            "evolution_percent": evolution_percent,
            "survival_percent": round(100 - evolution_percent, 2),
            "files_analyzed": len(files),
            "repository": os.path.basename(repo_root),
            "file_breakdown": None,
            "timeline": None,
            "error": None
        }
        
        if file_breakdown:
            file_stats = []
            for file_path, file_total, file_base in results:
                if file_total > 0:
                    file_evolution = round((file_total - file_base) / file_total * 100, 2)
                    file_stats.append({
                        "file": file_path,
                        "total_lines": file_total,
                        "evolved_lines": file_total - file_base,
                        "evolution_percent": file_evolution
                    })
            file_stats.sort(key=lambda x: x["evolution_percent"], reverse=True)
            result["file_breakdown"] = file_stats[:20]
        
        if timeline:
            result["timeline"] = get_commit_timeline(repo_root, base_full)
        
        return result
        
    except NotAGitRepositoryError as e:
        return AnalysisResult(
            error=str(e),
            evolution_percent=0.0,
            base_commit="",
            total_lines=0,
            base_lines_surviving=0,
            manual_or_modified_lines=0,
            survival_percent=0.0,
            files_analyzed=0,
            repository="",
            file_breakdown=None,
            timeline=None
        )
    except InvalidCommitError as e:
        return AnalysisResult(
            error=str(e),
            evolution_percent=0.0,
            base_commit="",
            total_lines=0,
            base_lines_surviving=0,
            manual_or_modified_lines=0,
            survival_percent=0.0,
            files_analyzed=0,
            repository="",
            file_breakdown=None,
            timeline=None
        )
    except GitCommandError as e:
        return AnalysisResult(
            error=str(e),
            evolution_percent=0.0,
            base_commit="",
            total_lines=0,
            base_lines_surviving=0,
            manual_or_modified_lines=0,
            survival_percent=0.0,
            files_analyzed=0,
            repository="",
            file_breakdown=None,
            timeline=None
        )
    except Exception as e:
        return AnalysisResult(
            error=f"Unexpected error: {str(e)}",
            evolution_percent=0.0,
            base_commit="",
            total_lines=0,
            base_lines_surviving=0,
            manual_or_modified_lines=0,
            survival_percent=0.0,
            files_analyzed=0,
            repository="",
            file_breakdown=None,
            timeline=None
        )
