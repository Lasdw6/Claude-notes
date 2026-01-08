# /note Command

Manage design intent notes for files in your codebase.

## Usage

```
/note <action> [file_path] [options]
```

## Actions

### create
Create a new design note for a file with interactive prompts.

```bash
/note create <file_path>
```

Example:
```bash
/note create src/components/Button.tsx
```

### view
Display an existing design note in formatted output.

```bash
/note view <file_path>
```

Example:
```bash
/note view src/components/Button.tsx
```

### edit
Edit an existing design note.

```bash
/note edit <file_path>
```

### delete
Delete a design note (with confirmation).

```bash
/note delete <file_path>
```

### list
List all design notes in the current project.

```bash
/note list
```

### migrate
Migrate a note from old file path to new file path (for file renames).

```bash
/note migrate <old_path> <new_path>
```

Example:
```bash
/note migrate old/Button.tsx src/components/Button.tsx
```

### help
Show this help message.

```bash
/note help
```

## Description

The Design Intent Layer plugin maintains persistent, file-level design notes that serve as "contracts" to prevent accidental violations of design intent, assumptions, and intentional shortcuts across LLM sessions.

Each note contains:
- **Design Intent**: Purpose, key decisions, and rationale
- **Assumptions**: What the code assumes (e.g., "async operations", "single-threaded")
- **Constraints**: Requirements that must be maintained (e.g., "backward compatible API")
- **Tradeoffs**: Intentional shortcuts or technical debt
- **Frozen Sections**: Code patterns or line ranges that should not be modified

Before Claude modifies a file with a design note, the note is automatically injected into the context and Claude must explicitly acknowledge understanding of the constraints.

## Examples

### Creating a Note

```bash
/note create src/auth/service.ts
```

You'll be prompted for:
1. Purpose of the file
2. Key design decisions
3. Assumptions the code makes
4. Constraints that must be maintained
5. Known tradeoffs or shortcuts
6. Frozen sections (optional)

### Viewing a Note

```bash
/note view src/auth/service.ts
```

Displays formatted output with all note sections, severity indicators, and metadata.

### Listing All Notes

```bash
/note list
```

Shows all notes in the project with summaries and critical status.

### Migrating After File Rename

```bash
/note migrate src/old-name.ts src/new-name.ts
```

Moves the design note to the new file path and records the migration history.

## Note Storage

Notes are stored in `.claude/notes/` directory with SHA1-hashed subdirectories for each file path. The structure is:

```
.claude/notes/
├── index.json              # Central registry
├── <file-path-hash>/
│   └── note.json          # Individual note
└── .cache/
    └── path-hash-cache.json
```

Notes are version-controlled alongside your code and should be committed to git.
