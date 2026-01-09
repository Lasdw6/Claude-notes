# Design Intent Layer Plugin for Claude Code

A Claude Code plugin that maintains persistent, file-level design notes serving as "contracts" to prevent accidental violations of design intent, assumptions, and intentional shortcuts across LLM sessions.

## Overview

When working with LLMs on code, critical context about design decisions, assumptions, and intentional tradeoffs often gets lost across sessions. This plugin solves that problem by:

1. **Storing persistent design notes** outside source files in `.claude/notes/`
2. **Automatically injecting notes** into Claude's context before file modifications
3. **Requiring explicit acknowledgment** from Claude before changes
4. **Detecting conflicts** when changes violate documented assumptions or frozen sections
5. **Allowing notes to evolve** through Claude-proposed updates with user approval

## Features

- **File-level Design Notes**: Capture intent, assumptions, constraints, and tradeoffs per file
- **PreToolUse Hook Integration**: Automatically loads notes before Write/Edit operations
- **Frozen Sections**: Mark code patterns or line ranges as unchangeable
- **Conflict Detection**: Heuristic-based detection of assumption violations
- **Version Control Friendly**: JSON storage, easy to diff and commit
- **Interactive CLI**: `/note` command for creating and managing notes
- **Note Evolution**: Claude can propose updates when intent changes

## Installation

### Prerequisites

- Claude Code CLI installed
- Python 3.7+ available in PATH

### Install Plugin

**Option 1: Install from local directory (for testing/development)**
```bash
/plugin install "C:\Desktop\Claude Notes"
```

**Option 2: Install from git repository**
```bash
/plugin install git+https://github.com/Lasdw6/Claude-notes
```

**Option 3: Manual installation (alternative)**
1. Copy plugin to Claude plugins directory:
   ```bash
   cp -r "C:\Desktop\Claude Notes" ~/.claude/plugins/design-intent-layer
   ```

2. Add to `.claude/settings.json`:
   ```json
   {
     "plugins": [
       {
         "path": "~/.claude/plugins/design-intent-layer"
       }
     ]
   }
   ```

### Verify Installation

After installing, verify the plugin is working:
```bash
/note help
```

You should see the help message for the `/note` command.

## Quick Start

### 1. Create a Design Note

```bash
/note create src/components/Button.tsx
```

You'll be prompted to enter:
- **Purpose**: Why this file exists
- **Key Decisions**: Important design choices made
- **Assumptions**: What the code assumes (e.g., "async operations", "max 1000 items")
- **Constraints**: Requirements that must be maintained (e.g., "backward compatible")
- **Tradeoffs**: Intentional shortcuts or technical debt
- **Frozen Sections**: Code that should not be modified

### 2. View a Note

```bash
/note view src/components/Button.tsx
```

### 3. Modify the File

When Claude tries to modify `Button.tsx`, the hook will:
1. Load the design note
2. Inject it into Claude's context
3. Require Claude to acknowledge constraints
4. Block if frozen sections are violated

### 4. List All Notes

```bash
/note list
```

## Usage

### Creating Effective Notes

**Good Note Structure:**

```yaml
Purpose: "Primary button component for all form submissions"

Key Decisions:
  - "Uses Tailwind for styling to match design system"
  - "Supports loading state to prevent double-submission"
  - "Disabled state includes cursor-not-allowed"

Assumptions:
  - "All form submissions are async (2-10 seconds)" [CRITICAL]
  - "Parent components manage loading state via props" [MEDIUM]

Constraints:
  - "Must support both <button> and <a> elements" [functional]
  - "Backward compatible with existing prop interface" [api]

Tradeoffs:
  - "Using inline Tailwind instead of CSS modules" [LOW debt]
    Reason: "Faster iteration during MVP"
    Repayment: "Extract to CSS modules in Sprint 8"

Frozen Sections:
  - Pattern: "export interface ButtonProps"
    Reason: "Public API - changing breaks 15+ consumers"
    Exceptions: "Adding optional properties with defaults only"
```

