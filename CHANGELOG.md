# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Unified CLI with subcommands (`search`, `list`, `export`, `view`)
- Fuzzy matching for improved search relevance
- CSV output format
- Comprehensive test suite

---

## [2.1.0] - 2026-01-09

### Added
- **`--last` flag** (`-L`) - Export the last N sessions for current project
  - `claude-search --last` - Export last session as markdown to stdout
  - `claude-search --last 3` - Export last 3 sessions
  - `claude-search --last --format json` - Export as JSON
  - `claude-search --last --format html -o file.html` - Export as HTML to file
  - `claude-search --last --detailed` - Include tool use, MCP, system messages
  - `claude-search --last --global` - Last session across all projects
- **`--format` flag** (`-f`) - Choose output format (markdown, json, html)
- **`--output` flag** (`-o`) - Save to file instead of stdout
- **`--detailed` flag** (`-d`) - Include tool use and system messages in export
- Helper functions for project session detection (`encode_project_path`, `find_project_sessions_dir`, `get_last_sessions`)

---

## [2.0.0] - 2026-01-09

### ⚠️ BREAKING CHANGES
- **Removed interactive mode** from `claude-search` - now fully non-interactive
- **Removed spacy dependency** - was slow, inaccurate, and printed warnings at import time
- **Changed default behavior** - no more V/E/Q menu prompts

### Added
- **JSON output** (`--json`, `-j`) - Machine-readable output for scripting and plugin integration
- **Quiet mode** (`--quiet`, `-q`) - Suppress all decorations and warnings
- **Project filtering** (`--project NAME`) - Filter by project name or path (matches against cwd)
- **Session ID filtering** (`--session-id UUID`) - Filter by specific session ID (partial match)
- **Branch filtering** (`--branch NAME`) - Filter by git branch name
- **Speaker filtering** (`--speaker human|assistant|tool`) - Filter by message author
- **Tool call inclusion** (`--show-tools`, `--no-tools`) - Control tool call visibility in results
- **Regex pattern search** (`--pattern REGEX`, `-p`) - Search using regular expressions
- **Global search** (`--global`, `-g`) - Search across all projects
- **Relative timestamps** (`--relative-time`, `-r`) - Display "10 minutes ago" style timestamps
- **Result limits** (`--limit N`, `-l`) - Control maximum results returned (default: 10)
- **Context size control** (`--context N`, `-c`) - Control snippet size in characters (default: 300)
- **Proper exit codes** - 0 (found), 1 (not found), 2 (error) for shell scripting

### Changed
- `SearchResult` dataclass now includes `cwd`, `git_branch`, `project_name` fields
- Results are grouped by session in JSON output for better structure
- Default result limit changed from 20 to 10 for more manageable output
- Improved relevance scoring without spacy dependency

### Removed
- spacy/NLP semantic search (was optional, slow, and printed import warnings)
- Interactive V/E/Q menu in `claude-search`
- Terminal control sequences and raw input handling in search CLI

### Fixed
- No more "Install spacy for enhanced semantic search" warnings
- No more hanging on interactive prompts when run from scripts/plugins

---

## [1.1.2] - 2025-01-08

### Fixed
- Allow manual workflow dispatch to publish to PyPI
- Update pyproject.toml version consistency

---

## [1.1.1] - 2025-01-07

### Fixed
- Preview extraction now shows actual user messages instead of system content
- Search and view functionality completely overhauled
- Show all conversations by default in CLI (removed artificial limit)

### Changed
- Complete file structure reorganization
- Improved preview extraction to filter out tool results and interruptions

---

## [1.1.0] - 2025-01-06

### Added
- Interactive UI with magenta ASCII banner
- Real-time search with arrow key navigation
- Folder selection dialog for output location
- Progress display during extraction
- Option to open output folder after extraction

### Changed
- Enhanced conversation list display with previews
- Better error handling throughout

---

## [1.0.0] - 2025-01-05

### Added
- Initial release
- Extract Claude Code conversations from `~/.claude/projects/`
- Export to Markdown, JSON, and HTML formats
- Search conversations with smart, exact, and regex modes
- Date range filtering
- Speaker filtering (human/assistant)
- Session listing with metadata
- Batch extraction support
- PyPI publishing workflow

---

## Fork Information

This is a fork of [ZeroSumQuant/claude-conversation-extractor](https://github.com/ZeroSumQuant/claude-conversation-extractor) maintained at [victor-software-house/claude-conversation-extractor](https://github.com/victor-software-house/claude-conversation-extractor).

### Fork Changes (v2.0.0+)
- Non-interactive CLI design for plugin integration
- Removed spacy dependency
- Added extensive filtering options
- JSON output for machine consumption
- Proper exit codes for scripting

---

[Unreleased]: https://github.com/victor-software-house/claude-conversation-extractor/compare/v2.1.0...HEAD
[2.1.0]: https://github.com/victor-software-house/claude-conversation-extractor/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/victor-software-house/claude-conversation-extractor/compare/v1.1.2...v2.0.0
[1.1.2]: https://github.com/victor-software-house/claude-conversation-extractor/compare/v1.1.1...v1.1.2
[1.1.1]: https://github.com/victor-software-house/claude-conversation-extractor/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/victor-software-house/claude-conversation-extractor/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/victor-software-house/claude-conversation-extractor/releases/tag/v1.0.0
