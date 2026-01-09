#!/usr/bin/env python3
"""
Non-interactive CLI for Claude conversations - search, list, and export.

Designed for scripting and integration with tools like Claude Code plugins.
All output goes to stdout with proper exit codes for automation.

Exit codes:
    0 - Success (matches found / export successful)
    1 - No matches found / no sessions
    2 - Error (invalid arguments, file not found, etc.)
"""

import argparse
import io
import json
import os
import sys
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

# Handle both package and direct execution imports
try:
    from .search_conversations import ConversationSearcher, SearchResult
    from .extract_claude_logs import ClaudeConversationExtractor
except ImportError:
    from search_conversations import ConversationSearcher, SearchResult
    from extract_claude_logs import ClaudeConversationExtractor


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


def encode_project_path(path: str) -> str:
    """Encode a path the way Claude Code does for project directories.

    Claude Code encodes paths by replacing '/' with '-' and prepending '-'.
    Example: /Users/foo/project -> -Users-foo-project
    """
    # Normalize path (resolve symlinks, remove trailing slashes)
    normalized = os.path.realpath(path).rstrip('/')
    # Replace / with - and prepend -
    return normalized.replace('/', '-')


def find_project_sessions_dir(cwd: Optional[str] = None) -> Optional[Path]:
    """Find the Claude sessions directory for the current or specified project.

    Args:
        cwd: Working directory to find sessions for (default: current directory)

    Returns:
        Path to the sessions directory, or None if not found
    """
    if cwd is None:
        cwd = os.getcwd()

    encoded = encode_project_path(cwd)
    sessions_dir = Path.home() / ".claude" / "projects" / encoded

    if sessions_dir.exists() and sessions_dir.is_dir():
        return sessions_dir

    return None


def get_last_sessions(
    n: int = 1,
    cwd: Optional[str] = None,
    global_search: bool = False,
) -> List[Path]:
    """Get the N most recent sessions for the current project (or globally).

    Args:
        n: Number of sessions to return
        cwd: Working directory to find sessions for (default: current directory)
        global_search: If True, search all projects, not just current

    Returns:
        List of session Paths sorted by modification time (most recent first)
    """
    claude_projects_dir = Path.home() / ".claude" / "projects"

    if not claude_projects_dir.exists():
        return []

    sessions = []

    if global_search:
        # Search all projects
        for jsonl_file in claude_projects_dir.rglob("*.jsonl"):
            sessions.append(jsonl_file)
    else:
        # Search current project only
        sessions_dir = find_project_sessions_dir(cwd)
        if sessions_dir is None:
            return []

        for jsonl_file in sessions_dir.glob("*.jsonl"):
            sessions.append(jsonl_file)

    # Sort by modification time (most recent first)
    sessions.sort(key=lambda x: x.stat().st_mtime, reverse=True)

    return sessions[:n]


def format_conversation_markdown(
    conversation: List[Dict[str, Any]],
    session_id: str,
) -> str:
    """Format a conversation as markdown string for stdout output."""
    lines = []

    # Get timestamp from first message
    first_timestamp = conversation[0].get("timestamp", "") if conversation else ""
    if first_timestamp:
        try:
            dt = datetime.fromisoformat(first_timestamp.replace("Z", "+00:00"))
            date_str = dt.strftime("%Y-%m-%d")
            time_str = dt.strftime("%H:%M:%S")
        except Exception:
            date_str = datetime.now().strftime("%Y-%m-%d")
            time_str = ""
    else:
        date_str = datetime.now().strftime("%Y-%m-%d")
        time_str = ""

    lines.append("# Claude Conversation Log\n")
    lines.append(f"Session ID: {session_id}")
    lines.append(f"Date: {date_str}" + (f" {time_str}" if time_str else ""))
    lines.append("\n---\n")

    for msg in conversation:
        role = msg["role"]
        content = msg["content"]

        if role == "user":
            lines.append("## 👤 User\n")
        elif role == "assistant":
            lines.append("## 🤖 Claude\n")
        elif role == "tool_use":
            lines.append("### 🔧 Tool Use\n")
        elif role == "tool_result":
            lines.append("### 📤 Tool Result\n")
        elif role == "system":
            lines.append("### ℹ️ System\n")
        else:
            lines.append(f"## {role}\n")

        lines.append(f"{content}\n")
        lines.append("---\n")

    return "\n".join(lines)