### Working with Frozen Sections

**Pattern-based (recommended):**
```json
{
  "pattern": "export interface UserProps",
  "reason": "Public API - breaking changes not allowed",
  "exceptions": "Adding optional properties with defaults only"
}
```

**Line-range based:**
```json
{
  "lineRange": [45, 65],
  "reason": "Critical authentication logic",
  "exceptions": "None"
}
```

### Note Proposal Workflow

When Claude detects that a note should be updated:

```
Claude: "I notice that assumption_2 about async operations no longer
         applies. The new code uses WebSocket streams.

         PROPOSED UPDATE:
         OLD: 'All operations are async and may take 2-10s'
         NEW: 'Operations use WebSocket streams for real-time updates'

         Should I update the design note?"

User: "Yes, update that. Also add a note about WebSocket reconnection."

Claude: [Updates note with proposal history]
```

## Commands

### /note create `<file_path>`
Create a new design note with interactive prompts.

### /note view `<file_path>`
Display an existing note in formatted output.

### /note edit `<file_path>`
Edit an existing note (manual JSON editing for now).

### /note delete `<file_path>`
Delete a note with confirmation.

### /note list
List all notes in the project with summaries.

### /note migrate `<old_path>` `<new_path>`
Migrate a note after file rename.

## Architecture

### Storage Structure

```
.claude/notes/
├── index.json                    # Central registry
├── <sha1-hash>/
│   └── note.json                 # Individual note
└── .cache/
    └── path-hash-cache.json     # Performance cache
```

### Note Schema

```json
{
  "version": "1.0",
  "filePath": "C:\\Projects\\src\\auth\\service.ts",
  "createdAt": "2026-01-08T10:30:00Z",
  "updatedAt": "2026-01-08T10:30:00Z",
  "designIntent": {
    "purpose": "Authentication service",
    "keyDecisions": ["Uses JWT tokens", "Session storage in Redis"],
    "rationale": "Stateless auth for horizontal scaling"
  },
  "assumptions": [
    {
      "id": "assume_1",
      "text": "Redis is always available",
      "severity": "critical"
    }
  ],
  "constraints": [
    {
      "id": "constraint_1",
      "text": "Must maintain backward compatible API",
      "type": "api",
      "reason": "External services depend on v1 endpoints"
    }
  ],
  "tradeoffs": [
    {
      "id": "tradeoff_1",
      "shortcut": "Hardcoded token expiry instead of config",
      "reason": "MVP deadline constraint",
      "debtLevel": "medium",
      "repaymentPlan": "Extract to environment config in Sprint 5"
    }
  ],
  "frozenSections": [
    {
      "id": "frozen_1",
      "pattern": "export interface AuthTokens",
      "reason": "Public API contract",
      "exceptions": "Adding optional fields only"
    }
  ],
  "requiresAcknowledgment": true,
  "tags": ["auth", "critical-path"]
}
```

### Hook Flow

1. **PreToolUse fires** for Write/Edit operations
2. **Extract file path** from tool parameters
3. **Normalize path** and compute SHA1 hash
4. **Load note** from `.claude/notes/<hash>/note.json`
5. **Check frozen sections** - block if violated
6. **Detect conflicts** (assumptions, breaking changes)
7. **Inject note** into Claude's context with acknowledgment requirement
8. **Verify acknowledgment** (pattern matching)
9. **Allow or block** execution

### Conflict Detection

**Frozen Section Violations (BLOCKING):**
- Pattern matches new content and has changed
- Line range overlaps with edit range
- No valid exception applies

**Assumption Violations (WARNING):**
- Async → Sync conversions detected
- Required dependencies missing
- Concurrency in single-threaded code

**Breaking Changes (WARNING):**
- Interface/type properties removed
- Function signatures modified
- Public API changes

## Configuration

### Plugin Settings

In `.claude-plugin/plugin.json`:

