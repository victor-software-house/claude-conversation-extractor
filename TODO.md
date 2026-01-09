# Enhancement Roadmap

## Status Overview

| Feature | Status | Version |
|---------|--------|---------|
| Non-interactive CLI | ✅ Done | 2.0.0 |
| JSON output | ✅ Done | 2.0.0 |
| Project/branch/speaker filters | ✅ Done | 2.0.0 |
| `--last` flag | ✅ Done | 2.1.0 |
| Surrounding messages context | 🔲 Next | 2.2.0 |
| Parse all JSONL types | 🔲 Planned | 2.3.0 |
| Unified CLI | 🔲 Planned | 3.0.0 |
| Test suite | 🔲 Planned | 3.0.0 |
| CSV format | 🔲 Planned | 3.1.0 |
| Fuzzy matching | 🔲 Planned | 3.2.0 |
| Session DAG navigation | 🔬 Research | TBD |

---

## Parsing Gap Analysis

### Currently Parsed

| Type | Content Extracted |
|------|-------------------|
| `user` | Text content, tool results |
| `assistant` | Text content, tool use (with --detailed) |
| `system` | Generic message field only |

### Missing Types (not parsed)

| Type | Subtype | Value |
|------|---------|-------|
| `system` | `stop_hook_summary` | Hook execution, errors, prevention |
| `system` | `turn_duration` | Performance timing |
| `system` | `api_error` | Error messages, codes |
| `system` | `local_command` | Commands like /clear, /compact |
| `system` | `compact_boundary` | Context compaction points |
| `file-history-snapshot` | - | File diffs, state changes |
| `queue-operation` | - | Background task queue |
| `summary` | - | AI-generated summaries |
| `custom-title` | - | User session titles |

---

## 1. Surrounding Messages Context (Priority: HIGH)

**Goal**: Return N messages before/after a match for better context.

### Target Interface

```bash
# Search with surrounding context
claude-search "error" --before 2 --after 3    # 2 msgs before, 3 after
claude-search "error" -B 2 -A 3               # Short form
claude-search "error" --around 5              # 5 before and after
```

### Implementation

**SearchResult additions**:
```python
@dataclass
class SearchResult:
    # ... existing fields ...
    message_index: int = 0              # Position in session
    surrounding_before: List[Dict] = field(default_factory=list)
    surrounding_after: List[Dict] = field(default_factory=list)
```

**Search function changes**:
```python
def search(
    self,
    query: str,
    before_context: int = 0,
    after_context: int = 0,
    ...
) -> List[SearchResult]:
    # Store all messages in memory for a session
    messages = []
    for line_num, line in enumerate(f, 1):
        entry = json.loads(line)
        messages.append((line_num, entry))

    # On match, capture surrounding
    for i, (line_num, entry) in enumerate(messages):
        if matches_query(entry, query):
            result = SearchResult(...)
            result.message_index = i
            result.surrounding_before = messages[max(0, i-before_context):i]
            result.surrounding_after = messages[i+1:i+1+after_context]
            results.append(result)
```

**JSON output with context**:
```json
{
  "matches": [
    {
      "message_index": 15,
      "speaker": "assistant",
      "snippet": "The error occurs because...",
      "before": [
        {"index": 13, "speaker": "user", "content": "I'm getting an error"},
        {"index": 14, "speaker": "assistant", "content": "Can you share the logs?"}
      ],
      "after": [
        {"index": 16, "speaker": "user", "content": "That fixed it!"}
      ]
    }
  ]
}
```

---

## 2. Message Pagination (Priority: MEDIUM)

**Goal**: Navigate sessions by message index ranges.

### Target Interface

```bash
# View specific message range
claude-search --session abc123 --from-msg 10 --to-msg 20
claude-search --session abc123 --msg 15              # Single message
claude-search --session abc123 --tail 10             # Last 10 messages
```

### Implementation

```python
def get_messages(
    session_id: str,
    from_index: int = 0,
    to_index: int = None,
    tail: int = None,
) -> List[Dict]:
    """Get messages by index range."""
    messages = load_session_messages(session_id)

    if tail:
        return messages[-tail:]

    if to_index is None:
        to_index = len(messages)

    return messages[from_index:to_index]
```

