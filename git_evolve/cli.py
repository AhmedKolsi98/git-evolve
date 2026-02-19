"""Command-line interface for git-evolve."""
import argparse
import csv
import json
import sys
import os
from typing import Dict, Any, Optional, List
from .analyzer import analyze, GitCommandError, InvalidCommitError, NotAGitRepositoryError

# Try to import colorama for colored output, fallback gracefully
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    COLORS_AVAILABLE = True
except ImportError:
    COLORS_AVAILABLE = False
    class Fore:
        GREEN = RED = YELLOW = CYAN = MAGENTA = ""
    class Style:
        BRIGHT = DIM = RESET_ALL = ""


def create_ascii_bar(percentage: float, width: int = 50) -> str:
    """Create an ASCII progress bar representation.
    
    Args:
        percentage: Value from 0 to 100
        width: Width of the bar in characters (default: 50)
    
    Returns:
        Formatted ASCII bar with filled and empty segments
    """
    filled = int(width * percentage / 100)
    filled_char = "█" if not COLORS_AVAILABLE else f"{Fore.CYAN}█{Style.RESET_ALL}"
    empty_char = "░" if not COLORS_AVAILABLE else f"{Fore.DIM}░{Style.RESET_ALL}"
    return f"[{filled_char * filled}{empty_char * (width - filled)}]"


def format_number(num: int) -> str:
    """Format a number with thousands separators.
    
    Args:
        num: Integer to format
    
    Returns:
        Formatted string with comma separators
    """
    return f"{num:,}"


def print_header(text: str) -> None:
    """Print a formatted section header.
    
    Args:
        text: Header text to display
    """
    header_char = "─" if not COLORS_AVAILABLE else f"{Fore.DIM}─{Style.RESET_ALL}"
    emoji = "🧬"
    print(f"\n{header_char * 60}\n  {emoji} {text}\n{header_char * 60}")


def print_visual_report(result: Dict[str, Any], show_timeline: bool = False) -> None:
    """Print a formatted visual report of analysis results.
    
    Displays repository statistics, evolution metrics, and top evolved files
    with ASCII visualizations.
    
    Args:
        result: Dictionary of analysis results from analyze()
        show_timeline: Whether to show commit timeline
    """
    if result.get("error"):
        error_msg = result["error"]
        if COLORS_AVAILABLE:
            print(f"{Fore.RED}Error: {error_msg}{Style.RESET_ALL}")
        else:
            print(f"Error: {error_msg}")
        return
    
    repo = result.get("repository", "Unknown")
    base = result.get("base_commit", "Unknown")[:8]
    
    print_header(f"Git Evolve Report: {repo}")
    print(f"  Base commit: {base}\n")
    
    total = result.get("total_lines", 0)
    base_lines = result.get("base_lines_surviving", 0)
    manual = result.get("manual_or_modified_lines", 0)
    evolution = result.get("evolution_percent", 0)
    survival = result.get("survival_percent", 0)
    
    # Apply colors if available
    stat_color = Fore.GREEN if evolution < 30 else (Fore.YELLOW if evolution < 60 else Fore.RED)
    if not COLORS_AVAILABLE:
        stat_color = ""
    
    print("  📊 Code Statistics")
    print(f"  {'─' * 40}")
    print(f"  {'Total Lines':<25} {format_number(total)}")
    print(f"  {'Base Lines Surviving':<25} {format_number(base_lines)}")
    print(f"  {'Evolved Lines':<25} {format_number(manual)}")
    print(f"  {'Files Analyzed':<25} {format_number(result.get('files_analyzed', 0))}")
    
    print(f"\n  📈 Evolution: {stat_color}{evolution}%{Style.RESET_ALL if COLORS_AVAILABLE else ''} | Survival: {survival}%")
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
    
    # Show timeline if requested
    if show_timeline and "timeline" in result and result["timeline"]:
        print()
        print_header("📜 Commit Timeline")
        for commit in result["timeline"][:10]:
            print(f"  {commit['hash'][:7]} | {commit['date'][:10]} | {commit['message'][:50]}")
    
    print(f"\n{'─' * 60}\n")


