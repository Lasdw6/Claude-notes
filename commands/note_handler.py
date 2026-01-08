#!/usr/bin/env python3
"""
Command handler for /note command.
Manages design intent notes through CLI interface.
"""

import sys
import os
import json
from datetime import datetime
from typing import Optional, Dict, Any

# Add lib directory to path
PLUGIN_ROOT = os.getenv('CLAUDE_PLUGIN_ROOT') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PLUGIN_ROOT, 'lib'))

from note_manager import NoteManager, NoteSchema
from path_utils import PathUtils


def print_formatted_note(note: Dict[str, Any], file_path: str):
    """Print a note in formatted output."""
    print("\n" + "=" * 80)
    print(f"DESIGN INTENT NOTE: {os.path.basename(file_path)}")
    print("=" * 80)
    print(f"\nFile: {file_path}\n")

    # Design Intent
    if 'designIntent' in note:
        intent = note['designIntent']
        print("PURPOSE:")
        print(f"  {intent.get('purpose', 'Not specified')}\n")

        if intent.get('keyDecisions'):
            print("KEY DECISIONS:")
            for decision in intent['keyDecisions']:
                print(f"  • {decision}")
            print()

        if intent.get('rationale'):
            print("RATIONALE:")
            print(f"  {intent['rationale']}\n")

    # Assumptions
    if note.get('assumptions'):
        print("ASSUMPTIONS (Must be maintained):")
        for assumption in note['assumptions']:
            severity = assumption.get('severity', 'medium').upper()
            marker = "✓" if severity != "CRITICAL" else "⚠"
            print(f"  [{severity}] {marker} {assumption['id']}: {assumption['text']}")
        print()

    # Constraints
    if note.get('constraints'):
        print("CONSTRAINTS (Active requirements):")
        for constraint in note['constraints']:
            constraint_type = constraint.get('type', 'functional')
            print(f"  [{constraint_type}] {constraint['id']}: {constraint['text']}")
            if constraint.get('reason'):
                print(f"      Reason: {constraint['reason']}")
        print()

    # Tradeoffs
    if note.get('tradeoffs'):
        print("KNOWN TRADEOFFS (Intentional shortcuts):")
        for tradeoff in note['tradeoffs']:
            debt_level = tradeoff.get('debtLevel', 'medium').upper()
            print(f"  [{debt_level}] {tradeoff['id']}: {tradeoff['shortcut']}")
            print(f"      Reason: {tradeoff['reason']}")
            if tradeoff.get('repaymentPlan'):
                print(f"      Repayment: {tradeoff['repaymentPlan']}")
        print()

    # Frozen Sections
    if note.get('frozenSections'):
        print("FROZEN SECTIONS (DO NOT MODIFY):")
        for frozen in note['frozenSections']:
            print(f"  🔒 {frozen['id']}:")
            if 'pattern' in frozen:
                print(f"      Pattern: {frozen['pattern']}")
            if 'lineRange' in frozen:
                print(f"      Lines: {frozen['lineRange'][0]}-{frozen['lineRange'][1]}")
            print(f"      Reason: {frozen['reason']}")
            if frozen.get('exceptions'):
                print(f"      Exceptions: {frozen['exceptions']}")
        print()

    # Metadata
    print("METADATA:")
    print(f"  Created: {note.get('createdAt', 'Unknown')}")
    print(f"  Updated: {note.get('updatedAt', 'Unknown')}")
    if note.get('tags'):
        print(f"  Tags: {', '.join(note['tags'])}")
    print("\n" + "=" * 80 + "\n")


def prompt_input(prompt: str, default: Optional[str] = None) -> str:
    """Prompt user for input."""
    if default:
        user_input = input(f"{prompt} [{default}]: ")
        return user_input if user_input else default
    else:
        return input(f"{prompt}: ")


def prompt_multiline(prompt: str) -> list:
    """Prompt for multiple lines (press Enter twice to finish)."""
    print(f"{prompt}")
    print("(Press Enter twice to finish)")
    lines = []
    empty_count = 0

    while True:
        line = input()
        if not line:
            empty_count += 1
            if empty_count >= 2:
                break
        else:
            empty_count = 0
            lines.append(line)

    return lines


