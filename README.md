# Claude Conversation Extractor

Export and search Claude Code conversations from `~/.claude/projects/`.

**Fork**: [victor-software-house/claude-conversation-extractor](https://github.com/victor-software-house/claude-conversation-extractor) (non-interactive CLI for scripting/plugins)

## Installation

```bash
pipx install git+https://github.com/victor-software-house/claude-conversation-extractor.git
```

## CLI Reference

### claude-search

Non-interactive search and export tool.

```bash
# Search
claude-search "query"                    # Text search
claude-search --pattern "import.*"       # Regex search
claude-search "bug" --project MyProject  # Filter by project
claude-search "fix" --branch main        # Filter by branch
claude-search "api" --json --quiet       # JSON output

# Export last session
claude-search --last                     # Markdown to stdout
claude-search --last 3                   # Last 3 sessions
claude-search --last --format json       # JSON format
claude-search --last -o output.md        # Save to file
claude-search --last --detailed          # Include tool use
claude-search --last --global            # All projects
```

**Search Flags:**
| Flag | Description |
|------|-------------|
| `--pattern`, `-p` | Regex pattern search |
| `--global`, `-g` | Search all projects |
| `--project` | Filter by project name/path |
| `--session-id` | Filter by session ID |
| `--branch` | Filter by git branch |
| `--speaker` | Filter: human/assistant/tool |
| `--show-tools`, `-t` | Include tool calls |
| `--from`, `--to` | Date range (YYYY-MM-DD) |
| `--json`, `-j` | JSON output |
| `--quiet`, `-q` | Suppress decorations |
| `--limit`, `-l` | Max results (default: 10) |
| `--context`, `-c` | Snippet size (default: 300) |

**Export Flags:**
| Flag | Description |
|------|-------------|
| `--last`, `-L` | Export last N sessions |
| `--format`, `-f` | markdown/json/html |
| `--output`, `-o` | Output file path |
| `--detailed`, `-d` | Include tool use/system msgs |

**Exit Codes:** 0=found, 1=not found, 2=error

### claude-extract

Interactive extraction tool.

```bash
claude-extract --list                    # List sessions
claude-extract --extract 1,3,5           # Extract by number
claude-extract --recent 5                # Extract recent
claude-extract --all                     # Extract all
claude-extract --format json --all       # JSON format
claude-extract --detailed --extract 1    # Include tool use
```

### claude-start

Interactive UI with ASCII art and real-time search.

## JSON Output Schema

### Search Results

```json
{
  "query": "search term",
  "total_matches": 5,
  "sessions_matched": 2,
  "results": [
    {
      "session_id": "abc123...",
      "project": "ProjectName",
      "cwd": "/path/to/project",
      "git_branch": "main",
      "matches": [
        {
          "speaker": "assistant",
          "timestamp": "2026-01-09T10:30:00",
          "relevance": 0.95,
          "snippet": "matching content...",
          "line_number": 42
        }
      ]
    }
  ]
}
```

## JSONL Schema Reference

Claude Code stores sessions as JSONL files in `~/.claude/projects/-{encoded-path}/`.

### Entry Types

| Type | Subtype | Parsed | Description |
|------|---------|--------|-------------|
| `user` | - | ✅ | User messages + tool results |
| `assistant` | - | ✅ | Claude responses + tool use |
| `system` | `stop_hook_summary` | ⚠️ partial | Hook execution results |
| `system` | `turn_duration` | ❌ | Performance metrics |
| `system` | `api_error` | ❌ | API errors |
| `system` | `local_command` | ❌ | Local commands (/clear, etc.) |
| `system` | `compact_boundary` | ❌ | Context compaction markers |
| `file-history-snapshot` | - | ❌ | File state snapshots |
| `queue-operation` | - | ❌ | Operation queue entries |
| `summary` | - | ❌ | Conversation summaries |
| `custom-title` | - | ❌ | User-set session titles |

### Entry Structure

Common fields across all entries:
```json
{
  "type": "user|assistant|system|...",
  "subtype": "optional subtype",
  "uuid": "entry-unique-id",
  "parentUuid": "parent-entry-id",
  "sessionId": "session-uuid",
  "timestamp": "ISO8601",
  "cwd": "/project/path",
  "gitBranch": "branch-name",
  "version": "claude-code-version"
}
```

### Message Content Types

Within `user` and `assistant` entries, `message.content` is an array:
```json
{
  "type": "user",
  "message": {
    "role": "user",
    "content": [
      {"type": "text", "text": "..."},
      {"type": "tool_result", "tool_use_id": "...", "content": "..."},
      {"type": "tool_use", "id": "...", "name": "Bash", "input": {...}}
    ]
  }
}
```

### Hook Summary Structure

```json
{
  "type": "system",
  "subtype": "stop_hook_summary",
  "hookCount": 1,
  "hookInfos": [{"command": "python3 hooks/stop.py"}],
  "hookErrors": [],
  "preventedContinuation": false,
  "hasOutput": true,
  "level": "suggestion"
}
```

### Session DAG Structure

Sessions form a DAG (Directed Acyclic Graph) via `parentUuid`:
- Each entry has `uuid` (self) and `parentUuid` (parent)
- Root entries have `parentUuid` pointing to previous turn
- Enables branching conversations and context tracking

## Pagination & Context

### Current Limitations

1. **Search returns snippets only** - no surrounding messages
2. **No message-level pagination** - full session or nothing
3. **Line numbers don't map to message indices**

### Workaround: Export + grep

```bash
# Export session, then grep with context
claude-search --last --format json | jq -r '.messages[].content' | grep -B5 -A5 "pattern"
```

## Session Storage

Path encoding: `/Users/foo/project` → `-Users-foo-project`

```
~/.claude/
└── projects/
    └── -Users-foo-project/
        ├── abc123-uuid.jsonl    # Session file
        └── def456-uuid.jsonl    # Another session
```

## Development

```bash
git clone https://github.com/victor-software-house/claude-conversation-extractor.git
cd claude-conversation-extractor
pip install -e .
python -m pytest tests/
```

## License

MIT