def print_csv_output(result: Dict[str, Any]) -> None:
    """Print analysis results in CSV format.
    
    Args:
        result: Dictionary of analysis results from analyze()
    """
    if result.get("error"):
        print(f"Error: {result['error']}", file=sys.stderr)
        sys.exit(1)
    
    writer = csv.writer(sys.stdout)
    writer.writerow([
        "Repository", "Base Commit", "Total Lines", "Base Lines Surviving",
        "Evolved Lines", "Evolution %", "Survival %", "Files Analyzed"
    ])
    writer.writerow([
        result.get("repository", ""),
        result.get("base_commit", "")[:8],
        result.get("total_lines", 0),
        result.get("base_lines_surviving", 0),
        result.get("manual_or_modified_lines", 0),
        result.get("evolution_percent", 0),
        result.get("survival_percent", 0),
        result.get("files_analyzed", 0)
    ])
    
    # If file breakdown is included, output that too
    if result.get("file_breakdown"):
        print("\n# File Breakdown")
        writer = csv.writer(sys.stdout)
        writer.writerow(["File", "Total Lines", "Evolved Lines", "Evolution %"])
        for stat in result["file_breakdown"]:
            writer.writerow([
                stat["file"],
                stat["total_lines"],
                stat["evolved_lines"],
                stat["evolution_percent"]
            ])


def parse_exclude_patterns(pattern_string: Optional[str]) -> Optional[List[str]]:
    """Parse comma-separated exclusion patterns.
    
    Args:
        pattern_string: Comma-separated string of patterns
    
    Returns:
        List of patterns or None if empty
    """
    if not pattern_string:
        return None
    patterns = [p.strip() for p in pattern_string.split(",") if p.strip()]
    return patterns if patterns else None


def main() -> None:
    """Main entry point for the git-evolve CLI.
    
    Parses command-line arguments and runs the code evolution analysis,
    then outputs results in the requested format.
    
    Exits with code 1 on error, 130 on keyboard interrupt.
    """
    parser = argparse.ArgumentParser(
        description="🧬 Analyze code evolution from a base commit.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  git-evolve --base v1.0.0
  git-evolve --base HEAD~20 --files
  git-evolve --base main --json
  git-evolve --base v2.0.0 --exclude "*.pyc,node_modules"
  git-evolve --base main --timeline --csv
  git-evolve --base v1.0.0 --progress"""
    )
    parser.add_argument("--base", required=True, help="Base commit hash, tag, or reference")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--csv", action="store_true", help="Output as CSV")
    parser.add_argument("--files", action="store_true", dest="file_breakdown", help="Show per-file breakdown")
    parser.add_argument("--timeline", action="store_true", help="Show commit timeline")
    parser.add_argument("--no-parallel", action="store_true", help="Disable parallel processing")
    parser.add_argument("--workers", type=int, default=4, help="Number of workers (default: 4)")
    parser.add_argument("--quiet", action="store_true", help="Minimal output")
    parser.add_argument("--progress", action="store_true", help="Show progress for large repositories")
    parser.add_argument(
        "--exclude", 
        type=str, 
        help="Comma-separated patterns to exclude (e.g., '*.pyc,node_modules/*')"
    )
    parser.add_argument(
        "--since",
        type=str,
        help="Only analyze commits after this date (ISO format: YYYY-MM-DD)"
    )
    parser.add_argument(
        "--until",
        type=str,
        help="Only analyze commits before this date (ISO format: YYYY-MM-DD)"
    )
    parser.add_argument("--color", action="store_true", default=COLORS_AVAILABLE, help="Enable colored output")
    
    args = parser.parse_args()
    
    # Handle --no-color flag
    if not args.color and COLORS_AVAILABLE:
        global Fore, Style
        class Fore:
            GREEN = RED = YELLOW = CYAN = MAGENTA = ""
        class Style:
            BRIGHT = DIM = RESET_ALL = ""
    
    try:
        exclude_patterns = parse_exclude_patterns(args.exclude)
        
        result = analyze(
            base_commit=args.base,
            file_breakdown=args.file_breakdown,
            timeline=args.timeline,
            parallel=not args.no_parallel,
            max_workers=args.workers,
            exclude_patterns=exclude_patterns,
            since=args.since,
            until=args.until,
            show_progress=args.progress
        )
        
        # Check for errors in result
        if result.get("error"):
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)
        
        if args.json:
            print(json.dumps(result, indent=2))
        elif args.csv:
            print_csv_output(result)
        elif args.quiet:
            print(f"{result['evolution_percent']}%")
        else:
            print_visual_report(result, show_timeline=args.timeline)
            
    except GitCommandError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except InvalidCommitError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except NotAGitRepositoryError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
