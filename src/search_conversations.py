#!/usr/bin/env python3
"""
Search functionality for Claude Conversation Extractor

This module provides powerful search capabilities including:
- Full-text search with relevance ranking
- Regex pattern matching
- Date range filtering
- Speaker filtering (Human/Assistant)
- Project/directory filtering
- Git branch filtering

Designed for non-interactive CLI usage with JSON output support.
"""

import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Any


@dataclass
class SearchResult:
    """Represents a search result with context and metadata."""

    file_path: Path
    session_id: str
    matched_content: str
    context: str
    speaker: str  # 'human' or 'assistant'
    timestamp: Optional[datetime] = None
    relevance_score: float = 0.0
    line_number: int = 0
    # New fields for filtering
    cwd: Optional[str] = None
    git_branch: Optional[str] = None
    project_name: Optional[str] = None

    def to_dict(self, relative_time: bool = False) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "session_id": self.session_id,
            "project": self.project_name or self._extract_project_name(),
            "cwd": self.cwd,
            "git_branch": self.git_branch,
            "speaker": self.speaker,
            "relevance": round(self.relevance_score, 3),
            "snippet": self.context,
            "line_number": self.line_number,
        }

        if self.timestamp:
            if relative_time:
                result["timestamp"] = self._relative_time()
            else:
                result["timestamp"] = self.timestamp.isoformat()

        return result

    def _extract_project_name(self) -> str:
        """Extract project name from file path."""
        if self.cwd:
            return Path(self.cwd).name
        # Fallback to parent directory name
        return self.file_path.parent.name.replace('-', '/').split('/')[-1]

    def _relative_time(self) -> str:
        """Format timestamp as relative time."""
        if not self.timestamp:
            return "unknown"

        now = datetime.now(self.timestamp.tzinfo) if self.timestamp.tzinfo else datetime.now()
        diff = now - self.timestamp

        if diff.days > 365:
            years = diff.days // 365
            return f"{years} year{'s' if years > 1 else ''} ago"
        elif diff.days > 30:
            months = diff.days // 30
            return f"{months} month{'s' if months > 1 else ''} ago"
        elif diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "just now"

    def format_text(self, relative_time: bool = False) -> str:
        """Format as human-readable text."""
        time_str = self._relative_time() if relative_time else (
            self.timestamp.strftime("%Y-%m-%d %H:%M") if self.timestamp else "unknown"
        )
        project = self.project_name or self._extract_project_name()

        return (
            f"[{time_str}] {project} ({self.speaker})\n"
            f"  {self.context[:200]}{'...' if len(self.context) > 200 else ''}"
        )