def create_note_interactive(manager: NoteManager, file_path: str) -> bool:
    """Create a note through interactive prompts."""
    print(f"\n=== Creating Design Note for {os.path.basename(file_path)} ===\n")

    # Create default note structure
    note = NoteSchema.create_default_note(file_path)

    # Design Intent
    print("STEP 1: Design Intent")
    purpose = prompt_input("  Purpose (what is this file for?)")
    note['designIntent']['purpose'] = purpose

    print("\n  Key Decisions (one per line, press Enter twice to finish):")
    decisions = prompt_multiline("  ")
    note['designIntent']['keyDecisions'] = decisions

    rationale = prompt_input("\n  Rationale (broader context)", "")
    if rationale:
        note['designIntent']['rationale'] = rationale

    # Assumptions
    print("\nSTEP 2: Assumptions")
    print("  What does this code assume? (e.g., async operations, single-threaded)")
    assumptions_input = prompt_multiline("  ")

    for i, assumption_text in enumerate(assumptions_input):
        severity = prompt_input(f"    Severity for '{assumption_text[:50]}...' [critical/medium/low]", "medium")
        note['assumptions'].append({
            'id': f'assume_{i+1}',
            'text': assumption_text,
            'severity': severity
        })

    # Constraints
    print("\nSTEP 3: Constraints")
    print("  What constraints must be maintained? (e.g., backward compatibility)")
    constraints_input = prompt_multiline("  ")

    for i, constraint_text in enumerate(constraints_input):
        constraint_type = prompt_input(f"    Type for '{constraint_text[:50]}...' [functional/api/performance]", "functional")
        reason = prompt_input(f"    Reason", "")
        note['constraints'].append({
            'id': f'constraint_{i+1}',
            'text': constraint_text,
            'type': constraint_type,
            'reason': reason
        })

    # Tradeoffs
    print("\nSTEP 4: Known Tradeoffs / Technical Debt")
    print("  Any intentional shortcuts or technical debt?")
    tradeoffs_input = prompt_multiline("  ")

    for i, shortcut_text in enumerate(tradeoffs_input):
        reason = prompt_input(f"    Reason for '{shortcut_text[:50]}...'")
        debt_level = prompt_input(f"    Debt level [high/medium/low]", "medium")
        repayment = prompt_input(f"    Repayment plan", "")
        note['tradeoffs'].append({
            'id': f'tradeoff_{i+1}',
            'shortcut': shortcut_text,
            'reason': reason,
            'debtLevel': debt_level,
            'repaymentPlan': repayment
        })

    # Frozen Sections
    print("\nSTEP 5: Frozen Sections (optional)")
    add_frozen = prompt_input("  Define frozen sections? [y/n]", "n")

    if add_frozen.lower() == 'y':
        print("  Enter frozen section patterns or line ranges:")
        frozen_count = 0

        while True:
            frozen_count += 1
            pattern = prompt_input(f"\n    Pattern (regex) for frozen section {frozen_count}", "")
            if not pattern:
                break

            reason = prompt_input(f"    Reason")
            exceptions = prompt_input(f"    Allowed exceptions", "")

            note['frozenSections'].append({
                'id': f'frozen_{frozen_count}',
                'pattern': pattern,
                'reason': reason,
                'exceptions': exceptions
            })

            another = prompt_input("    Add another frozen section? [y/n]", "n")
            if another.lower() != 'y':
                break

    # Tags
    tags_input = prompt_input("\nTags (comma-separated)", "")
    if tags_input:
        note['tags'] = [tag.strip() for tag in tags_input.split(',')]

    # Confirmation
    print("\n=== Review ===")
    print_formatted_note(note, file_path)

    confirm = prompt_input("Create this note? [y/n]", "y")
    if confirm.lower() != 'y':
        print("Note creation cancelled.")
        return False

    # Create note
    success, error = manager.create_note(file_path, note)
    if success:
        print(f"\n✓ Note created successfully for {file_path}")
        print(f"  Stored in: .claude/notes/<hash>/note.json")
        return True
    else:
        print(f"\n✗ Failed to create note: {error}")
        return False


