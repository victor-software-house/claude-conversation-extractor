# Claude Conversation Extractor - Enhancement Roadmap

## Overview

This document tracks planned enhancements to unify and improve the CLI tools.

---

## 1. Add `--last` Flag for Current Session Export

**Priority**: High
**Status**: Pending

### Requirements
- Add `--last` / `-L` flag to get the most recent/current session
- Auto-detect current project from CWD and find matching session
- Export full conversation as markdown by default
- Support `--format` flag for JSON/HTML output

### Implementation Details

```bash
# Get last session for current project
claude --last

# Get last session and export as markdown
claude --last --export output.md

# Get last session as JSON
claude --last --json

# Get last N sessions
claude --last 3
```

### Technical Approach
1. Find sessions directory for current CWD: `~/.claude/projects/-{encoded-path}/`
2. Sort sessions by modification time (most recent first)
3. Extract and format the conversation
4. Output to stdout or file based on flags

### Files to Modify
- `src/search_cli.py` - Add `--last` argument
- `src/extract_claude_logs.py` - Add `get_last_session()` method

---

## 2. Unified CLI Interface

**Priority**: High
**Status**: Pending

### Current State (Fragmented)
```
claude-search   # Search conversations
claude-extract  # Extract to markdown (interactive)
claude-logs     # Extract to markdown (interactive)
claude-start    # Launch interactive UI
```

### Target State (Unified)
```bash
claude-history [command] [options]

# Or simply:
claude-conv [command] [options]
```

### Proposed Subcommand Structure

```bash
# Search
claude-history search "query" [options]
claude-history search --pattern "regex" [options]

# List sessions
claude-history list [options]
claude-history list --limit 10
claude-history list --project EvoSiteMaster

# Export sessions
claude-history export <session-id> [options]
claude-history export --last [options]
claude-history export --all --output ./exports/
claude-history export --recent 5 --format json

# View session (non-interactive display)
claude-history view <session-id>
claude-history view --last
```

### Backward Compatibility
- Keep old entry points as aliases for transition period
- `claude-search` → `claude-history search`
- `claude-extract` → `claude-history export --interactive`
- `claude-logs` → `claude-history list`

### Files to Create/Modify
- `src/cli.py` - New unified entry point with subcommand routing
- `src/commands/search.py` - Search subcommand
- `src/commands/list.py` - List subcommand
- `src/commands/export.py` - Export subcommand
- `src/commands/view.py` - View subcommand
- `pyproject.toml` - Update entry points

---

## 3. Port claude-logs Features

**Priority**: High
**Status**: Pending

### Features to Port from claude-logs

| Feature | Flag | Description | Status |
|---------|------|-------------|--------|
| List sessions | `--list` | Show all sessions with metadata | Pending |
| Extract by number | `--extract N` | Extract session by list number | Pending |
| Extract all | `--all` | Export all sessions | Pending |
| Extract recent | `--recent N` | Export N most recent | Pending |
| Output directory | `--output DIR` | Custom output location | Pending |
| List limit | `--limit N` | Limit list display | Pending |
| Interactive mode | `--interactive` | Launch TUI (optional) | Pending |
| Detailed export | `--detailed` | Include tool use, MCP, system msgs | Pending |
| Format selection | `--format {md,json,html}` | Output format | Pending |

### Implementation Notes

**List Command Enhancement**:
```bash
claude-history list
# Output:
#   1. [2026-01-09 10:30] EvoSiteMaster (main) - 45 messages, 12KB
#      Preview: "Help me implement the authentication..."
#   2. [2026-01-08 15:20] doc-toolkit (feat/cli) - 23 messages, 8KB
#      Preview: "Add fuzzy search to the CLI..."
```

**Detailed Export**:
- Include tool_use blocks with tool name and input
- Include tool_result blocks with output/errors
- Include system messages
- Format appropriately per output format

---

## 4. Test Suite

**Priority**: High
**Status**: Pending

### Test Categories

#### Unit Tests (`tests/unit/`)
- `test_search_conversations.py`
  - `test_smart_search_basic()`
  - `test_exact_search()`
  - `test_regex_search()`
  - `test_project_filter()`
  - `test_branch_filter()`
  - `test_speaker_filter()`
  - `test_date_range_filter()`
  - `test_relevance_scoring()`
  - `test_context_extraction()`

- `test_search_cli.py`
  - `test_json_output_format()`
  - `test_text_output_format()`
  - `test_quiet_mode()`
  - `test_exit_codes()`
  - `test_argument_parsing()`
  - `test_invalid_arguments()`

- `test_extract_claude_logs.py`
  - `test_find_sessions()`
  - `test_extract_conversation()`
  - `test_save_as_markdown()`
  - `test_save_as_json()`
  - `test_save_as_html()`
  - `test_detailed_extraction()`