def format_conversation_json(
    conversation: List[Dict[str, Any]],
    session_id: str,
) -> str:
    """Format a conversation as JSON string for stdout output."""
    first_timestamp = conversation[0].get("timestamp", "") if conversation else ""
    if first_timestamp:
        try:
            dt = datetime.fromisoformat(first_timestamp.replace("Z", "+00:00"))
            date_str = dt.strftime("%Y-%m-%d")
        except Exception:
            date_str = datetime.now().strftime("%Y-%m-%d")
    else:
        date_str = datetime.now().strftime("%Y-%m-%d")

    output = {
        "session_id": session_id,
        "date": date_str,
        "message_count": len(conversation),
        "messages": conversation
    }

    return json.dumps(output, indent=2, ensure_ascii=False)


def handle_last_sessions(args) -> int:
    """Handle --last flag: export last N sessions for current project.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0=success, 1=no sessions, 2=error)
    """
    n = args.last
    global_search = getattr(args, 'global_search', False)

    # Get last N sessions
    sessions = get_last_sessions(n=n, global_search=global_search)

    if not sessions:
        if not args.quiet:
            if global_search:
                print("No Claude sessions found.", file=sys.stderr)
            else:
                cwd = os.getcwd()
                print(f"No Claude sessions found for project: {cwd}", file=sys.stderr)
                print("Use --global to search all projects.", file=sys.stderr)
        return 1

    # Initialize extractor (suppress the "Saving logs to:" message)
    with redirect_stdout(io.StringIO()):
        extractor = ClaudeConversationExtractor(output_dir="/tmp")

    # Process each session
    all_outputs = []
    for session_path in sessions:
        session_id = session_path.stem
        conversation = extractor.extract_conversation(
            session_path,
            detailed=args.detailed
        )

        if not conversation:
            if not args.quiet:
                print(f"Warning: No content in session {session_id[:8]}", file=sys.stderr)
            continue

        # Format based on output format
        if args.format == "json":
            output = format_conversation_json(conversation, session_id)
        elif args.format == "html":
            # For HTML, save to file (not suitable for stdout concatenation)
            if args.output:
                output_path = extractor.save_as_html(conversation, session_id)
                if output_path and not args.quiet:
                    print(f"Saved: {output_path}", file=sys.stderr)
                continue
            else:
                # Fall back to markdown for stdout
                output = format_conversation_markdown(conversation, session_id)
        else:  # markdown
            output = format_conversation_markdown(conversation, session_id)

        all_outputs.append(output)

    if not all_outputs:
        if not args.quiet:
            print("No conversation content found.", file=sys.stderr)
        return 1

    # Combine outputs
    combined_output = "\n\n".join(all_outputs)

    # Output to file or stdout
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(combined_output)
        if not args.quiet:
            print(f"Saved: {output_path}", file=sys.stderr)
    else:
        print(combined_output)

    return 0


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

  %(prog)s --last                       # Export last session as markdown
  %(prog)s --last 3                     # Export last 3 sessions
  %(prog)s --last --format json         # Export as JSON
  %(prog)s --last -o output.md          # Save to file
  %(prog)s --last --detailed            # Include tool use & system msgs
  %(prog)s --last --global              # Last session across all projects

Exit codes:
  0 - Matches found / export successful
  1 - No matches found / no sessions
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

    # Last session export
    parser.add_argument(
        "--last", "-L",
        nargs="?",
        const=1,
        type=int,
        metavar="N",
        help="Export the last N sessions for current project (default: 1)",
    )
    parser.add_argument(
        "--format", "-f",
        choices=["markdown", "json", "html"],
        default="markdown",
        help="Output format for --last export (default: markdown)",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output file path for --last (default: stdout)",
    )
    parser.add_argument(
        "--detailed", "-d",
        action="store_true",
        help="Include tool use, MCP responses, and system messages in --last export",
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

    # Handle --last flag (export last N sessions)
    if args.last is not None:
        return handle_last_sessions(args)

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