**JSON output**:
```json
{
  "session_id": "abc123",
  "total_messages": 45,
  "range": {"from": 10, "to": 20},
  "messages": [
    {"index": 10, "type": "user", "content": "...", "timestamp": "..."},
    {"index": 11, "type": "assistant", "content": "...", "timestamp": "..."}
  ]
}
```

---

## 3. Session DAG Research (Priority: RESEARCH)

**Goal**: Understand and expose conversation branching structure.

### Observed Fields

Every JSONL entry has:
```json
{
  "uuid": "entry-unique-id",
  "parentUuid": "parent-entry-id",
  "sessionId": "session-uuid",
  "isSidechain": false
}
```

### Research Questions

1. **What creates branches?**
   - Does `/undo` create a branch?
   - Does `/retry` create a sidechain?
   - What sets `isSidechain: true`?

2. **Cross-session linking?**
   - Can `parentUuid` point to another session?
   - How does `/resume` work across sessions?
   - What links compacted conversations?

3. **DAG structure**
   - Is it a tree or true DAG (multiple parents)?
   - How deep can branches go?
   - Are orphan nodes possible?

### Investigation Commands

```bash
# Find entries with isSidechain=true
jq -c 'select(.isSidechain == true)' session.jsonl

# Find parentUuid patterns
jq -r '[.uuid, .parentUuid] | @tsv' session.jsonl | head -20

# Check for cross-session references
jq -r '.parentUuid' session.jsonl | sort -u > parents.txt
jq -r '.uuid' session.jsonl | sort -u > uuids.txt
comm -23 parents.txt uuids.txt  # Parents not in this session
```

### Potential Features

Once understood:
- `claude-history tree <session>` - Visualize conversation branches
- `claude-history branch <uuid>` - Show branch from point
- `claude-history merge <uuid1> <uuid2>` - Compare divergent paths

---

## 4. Parse All JSONL Types (Priority: MEDIUM)

**Goal**: Extract value from all entry types.

### Implementation per Type

**system/stop_hook_summary**:
```python
if entry.get("subtype") == "stop_hook_summary":
    return {
        "type": "hook",
        "count": entry.get("hookCount"),
        "commands": [h.get("command") for h in entry.get("hookInfos", [])],
        "errors": entry.get("hookErrors", []),
        "prevented": entry.get("preventedContinuation"),
        "output": entry.get("hasOutput"),
    }
```

**system/api_error**:
```python
if entry.get("subtype") == "api_error":
    return {
        "type": "error",
        "error": entry.get("error"),
        "timestamp": entry.get("timestamp"),
    }
```

**custom-title**:
```python
if entry.get("type") == "custom-title":
    return {
        "type": "title",
        "title": entry.get("title"),
    }
```

**summary**:
```python
if entry.get("type") == "summary":
    return {
        "type": "summary",
        "content": entry.get("summary"),
        "timestamp": entry.get("timestamp"),
    }
```

---

## 5. Unified CLI (Priority: MEDIUM)

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

1. **Surrounding Messages** - Add `-B`/`-A` context flags (v2.2.0)
2. **Message Pagination** - Add `--from-msg`/`--to-msg` flags (v2.2.0)
3. **Parse All Types** - Extract all JSONL entry types (v2.3.0)
4. **Unified CLI** - Restructure into subcommands (v3.0.0)
5. **Test Suite** - Add pytest infrastructure (v3.0.0)
6. **CSV Format** - Simple addition (v3.1.0)
7. **Fuzzy Matching** - Optional enhancement (v3.2.0)
8. **Session DAG** - Research and implement (TBD)

## File Change Summary

| Task | Files to Create | Files to Modify |
|------|-----------------|-----------------|
| Surrounding Messages | - | `src/search_conversations.py`, `src/search_cli.py` |
| Message Pagination | - | `src/search_cli.py` |
| Parse All Types | - | `src/search_conversations.py`, `src/extract_claude_logs.py` |
| Unified CLI | `src/cli.py`, `src/commands/*.py` | `pyproject.toml` |
| Test Suite | `tests/**/*.py`, `conftest.py` | `pyproject.toml` |
| CSV Format | - | `src/search_cli.py` |
| Fuzzy Matching | - | `src/search_conversations.py`, `pyproject.toml` |
| Session DAG | `src/dag.py` | TBD |
