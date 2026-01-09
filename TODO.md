# Enhancement Roadmap

## Status Overview

| Feature | Status | Version |
|---------|--------|---------|
| Non-interactive CLI | ✅ Done | 2.0.0 |
| JSON output | ✅ Done | 2.0.0 |
| Project/branch/speaker filters | ✅ Done | 2.0.0 |
| `--last` flag | ✅ Done | 2.1.0 |
| Unified CLI | 🔲 Next | 3.0.0 |
| Test suite | 🔲 Planned | 3.0.0 |
| CSV format | 🔲 Planned | 3.1.0 |
| Fuzzy matching | 🔲 Planned | 3.2.0 |

---

## 1. Unified CLI (Priority: HIGH)

**Goal**: Single entry point `claude-history` with subcommands.

### Target Interface

```bash
claude-history search "query" [options]
claude-history list [options]
claude-history export <session-id|--last|--all> [options]
claude-history view <session-id|--last>
```

### Implementation

**File**: `src/cli.py` (new)

```python
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(prog='claude-history')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # search subcommand
    search_parser = subparsers.add_parser('search')
    search_parser.add_argument('query', nargs='?')
    # ... add all search flags from search_cli.py

    # list subcommand
    list_parser = subparsers.add_parser('list')
    list_parser.add_argument('--limit', type=int)
    list_parser.add_argument('--project', type=str)
    list_parser.add_argument('--json', action='store_true')

    # export subcommand
    export_parser = subparsers.add_parser('export')
    export_parser.add_argument('session_id', nargs='?')
    export_parser.add_argument('--last', nargs='?', const=1, type=int)
    export_parser.add_argument('--all', action='store_true')
    export_parser.add_argument('--recent', type=int)
    export_parser.add_argument('--format', choices=['markdown','json','html','csv'])
    export_parser.add_argument('--output', '-o', type=str)
    export_parser.add_argument('--detailed', action='store_true')

    # view subcommand
    view_parser = subparsers.add_parser('view')
    view_parser.add_argument('session_id', nargs='?')
    view_parser.add_argument('--last', action='store_true')

    args = parser.parse_args()

    if args.command == 'search':
        from .commands.search import run
        return run(args)
    elif args.command == 'list':
        from .commands.list import run
        return run(args)
    # ... etc

if __name__ == '__main__':
    sys.exit(main())
```

**Directory structure**:
```
src/
├── cli.py                 # Main entry point
├── commands/
│   ├── __init__.py
│   ├── search.py          # Move from search_cli.py
│   ├── list.py            # New
│   ├── export.py          # New
│   └── view.py            # New
├── extract_claude_logs.py # Keep as-is
└── search_conversations.py # Keep as-is
```

**pyproject.toml update**:
```toml
[project.scripts]
claude-history = "claude_conversation_extractor.cli:main"
# Keep old entry points for backward compatibility
claude-search = "claude_conversation_extractor.search_cli:main"
claude-extract = "claude_conversation_extractor.extract_claude_logs:main"
```

### List Command Output

```
$ claude-history list
  #  Project              Branch      Messages  Size    Modified
───────────────────────────────────────────────────────────────────
  1  EvoSiteMaster        main        45        12KB    10 min ago
     "Help me implement the authentication..."
  2  doc-toolkit          feat/cli    23        8KB     2 hours ago
     "Add fuzzy search to the CLI..."
```

JSON mode:
```json
{
  "sessions": [
    {
      "number": 1,
      "session_id": "abc123...",
      "project": "EvoSiteMaster",
      "cwd": "/path/to/project",
      "branch": "main",
      "message_count": 45,
      "size_bytes": 12288,
      "modified": "2026-01-09T10:30:00",
      "preview": "Help me implement..."
    }
  ]
}
```

---

## 2. Test Suite (Priority: HIGH)

**Framework**: pytest + pytest-cov

### Setup

```toml
# pyproject.toml additions
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]

[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-cov>=4.0"]
```

### Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Fixtures
├── fixtures/
│   ├── sample_session.jsonl # Real format sample
│   └── multi_session/       # Multiple sessions
├── unit/
│   ├── test_search.py
│   ├── test_extract.py
│   └── test_cli.py
└── integration/
    └── test_workflows.py
```

### Key Fixtures (`conftest.py`)

```python
import pytest
from pathlib import Path
import tempfile
import json

@pytest.fixture
def sample_session(tmp_path):
    """Create a sample JSONL session file."""
    session_dir = tmp_path / ".claude" / "projects" / "-test-project"
    session_dir.mkdir(parents=True)

    session_file = session_dir / "abc123.jsonl"
    messages = [
        {"type": "user", "message": {"role": "user", "content": "Hello"}, "timestamp": "2026-01-09T10:00:00Z"},
        {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "Hi there!"}]}, "timestamp": "2026-01-09T10:00:05Z"},
    ]
    with open(session_file, 'w') as f:
        for msg in messages:
            f.write(json.dumps(msg) + '\n')

    return session_file