#### Integration Tests (`tests/integration/`)
- `test_cli_integration.py`
  - `test_search_to_export_workflow()`
  - `test_list_to_view_workflow()`
  - `test_global_search()`

#### Fixtures (`tests/fixtures/`)
- Create sample JSONL files with various message types
- Mock session data for consistent testing

### Test Framework
```python
# pyproject.toml additions
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]

[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-cov>=4.0"]
```

### Coverage Target
- Minimum 80% code coverage
- 100% coverage for CLI argument parsing
- 100% coverage for output formatting

---

## 5. README Documentation

**Priority**: Medium
**Status**: Pending

### Documentation Structure

```markdown
# Claude Conversation Extractor

## Quick Start
- Installation
- Basic usage examples

## CLI Reference

### Search Command
- All flags with examples
- JSON output schema
- Exit codes

### List Command
- Filtering options
- Output format

### Export Command
- Format options (markdown, json, html, csv)
- Detailed mode
- Batch export

### View Command
- Display options

## Configuration
- Environment variables
- Config file (if any)

## Examples
### Search for code discussions
### Export last session
### Batch export with filters
### Integration with Claude Code plugins

## Development
- Running tests
- Contributing
```

### Example Sections to Include

```markdown
## Search Examples

\`\`\`bash
# Basic search
claude-history search "typescript error"

# Regex pattern search
claude-history search --pattern "function\s+\w+" --limit 20

# Filter by project and branch
claude-history search "api" --project EvoSiteMaster --branch main

# JSON output for scripting
claude-history search "bug" --json | jq '.results[].matches[].snippet'

# Search with date range
claude-history search "deploy" --from 2026-01-01 --to 2026-01-07
\`\`\`

## Export Examples

\`\`\`bash
# Export last session as markdown
claude-history export --last

# Export specific session as JSON
claude-history export abc123 --format json --output ./exports/

# Export all sessions with tool calls included
claude-history export --all --detailed --format html
\`\`\`
```

---

## 6. Fuzzy Matching

**Priority**: Medium
**Status**: Pending

### Approach Options

#### Option A: rapidfuzz Library
```python
from rapidfuzz import fuzz, process

def fuzzy_search(query: str, content: str, threshold: float = 0.6) -> float:
    """Return similarity score between query and content."""
    # Token set ratio handles word order variations
    return fuzz.token_set_ratio(query.lower(), content.lower()) / 100.0
```

**Pros**: Fast, accurate, well-maintained
**Cons**: Adds dependency

#### Option B: Simple Token-Based Fuzzy
```python
def simple_fuzzy(query: str, content: str) -> float:
    """Simple fuzzy matching without dependencies."""
    query_tokens = set(query.lower().split())
    content_tokens = set(content.lower().split())

    # Check for partial matches
    matches = 0
    for qt in query_tokens:
        for ct in content_tokens:
            if qt in ct or ct in qt:
                matches += 1
                break

    return matches / len(query_tokens) if query_tokens else 0.0
```

**Pros**: No dependencies
**Cons**: Less accurate

### Recommendation
Use `rapidfuzz` as optional dependency:
- If installed, use for enhanced fuzzy matching
- If not installed, fall back to simple token matching
- Add `[fuzzy]` optional dependency group

```toml
[project.optional-dependencies]
fuzzy = ["rapidfuzz>=3.0"]
```

---

## 7. CSV Format Support

**Priority**: Low
**Status**: Pending

### CSV Schema

```csv
session_id,project,branch,timestamp,speaker,content,relevance
abc123,EvoSiteMaster,main,2026-01-09T10:30:00,human,"Help me implement...",1.0
abc123,EvoSiteMaster,main,2026-01-09T10:30:15,assistant,"I'll help you...",0.9
```

### Implementation

```python
import csv
from io import StringIO

def format_csv_output(results: List[SearchResult], query: str) -> str:
    """Format results as CSV."""
    output = StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        'session_id', 'project', 'branch', 'timestamp',
        'speaker', 'relevance', 'content'
    ])

    # Data rows
    for result in results:
        writer.writerow([
            result.session_id,
            result.project_name or result._extract_project_name(),
            result.git_branch,
            result.timestamp.isoformat() if result.timestamp else '',
            result.speaker,
            result.relevance_score,
            result.context.replace('\n', ' ')[:500]
        ])

    return output.getvalue()
```

### CLI Flag
```bash
claude-history search "query" --format csv > results.csv
claude-history export --all --format csv --output ./exports/
```

---

## Implementation Order

1. **Phase 1** (Core): `--last` flag, unified CLI structure
2. **Phase 2** (Features): Port claude-logs features, CSV format
3. **Phase 3** (Quality): Test suite, documentation
4. **Phase 4** (Enhancement): Fuzzy matching

---

## Notes

- All changes should maintain backward compatibility where possible
- Exit codes must be consistent across all commands
- JSON output schema should be documented and versioned
- Consider adding `--version` flag to CLI
