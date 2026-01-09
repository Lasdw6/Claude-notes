allowed-tools: Bash(python3 *note_handler.py*)

description: Manage design intent notes for files in your codebase. Create, view, edit, list, delete, and migrate design notes that capture intent, assumptions, constraints, and tradeoffs to prevent violations across LLM sessions.

---

You have access to a `/note` command system for managing design intent notes. Execute the command by running the note_handler.py script located in the plugin directory.

## Available Actions

- **create <file_path>** - Create a new design note with interactive prompts
- **view <file_path>** - Display an existing design note
- **edit <file_path>** - Edit an existing design note (manual JSON editing)
- **delete <file_path>** - Delete a design note with confirmation
- **list** - List all design notes in the project
- **migrate <old_path> <new_path>** - Migrate note after file rename
- **help** - Show help message

## Execution

Parse the user's command arguments and execute:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/commands/note_handler.py <action> [arguments]
```

For example:
- `/note create src/file.ts` → `python3 ${CLAUDE_PLUGIN_ROOT}/commands/note_handler.py create src/file.ts`
- `/note list` → `python3 ${CLAUDE_PLUGIN_ROOT}/commands/note_handler.py list`
- `/note view src/file.ts` → `python3 ${CLAUDE_PLUGIN_ROOT}/commands/note_handler.py view src/file.ts`

## Interactive Commands

For `create`, the script will prompt the user interactively for:
1. Design intent (purpose, key decisions, rationale)
2. Assumptions (with severity levels)
3. Constraints (with types and reasons)
4. Known tradeoffs (with debt levels and repayment plans)
5. Frozen sections (patterns or line ranges that cannot be modified)
6. Tags

## Output

Display the script's output directly to the user. Do not add commentary before or after the command execution - let the script handle all user interaction.

## Error Handling

If the command fails, display the error message from the script and suggest corrective actions based on the error.
