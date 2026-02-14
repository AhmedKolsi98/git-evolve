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
