#!/usr/bin/env python3
"""
PreToolUse hook for Design Intent Layer plugin.
Injects design notes into Claude's context before Write/Edit operations.
"""

import sys
import json
import os
from pathlib import Path

# Add lib directory to path
PLUGIN_ROOT = os.getenv('CLAUDE_PLUGIN_ROOT') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PLUGIN_ROOT, 'lib'))

from note_manager import NoteManager
from acknowledgment_verifier import format_acknowledgment_requirement
from conflict_detection import detect_conflicts


def extract_file_path(tool_input: dict, tool_name: str) -> str:
    """
    Extract file path from tool input.

    Args:
        tool_input: The tool input dictionary
        tool_name: The tool name (Write or Edit)

    Returns:
        The file path being modified
    """
    # For Write tool
    if 'file_path' in tool_input:
        return tool_input['file_path']

    # For Edit tool
    if 'path' in tool_input:
        return tool_input['path']

    raise ValueError(f"Could not extract file path from {tool_name} tool input")


def extract_content(tool_input: dict, tool_name: str) -> tuple[str, str]:
    """
    Extract old and new content from tool input.

    Args:
        tool_input: The tool input dictionary
        tool_name: The tool name

    Returns:
        (old_content, new_content) tuple
    """
    old_content = None
    new_content = None

    if tool_name.lower() == 'write':
        # Write tool - new content only
        new_content = tool_input.get('content', '')

        # Try to read old content if file exists
        file_path = extract_file_path(tool_input, tool_name)
        if os.path.isfile(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    old_content = f.read()
            except (IOError, UnicodeDecodeError):
                pass

    elif tool_name.lower() == 'edit':
        # Edit tool - has old_string and new_string
        old_content = tool_input.get('old_string', '')
        new_content = tool_input.get('new_string', '')

    return old_content, new_content


def main():
    """Main hook entry point."""
    try:
        # Read hook input from stdin
        hook_input = json.load(sys.stdin)

        tool_name = hook_input.get('tool_name', '')
        tool_input = hook_input.get('tool_input', {})
        cwd = hook_input.get('cwd', os.getcwd())

        # Extract file path
        try:
            file_path = extract_file_path(tool_input, tool_name)
        except ValueError as e:
            # If we can't extract file path, allow execution (not our concern)
            print(json.dumps({
                'decision': 'allow',
                'continue': True
            }))
            sys.exit(0)

        # Initialize note manager
        manager = NoteManager(project_root=cwd)

        # Load design note
        note = manager.load_note(file_path)

        if note is None:
            # No note exists - allow execution without injection
            print(json.dumps({
                'decision': 'allow',
                'continue': True
            }))
            sys.exit(0)

        # Note exists - perform conflict detection
        try:
            old_content, new_content = extract_content(tool_input, tool_name)
        except Exception:
            # If content extraction fails, still inject the note but skip conflict detection
            old_content, new_content = None, None

        if new_content:
            frozen_violation, assumption_violations, breaking_changes = detect_conflicts(
                note, file_path, new_content, old_content
            )

            # Check for frozen section violations (BLOCKING)
            if frozen_violation:
                error_msg = frozen_violation.format_error()
                print(json.dumps({
                    'decision': 'block',
                    'blocked': True,
                    'reason': error_msg
                }), file=sys.stderr)
                sys.exit(2)

            # Check for critical assumption violations (WARNING but allow)
            if assumption_violations:
                for violation in assumption_violations:
                    if violation.severity == 'critical':
                        # Log warning but don't block
                        warning = violation.format_warning()
                        print(f"WARNING: {warning}", file=sys.stderr)

        # Format acknowledgment requirement
        acknowledgment_msg = format_acknowledgment_requirement(note, file_path)

        # Inject note into context and allow execution
        response = {
            'decision': 'allow',
            'additionalContext': acknowledgment_msg,
            'systemMessage': f'Design note loaded for {os.path.basename(file_path)}',
            'continue': True
        }

        print(json.dumps(response))
        sys.exit(0)

    except Exception as e:
        # On error, log but allow execution (fail open)
        print(f"Hook error: {str(e)}", file=sys.stderr)
        print(json.dumps({
            'decision': 'allow',
            'continue': True
        }))
        sys.exit(0)


if __name__ == '__main__':
    main()
