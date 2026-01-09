#!/usr/bin/env python3
"""
Non-interactive CLI search for Claude conversations.

Designed for scripting and integration with tools like Claude Code plugins.
All output goes to stdout with proper exit codes for automation.

Exit codes:
    0 - Success (matches found)
    1 - No matches found
    2 - Error (invalid arguments, file not found, etc.)
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Handle both package and direct execution imports
try:
    from .search_conversations import ConversationSearcher, SearchResult
except ImportError:
    from search_conversations import ConversationSearcher, SearchResult


def format_text_output(
    results: List[SearchResult],
    query: str,
    relative_time: bool = False,
    quiet: bool = False,
) -> str:
    """Format results as human-readable text."""
    lines = []

    if not quiet:
        lines.append(f"Found {len(results)} matches for '{query}'")
        lines.append("")

    for i, result in enumerate(results, 1):
        if not quiet:
            lines.append(f"{i}. {result.format_text(relative_time)}")
        else:
            # Minimal output in quiet mode
            project = result.project_name or result._extract_project_name()
            lines.append(f"{result.session_id[:8]} {project}: {result.context[:100]}...")

        if not quiet:
            lines.append("")

    return "\n".join(lines)


def format_json_output(
    results: List[SearchResult],
    query: str,
    relative_time: bool = False,
) -> str:
    """Format results as JSON for machine consumption."""
    # Group by session for better structure
    sessions = {}
    for result in results:
        sid = result.session_id
        if sid not in sessions:
            sessions[sid] = {
                "session_id": sid,
                "project": result.project_name or result._extract_project_name(),
                "cwd": result.cwd,
                "git_branch": result.git_branch,
                "matches": [],
            }
        sessions[sid]["matches"].append({
            "speaker": result.speaker,
            "timestamp": result._relative_time() if relative_time else (
                result.timestamp.isoformat() if result.timestamp else None
            ),
            "relevance": round(result.relevance_score, 3),
            "snippet": result.context,
            "line_number": result.line_number,
        })

    output = {
        "query": query,
        "total_matches": len(results),
        "sessions_matched": len(sessions),
        "results": list(sessions.values()),
    }

    return json.dumps(output, indent=2, ensure_ascii=False)


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse date string in various formats."""
    formats = [
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def main() -> int:
    """Main entry point for CLI search."""
    parser = argparse.ArgumentParser(
        description="Search Claude Code conversation history (non-interactive)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "typescript error"           # Basic text search
  %(prog)s --pattern "import.*"         # Regex search
  %(prog)s "bug" --project EvoSiteMaster    # Filter by project
  %(prog)s "fix" --branch feat/auth     # Filter by git branch
  %(prog)s "api" --json --quiet         # JSON output, no decorations
  %(prog)s "test" --limit 5 --context 500   # Customize output

Exit codes:
  0 - Matches found
  1 - No matches found
  2 - Error
        """,
    )

    # Search query (positional or via --pattern for regex)
    parser.add_argument(
        "query",
        nargs="?",
        help="Search query (text)",
    )
    parser.add_argument(
        "--pattern", "-p",
        type=str,
        help="Regex pattern to search for (alternative to positional query)",
    )

    # Scope flags
    parser.add_argument(
        "--global", "-g",
        dest="global_search",
        action="store_true",
        help="Search all projects globally",
    )
    parser.add_argument(
        "--project",
        type=str,
        help="Filter by project name or path (matches against cwd)",
    )
    parser.add_argument(
        "--session-id",
        type=str,
        help="Filter by specific session ID (partial match supported)",
    )
    parser.add_argument(
        "--branch",
        type=str,
        help="Filter by git branch name",
    )

    # Speaker/content filters
    parser.add_argument(
        "--speaker",
        choices=["human", "assistant", "tool"],
        help="Filter by speaker type",
    )
    parser.add_argument(
        "--show-tools", "-t",
        action="store_true",
        help="Include tool calls in search results",
    )
    parser.add_argument(
        "--no-tools",
        action="store_true",
        help="Exclude tool calls from results (default)",
    )

    # Date filters
    parser.add_argument(
        "--from", "--date-from",
        dest="date_from",
        type=str,
        help="Filter results from date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--to", "--date-to",
        dest="date_to",
        type=str,
        help="Filter results to date (YYYY-MM-DD)",
    )

    # Output format flags
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress decorations and warnings (minimal output)",
    )
    parser.add_argument(
        "--relative-time", "-r",
        action="store_true",
        help="Display relative timestamps (e.g., '10 minutes ago')",
    )
    parser.add_argument(
        "--absolute-time",
        action="store_true",
        help="Display absolute timestamps (default)",
    )

    # Limits
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=10,
        help="Maximum number of results (default: 10)",
    )
    parser.add_argument(
        "--context", "-c",
        type=int,
        default=300,
        help="Context snippet size in characters (default: 300)",
    )

    # Search options
    parser.add_argument(
        "--case-sensitive",
        action="store_true",
        help="Make search case-sensitive",
    )
    parser.add_argument(
        "--exact",
        action="store_true",
        help="Use exact string matching (no fuzzy/smart search)",
    )

    args = parser.parse_args()

    # Determine search query and mode
    if args.pattern:
        query = args.pattern
        mode = "regex"
    elif args.query:
        query = args.query
        mode = "exact" if args.exact else "smart"
    else:
        if not args.quiet:
            print("Error: No search query provided", file=sys.stderr)
            print("Usage: claude-search QUERY or claude-search --pattern REGEX", file=sys.stderr)
        return 2

    # Parse date filters
    date_from = None
    date_to = None

    if args.date_from:
        date_from = parse_date(args.date_from)
        if not date_from:
            if not args.quiet:
                print(f"Error: Invalid date format: {args.date_from}", file=sys.stderr)
            return 2

    if args.date_to:
        date_to = parse_date(args.date_to)
        if not date_to:
            if not args.quiet:
                print(f"Error: Invalid date format: {args.date_to}", file=sys.stderr)
            return 2

    # Determine if tools should be included
    include_tools = args.show_tools and not args.no_tools

    # Initialize searcher
    searcher = ConversationSearcher(quiet=args.quiet)

    # Perform search
    try:
        results = searcher.search(
            query=query,
            mode=mode,
            date_from=date_from,
            date_to=date_to,
            speaker_filter=args.speaker,
            max_results=args.limit,
            case_sensitive=args.case_sensitive,
            context_size=args.context,
            session_id=args.session_id,
            project_filter=args.project,
            branch_filter=args.branch,
            include_tools=include_tools,
            global_search=args.global_search,
        )
    except Exception as e:
        if not args.quiet:
            print(f"Error: {e}", file=sys.stderr)
        return 2

    # Handle no results
    if not results:
        if args.json:
            print(json.dumps({
                "query": query,
                "total_matches": 0,
                "sessions_matched": 0,
                "results": [],
            }, indent=2))
        elif not args.quiet:
            print(f"No matches found for '{query}'")
        return 1

    # Format and output results
    use_relative_time = args.relative_time and not args.absolute_time

    if args.json:
        output = format_json_output(results, query, use_relative_time)
    else:
        output = format_text_output(results, query, use_relative_time, args.quiet)

    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