class ConversationSearcher:
    """
    Main search engine for Claude conversations.

    Provides multiple search modes and filtering capabilities.
    All methods are non-interactive and suitable for scripting.
    """

    def __init__(self, quiet: bool = False):
        """
        Initialize the searcher.

        Args:
            quiet: If True, suppress all non-essential output
        """
        self.quiet = quiet

        # Common words to ignore in relevance scoring
        self.stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
            "for", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would",
            "could", "should", "may", "might", "i", "you", "we", "they",
            "it", "this", "that", "these", "those",
        }

    def search(
        self,
        query: str,
        search_dir: Optional[Path] = None,
        mode: str = "smart",
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        speaker_filter: Optional[str] = None,
        max_results: int = 10,
        case_sensitive: bool = False,
        context_size: int = 300,
        # New filter options
        session_id: Optional[str] = None,
        project_filter: Optional[str] = None,
        branch_filter: Optional[str] = None,
        include_tools: bool = False,
        global_search: bool = False,
    ) -> List[SearchResult]:
        """
        Search conversations with various filters.

        Args:
            query: Search query (text or regex pattern if mode="regex")
            search_dir: Directory to search in (default: ~/.claude/projects)
            mode: Search mode - "smart", "exact", "regex"
            date_from: Filter results from this date
            date_to: Filter results until this date
            speaker_filter: Filter by speaker - "human", "assistant", or None
            max_results: Maximum number of results to return
            case_sensitive: Whether search should be case-sensitive
            context_size: Number of characters for context snippets
            session_id: Filter by specific session ID
            project_filter: Filter by project name or path (matches cwd)
            branch_filter: Filter by git branch name
            include_tools: Include tool use messages in results
            global_search: Search all projects (ignore search_dir)

        Returns:
            List of SearchResult objects sorted by relevance
        """
        # Default search directory
        if search_dir is None or global_search:
            search_dir = Path.home() / ".claude" / "projects"

        # Validate search directory
        if not search_dir.exists():
            return []

        # Return empty results for empty query
        if not query or not query.strip():
            return []

        # Find all JSONL files
        jsonl_files = list(search_dir.rglob("*.jsonl"))
        if not jsonl_files:
            return []

        # Filter by session ID if provided
        if session_id:
            jsonl_files = [f for f in jsonl_files if session_id in f.stem]

        # Apply date filtering to files if provided
        if date_from or date_to:
            jsonl_files = self._filter_files_by_date(jsonl_files, date_from, date_to)

        # Search based on mode
        all_results = []

        for jsonl_file in jsonl_files:
            if mode == "regex":
                results = self._search_regex(
                    jsonl_file, query, speaker_filter, case_sensitive,
                    context_size, project_filter, branch_filter, include_tools
                )
            elif mode == "exact":
                results = self._search_exact(
                    jsonl_file, query, speaker_filter, case_sensitive,
                    context_size, project_filter, branch_filter, include_tools
                )
            else:  # smart mode
                results = self._search_smart(
                    jsonl_file, query, speaker_filter, case_sensitive,
                    context_size, project_filter, branch_filter, include_tools
                )

            all_results.extend(results)

        # Sort by relevance score
        all_results.sort(key=lambda x: x.relevance_score, reverse=True)

        # Return top results
        return all_results[:max_results]

    def _filter_files_by_date(
        self,
        files: List[Path],
        date_from: Optional[datetime],
        date_to: Optional[datetime],
    ) -> List[Path]:
        """Filter files by modification date."""
        filtered = []

        for file in files:
            file_mtime = datetime.fromtimestamp(file.stat().st_mtime)

            if date_from and file_mtime < date_from:
                continue
            if date_to and file_mtime > date_to:
                continue

            filtered.append(file)

        return filtered

    def _matches_filters(
        self,
        entry: Dict,
        project_filter: Optional[str],
        branch_filter: Optional[str],
    ) -> bool:
        """Check if entry matches project and branch filters."""
        if project_filter:
            cwd = entry.get("cwd", "")
            if project_filter.lower() not in cwd.lower():
                return False

        if branch_filter:
            git_branch = entry.get("gitBranch", "")
            if branch_filter.lower() != git_branch.lower():
                return False

        return True

    def _search_smart(
        self,
        jsonl_file: Path,
        query: str,
        speaker_filter: Optional[str],
        case_sensitive: bool,
        context_size: int,
        project_filter: Optional[str],
        branch_filter: Optional[str],
        include_tools: bool,
    ) -> List[SearchResult]:
        """Smart search that combines multiple techniques."""
        results = []
        session_id = jsonl_file.stem

        # Process query
        if not case_sensitive:
            query_lower = query.lower()
            query_tokens = set(query_lower.split()) - self.stop_words
        else:
            query_tokens = set(query.split()) - self.stop_words

        try:
            with open(jsonl_file, "r", encoding="utf-8") as f:
                line_num = 0
                for line in f:
                    line_num += 1
                    try:
                        entry = json.loads(line.strip())

                        # Check filters first
                        if not self._matches_filters(entry, project_filter, branch_filter):
                            continue

                        # Determine message type
                        entry_type = entry.get("type")
                        if entry_type == "user":
                            speaker = "human"
                        elif entry_type == "assistant":
                            speaker = "assistant"
                        elif include_tools and entry_type in ("tool_use", "tool_result"):
                            speaker = "tool"
                        else:
                            continue

                        # Apply speaker filter
                        if speaker_filter and speaker != speaker_filter:
                            continue

                        # Extract content
                        content = self._extract_content(entry)
                        if not content:
                            continue

                        # Calculate relevance
                        relevance = self._calculate_relevance(
                            content, query, query_tokens, case_sensitive
                        )

                        if relevance > 0.1:  # Threshold for inclusion
                            context = self._extract_context(
                                content, query, case_sensitive, context_size
                            )

                            # Parse timestamp
                            timestamp = self._parse_timestamp(entry.get("timestamp"))

                            result = SearchResult(
                                file_path=jsonl_file,
                                session_id=session_id,
                                matched_content=content[:200],
                                context=context,
                                speaker=speaker,
                                timestamp=timestamp,
                                relevance_score=relevance,
                                line_number=line_num,
                                cwd=entry.get("cwd"),
                                git_branch=entry.get("gitBranch"),
                            )
                            results.append(result)

                    except json.JSONDecodeError:
                        continue

        except Exception:
            pass  # Silently skip problematic files

        return results

    def _search_exact(
        self,
        jsonl_file: Path,
        query: str,
        speaker_filter: Optional[str],
        case_sensitive: bool,
        context_size: int,
        project_filter: Optional[str],
        branch_filter: Optional[str],
        include_tools: bool,
    ) -> List[SearchResult]:
        """Exact string matching search."""
        results = []
        session_id = jsonl_file.stem
        search_query = query if case_sensitive else query.lower()

        try:
            with open(jsonl_file, "r", encoding="utf-8") as f:
                line_num = 0
                for line in f:
                    line_num += 1
                    try:
                        entry = json.loads(line.strip())

                        if not self._matches_filters(entry, project_filter, branch_filter):
                            continue

                        entry_type = entry.get("type")
                        if entry_type == "user":
                            speaker = "human"
                        elif entry_type == "assistant":
                            speaker = "assistant"
                        elif include_tools and entry_type in ("tool_use", "tool_result"):
                            speaker = "tool"
                        else:
                            continue

                        if speaker_filter and speaker != speaker_filter:
                            continue

                        content = self._extract_content(entry)
                        if not content:
                            continue

                        search_content = content if case_sensitive else content.lower()

                        if search_query in search_content:
                            match_count = search_content.count(search_query)
                            relevance = min(1.0, match_count * 0.2)
                            context = self._extract_context(
                                content, query, case_sensitive, context_size
                            )
                            timestamp = self._parse_timestamp(entry.get("timestamp"))

                            result = SearchResult(
                                file_path=jsonl_file,
                                session_id=session_id,
                                matched_content=content[:200],
                                context=context,
                                speaker=speaker,
                                timestamp=timestamp,
                                relevance_score=relevance,
                                line_number=line_num,
                                cwd=entry.get("cwd"),
                                git_branch=entry.get("gitBranch"),
                            )
                            results.append(result)

                    except json.JSONDecodeError:
                        continue

        except Exception:
            pass

        return results

    def _search_regex(
        self,
        jsonl_file: Path,
        pattern: str,
        speaker_filter: Optional[str],
        case_sensitive: bool,
        context_size: int,
        project_filter: Optional[str],
        branch_filter: Optional[str],
        include_tools: bool,
    ) -> List[SearchResult]:
        """Regex pattern matching search."""
        results = []
        session_id = jsonl_file.stem

        try:
            flags = 0 if case_sensitive else re.IGNORECASE
            regex = re.compile(pattern, flags)
        except re.error:
            return []  # Invalid regex

        try:
            with open(jsonl_file, "r", encoding="utf-8") as f:
                line_num = 0
                for line in f:
                    line_num += 1
                    try:
                        entry = json.loads(line.strip())

                        if not self._matches_filters(entry, project_filter, branch_filter):
                            continue

                        entry_type = entry.get("type")
                        if entry_type == "user":
                            speaker = "human"
                        elif entry_type == "assistant":
                            speaker = "assistant"
                        elif include_tools and entry_type in ("tool_use", "tool_result"):
                            speaker = "tool"
                        else:
                            continue

                        if speaker_filter and speaker != speaker_filter:
                            continue

                        content = self._extract_content(entry)
                        if not content:
                            continue

                        matches = list(regex.finditer(content))

                        if matches:
                            relevance = min(1.0, len(matches) * 0.2)

                            # Get context around first match
                            first_match = matches[0]
                            start = max(0, first_match.start() - context_size // 2)
                            end = min(len(content), first_match.end() + context_size // 2)
                            context = content[start:end]
                            if start > 0:
                                context = "..." + context
                            if end < len(content):
                                context = context + "..."

                            timestamp = self._parse_timestamp(entry.get("timestamp"))

                            result = SearchResult(
                                file_path=jsonl_file,
                                session_id=session_id,
                                matched_content=first_match.group(),
                                context=context,
                                speaker=speaker,
                                timestamp=timestamp,
                                relevance_score=relevance,
                                line_number=line_num,
                                cwd=entry.get("cwd"),
                                git_branch=entry.get("gitBranch"),
                            )
                            results.append(result)

                    except json.JSONDecodeError:
                        continue

        except Exception:
            pass

        return results

    def _extract_content(self, entry: Dict) -> str:
        """Extract text content from a JSONL entry."""
        if "message" in entry:
            msg = entry["message"]
            if isinstance(msg, dict):
                content = msg.get("content", "")

                if isinstance(content, list):
                    text_parts = []
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            text_parts.append(item.get("text", ""))
                        elif isinstance(item, str):
                            text_parts.append(item)
                    return " ".join(text_parts)
                elif isinstance(content, str):
                    return content

        return ""

    def _calculate_relevance(
        self, content: str, query: str, query_tokens: Set[str], case_sensitive: bool
    ) -> float:
        """Calculate relevance score for content against query."""
        relevance = 0.0

        if not case_sensitive:
            content_lower = content.lower()
            query_lower = query.lower()
        else:
            content_lower = content
            query_lower = query

        # Exact match bonus
        if query_lower in content_lower:
            relevance += 0.5
            count = content_lower.count(query_lower)
            relevance += min(0.3, count * 0.1)

        # Token overlap
        content_tokens = set(content_lower.split()) - self.stop_words
        if query_tokens and content_tokens:
            overlap = len(query_tokens & content_tokens)
            relevance += min(0.4, overlap / len(query_tokens) * 0.4)

        return min(1.0, relevance)

    def _extract_context(
        self, content: str, query: str, case_sensitive: bool, context_size: int = 300
    ) -> str:
        """Extract context around the match for display."""
        if not case_sensitive:
            pos = content.lower().find(query.lower())
        else:
            pos = content.find(query)

        if pos == -1:
            # No exact match, return beginning of content
            return content[:context_size] + ("..." if len(content) > context_size else "")

        # Extract context around match
        half_context = context_size // 2
        start = max(0, pos - half_context)
        end = min(len(content), pos + len(query) + half_context)

        context = content[start:end]

        if start > 0:
            context = "..." + context
        if end < len(content):
            context = context + "..."

        return context

    def _parse_timestamp(self, timestamp_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO timestamp string to datetime."""
        if not timestamp_str:
            return None
        try:
            return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except ValueError:
            return None