```json
{
  "name": "design-intent-layer",
  "displayName": "Design Intent Layer",
  "version": "1.0.0",
  "hooks": "./hooks/hooks.json",
  "commands": {
    "note": "./commands/note.md"
  },
  "permissions": {
    "allow": ["Read", "Write", "Edit", "Bash"]
  }
}
```

### Hook Configuration

In `hooks/hooks.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "python \"${CLAUDE_PLUGIN_ROOT}/hooks/pre_tool_use.py\"",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

## Best Practices

### When to Create Notes

✅ **DO create notes for:**
- Public APIs and interfaces
- Critical business logic
- Files with intentional technical debt
- Complex algorithms with specific assumptions
- Authentication/security-sensitive code
- Files that break often due to lost context

❌ **DON'T create notes for:**
- Trivial utility functions
- Auto-generated code
- Temporary test files
- Self-documenting simple components

### Writing Effective Assumptions

**Good:**
- "All database queries use connection pooling with max 10 connections"
- "User input is pre-sanitized by middleware before reaching this layer"
- "File uploads are limited to 10MB by nginx config"

**Bad:**
- "Code is async" (too vague)
- "Uses database" (obvious)
- "Works correctly" (meaningless)

### Frozen Section Guidelines

- **Use patterns over line ranges** (more stable across refactors)
- **Document exceptions explicitly** (what changes ARE allowed?)
- **Keep frozen sections minimal** (only truly critical code)
- **Review frozen sections regularly** (can they be unfrozen?)

## Troubleshooting

### Hook Not Firing

1. Check plugin is enabled in settings
2. Verify Python is in PATH: `python --version`
3. Check hook logs: `claude --verbose`
4. Verify `hooks/pre_tool_use.py` has execute permissions

### Note Not Found

1. Check file path is correct (absolute vs relative)
2. Verify note exists: `/note list`
3. Check `.claude/notes/index.json` for entry
4. Try recreating with `/note create`

### Schema Validation Errors

1. Load note: `cat .claude/notes/<hash>/note.json`
2. Validate JSON syntax
3. Check required fields: version, filePath, createdAt, updatedAt
4. Verify severity values: critical/medium/low
5. Verify debt levels: high/medium/low

### False Positive Conflicts

The conflict detection uses heuristics and may have false positives. If Claude is blocked incorrectly:

1. Update the frozen section exceptions
2. Modify assumption wording to be more specific
3. Report issue for heuristic improvement

## Development

### Running Tests

```bash
cd tests/
python -m pytest
```

### Project Structure

```
design-intent-layer/
├── .claude-plugin/
│   └── plugin.json           # Plugin metadata
├── hooks/
│   ├── hooks.json           # Hook configuration
│   └── pre_tool_use.py      # PreToolUse hook script
├── lib/
│   ├── __init__.py
│   ├── path_utils.py        # Path normalization and hashing
│   ├── note_manager.py      # CRUD operations
│   ├── acknowledgment_verifier.py
│   └── conflict_detection.py
├── commands/
│   ├── note.md              # Command definition
│   └── note_handler.py      # Command implementation
└── README.md
```

## Limitations

- **Heuristic conflict detection**: Not perfect, may miss violations or have false positives
- **Pattern matching**: Frozen section patterns must be carefully crafted
- **Line ranges**: Unstable across refactors, prefer patterns
- **Manual editing**: `/note edit` requires manual JSON editing (for now)
- **Single file scope**: No directory or project-level notes yet

## Roadmap

- [ ] AI-powered semantic conflict detection
- [ ] Directory and project-level notes
- [ ] Function/class-level granular notes
- [ ] `/note edit` interactive mode
- [ ] Note templates for common patterns
- [ ] Integration with external tools (Jira, Linear)
- [ ] Automatic staleness detection
- [ ] MCP server exposing note operations

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

- GitHub Issues: [Report bugs or request features]
- Documentation: This README
- Examples: See `examples/` directory

## Acknowledgments

Built for the Claude Code plugin ecosystem. Inspired by the need to preserve design intent across LLM-assisted development sessions.