@pytest.fixture
def mock_claude_dir(tmp_path, monkeypatch):
    """Mock ~/.claude directory."""
    monkeypatch.setenv('HOME', str(tmp_path))
    return tmp_path / ".claude"
```

### Test Cases

**test_search.py**:
```python
def test_smart_search_finds_match(sample_session):
    searcher = ConversationSearcher()
    results = searcher.search("Hello", mode="smart")
    assert len(results) >= 1
    assert "Hello" in results[0].matched_content

def test_regex_search(sample_session):
    results = searcher.search(r"H[ea]llo", mode="regex")
    assert len(results) >= 1

def test_project_filter(mock_claude_dir):
    results = searcher.search("test", project_filter="test-project")
    # Assert only test-project results

def test_no_results_returns_empty():
    results = searcher.search("nonexistent-xyz-123")
    assert results == []
```

**test_cli.py**:
```python
import subprocess

def test_json_output_valid():
    result = subprocess.run(
        ['claude-search', 'test', '--json', '--quiet'],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    assert 'results' in data
    assert 'total_matches' in data

def test_exit_code_not_found():
    result = subprocess.run(
        ['claude-search', 'nonexistent-xyz-123', '--quiet'],
        capture_output=True
    )
    assert result.returncode == 1

def test_last_flag_outputs_markdown():
    result = subprocess.run(
        ['claude-search', '--last', '--quiet'],
        capture_output=True, text=True
    )
    assert '# Claude Conversation Log' in result.stdout
```

---

## 3. CSV Format (Priority: LOW)

### Schema

```csv
session_id,project,branch,timestamp,speaker,relevance,content
abc123,EvoSiteMaster,main,2026-01-09T10:30:00,human,1.0,"Help me implement..."
abc123,EvoSiteMaster,main,2026-01-09T10:30:15,assistant,0.9,"I'll help you..."
```

### Implementation

Add to `search_cli.py`:

```python
import csv
from io import StringIO

def format_csv_output(results: List[SearchResult], query: str) -> str:
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['session_id', 'project', 'branch', 'timestamp', 'speaker', 'relevance', 'content'])

    for result in results:
        writer.writerow([
            result.session_id,
            result.project_name or result._extract_project_name(),
            result.git_branch or '',
            result.timestamp.isoformat() if result.timestamp else '',
            result.speaker,
            round(result.relevance_score, 3),
            result.context.replace('\n', ' ')[:500]
        ])

    return output.getvalue()
```

Update argparse:
```python
parser.add_argument('--format', choices=['text', 'json', 'csv'], default='text')
```

---

## 4. Fuzzy Matching (Priority: LOW)

### Approach

Use `rapidfuzz` as optional dependency with fallback.

```toml
[project.optional-dependencies]
fuzzy = ["rapidfuzz>=3.0"]
```

### Implementation

```python
# search_conversations.py

try:
    from rapidfuzz import fuzz
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False

def fuzzy_match(query: str, content: str, threshold: float = 0.6) -> float:
    """Return similarity score 0-1."""
    if HAS_RAPIDFUZZ:
        return fuzz.token_set_ratio(query.lower(), content.lower()) / 100.0
    else:
        # Simple fallback: token overlap
        query_tokens = set(query.lower().split())
        content_tokens = set(content.lower().split())
        if not query_tokens:
            return 0.0
        matches = sum(1 for qt in query_tokens if any(qt in ct or ct in qt for ct in content_tokens))
        return matches / len(query_tokens)

def search(self, query: str, mode: str = "smart", ...):
    if mode == "fuzzy":
        # Use fuzzy_match for scoring
        score = fuzzy_match(query, content)
        if score >= threshold:
            results.append(...)
```

---

## Implementation Order

1. **Unified CLI** - Restructure into subcommands
2. **Test Suite** - Add pytest infrastructure
3. **CSV Format** - Simple addition
4. **Fuzzy Matching** - Optional enhancement

## File Change Summary

| Task | Files to Create | Files to Modify |
|------|-----------------|-----------------|
| Unified CLI | `src/cli.py`, `src/commands/*.py` | `pyproject.toml` |
| Test Suite | `tests/**/*.py`, `conftest.py` | `pyproject.toml` |
| CSV Format | - | `src/search_cli.py` |
| Fuzzy Matching | - | `src/search_conversations.py`, `pyproject.toml` |