def cmd_create(manager: NoteManager, file_path: str) -> int:
    """Create command."""
    if manager.path_utils.note_exists(file_path):
        print(f"Error: Note already exists for {file_path}")
        print("Use /note edit to modify it.")
        return 1

    success = create_note_interactive(manager, file_path)
    return 0 if success else 1


def cmd_view(manager: NoteManager, file_path: str) -> int:
    """View command."""
    note = manager.load_note(file_path)
    if note is None:
        print(f"Error: No note found for {file_path}")
        return 1

    print_formatted_note(note, file_path)
    return 0


def cmd_list(manager: NoteManager) -> int:
    """List command."""
    notes = manager.list_notes()

    if not notes:
        print("No design notes found in this project.")
        return 0

    print("\n=== Design Notes ===\n")
    for entry in notes:
        critical_marker = "⚠ CRITICAL" if entry.get('critical') else ""
        print(f"📝 {entry['filePath']}")
        print(f"   {entry.get('designIntentSummary', 'No description')} {critical_marker}")
        print(f"   Updated: {entry.get('updatedAt', 'Unknown')}\n")

    print(f"Total: {len(notes)} note(s)\n")
    return 0


def cmd_delete(manager: NoteManager, file_path: str) -> int:
    """Delete command."""
    note = manager.load_note(file_path)
    if note is None:
        print(f"Error: No note found for {file_path}")
        return 1

    print(f"\nDeleting note for: {file_path}")
    print(f"Purpose: {note.get('designIntent', {}).get('purpose', 'No description')}")

    confirm = prompt_input("\nAre you sure? [y/n]", "n")
    if confirm.lower() != 'y':
        print("Deletion cancelled.")
        return 0

    success, error = manager.delete_note(file_path)
    if success:
        print(f"✓ Note deleted successfully")
        return 0
    else:
        print(f"✗ Failed to delete note: {error}")
        return 1


def cmd_migrate(manager: NoteManager, old_path: str, new_path: str) -> int:
    """Migrate command."""
    success, error = manager.migrate_note(old_path, new_path)
    if success:
        print(f"✓ Note migrated successfully")
        print(f"  From: {old_path}")
        print(f"  To: {new_path}")
        return 0
    else:
        print(f"✗ Failed to migrate note: {error}")
        return 1


def show_help():
    """Show help message."""
    help_text = """
/note - Manage design intent notes for files

Usage: /note <action> [file_path] [options]

Actions:
  create <file_path>           Create new design note
  view <file_path>             View existing design note
  edit <file_path>             Edit existing design note
  delete <file_path>           Delete design note
  list                         List all design notes
  migrate <old> <new>          Migrate note after file rename
  help                         Show this help

Examples:
  /note create src/components/Button.tsx
  /note view src/components/Button.tsx
  /note list
  /note migrate old.ts new.ts

For more information, see the README.md in the plugin directory.
"""
    print(help_text)


def main():
    """Main command handler entry point."""
    if len(sys.argv) < 2:
        show_help()
        return 0

    action = sys.argv[1].lower()
    cwd = os.getcwd()

    manager = NoteManager(project_root=cwd)

    if action == 'help':
        show_help()
        return 0

    elif action == 'list':
        return cmd_list(manager)

    elif action in ['create', 'view', 'delete']:
        if len(sys.argv) < 3:
            print(f"Error: {action} requires a file path")
            print(f"Usage: /note {action} <file_path>")
            return 1

        file_path = sys.argv[2]

        if action == 'create':
            return cmd_create(manager, file_path)
        elif action == 'view':
            return cmd_view(manager, file_path)
        elif action == 'delete':
            return cmd_delete(manager, file_path)

    elif action == 'migrate':
        if len(sys.argv) < 4:
            print("Error: migrate requires old_path and new_path")
            print("Usage: /note migrate <old_path> <new_path>")
            return 1

        old_path = sys.argv[2]
        new_path = sys.argv[3]
        return cmd_migrate(manager, old_path, new_path)

    elif action == 'edit':
        print("Note: edit command not yet implemented")
        print("For now, manually edit the note file or use create to recreate it")
        return 1

    else:
        print(f"Error: Unknown action '{action}'")
        show_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
