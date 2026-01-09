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

## Session Storage

Claude Code stores sessions in: `~/.claude/projects/-{encoded-path}/`

Path encoding: `/Users/foo/project` → `-Users-foo-project`

## Development

```bash
git clone https://github.com/victor-software-house/claude-conversation-extractor.git
cd claude-conversation-extractor
pip install -e .
python -m pytest tests/
```

## License

MIT
