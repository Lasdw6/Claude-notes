"""
Note manager for Design Intent Layer plugin.
Handles CRUD operations, schema validation, and index management.
"""

import os
import json
from datetime import datetime
from typing import Optional, Dict, List, Any
from pathlib import Path

try:
    from .path_utils import PathUtils
except ImportError:
    from path_utils import PathUtils


class NoteSchema:
    """JSON schema validation for design notes."""

    REQUIRED_FIELDS = ['version', 'filePath', 'createdAt', 'updatedAt']
    VALID_SEVERITIES = ['critical', 'medium', 'low']
    VALID_CONSTRAINT_TYPES = ['functional', 'api', 'performance']
    VALID_DEBT_LEVELS = ['high', 'medium', 'low']

    @staticmethod
    def validate(note: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate a note against the schema.

        Args:
            note: The note dictionary to validate

        Returns:
            (is_valid, error_message) tuple
        """
        # Check required fields
        for field in NoteSchema.REQUIRED_FIELDS:
            if field not in note:
                return False, f"Missing required field: {field}"

        # Validate version
        if note.get('version') != '1.0':
            return False, "Invalid version. Expected '1.0'"

        # Validate assumptions
        if 'assumptions' in note:
            if not isinstance(note['assumptions'], list):
                return False, "assumptions must be a list"
            for assumption in note['assumptions']:
                if 'id' not in assumption or 'text' not in assumption:
                    return False, "Each assumption must have 'id' and 'text'"
                if 'severity' in assumption and assumption['severity'] not in NoteSchema.VALID_SEVERITIES:
                    return False, f"Invalid severity: {assumption['severity']}"

        # Validate constraints
        if 'constraints' in note:
            if not isinstance(note['constraints'], list):
                return False, "constraints must be a list"
            for constraint in note['constraints']:
                if 'id' not in constraint or 'text' not in constraint:
                    return False, "Each constraint must have 'id' and 'text'"
                if 'type' in constraint and constraint['type'] not in NoteSchema.VALID_CONSTRAINT_TYPES:
                    return False, f"Invalid constraint type: {constraint['type']}"

        # Validate tradeoffs
        if 'tradeoffs' in note:
            if not isinstance(note['tradeoffs'], list):
                return False, "tradeoffs must be a list"
            for tradeoff in note['tradeoffs']:
                required_tradeoff_fields = ['id', 'shortcut', 'reason']
                for field in required_tradeoff_fields:
                    if field not in tradeoff:
                        return False, f"Each tradeoff must have '{field}'"
                if 'debtLevel' in tradeoff and tradeoff['debtLevel'] not in NoteSchema.VALID_DEBT_LEVELS:
                    return False, f"Invalid debtLevel: {tradeoff['debtLevel']}"

        # Validate frozenSections
        if 'frozenSections' in note:
            if not isinstance(note['frozenSections'], list):
                return False, "frozenSections must be a list"
            for frozen in note['frozenSections']:
                if 'id' not in frozen or 'reason' not in frozen:
                    return False, "Each frozen section must have 'id' and 'reason'"
                if 'pattern' not in frozen and 'lineRange' not in frozen:
                    return False, "Each frozen section must have either 'pattern' or 'lineRange'"

        return True, None

    @staticmethod
    def create_default_note(file_path: str) -> Dict[str, Any]:
        """Create a default note structure."""
        now = datetime.utcnow().isoformat() + 'Z'
        return {
            'version': '1.0',
            'filePath': file_path,
            'createdAt': now,
            'updatedAt': now,
            'designIntent': {
                'purpose': '',
                'keyDecisions': [],
                'rationale': ''
            },
            'assumptions': [],
            'constraints': [],
            'tradeoffs': [],
            'frozenSections': [],
            'requiresAcknowledgment': True,
            'tags': []
        }


class NoteManager:
    """Manager for design notes."""

    INDEX_PATH = ".claude/notes/index.json"

    def __init__(self, project_root: Optional[str] = None):
        """Initialize note manager."""
        self.project_root = project_root or os.getcwd()
        self.path_utils = PathUtils(self.project_root)
        self.index_path = os.path.join(self.project_root, self.INDEX_PATH)
        self._ensure_notes_dir()

    def _ensure_notes_dir(self):
        """Ensure notes directory structure exists."""
        notes_dir = os.path.join(self.project_root, ".claude", "notes")
        os.makedirs(notes_dir, exist_ok=True)
        os.makedirs(os.path.join(notes_dir, ".cache"), exist_ok=True)
        os.makedirs(os.path.join(notes_dir, ".audit"), exist_ok=True)

        # Create index if it doesn't exist
        if not os.path.isfile(self.index_path):
            self._create_index()

    def _create_index(self):
        """Create a new empty index."""
        index = {
            'version': '1.0',
            'lastUpdated': datetime.utcnow().isoformat() + 'Z',
            'notes': []
        }
        with open(self.index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2)

    def _load_index(self) -> Dict[str, Any]:
        """Load the index file."""
        if not os.path.isfile(self.index_path):
            self._create_index()

        with open(self.index_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save_index(self, index: Dict[str, Any]):
        """Save the index file."""
        index['lastUpdated'] = datetime.utcnow().isoformat() + 'Z'
        with open(self.index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2)

    def create_note(self, file_path: str, note_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Create a new design note.

        Args:
            file_path: The file to create a note for
            note_data: The note data dictionary

        Returns:
            (success, error_message) tuple
        """
        # Normalize path
        normalized_path = self.path_utils.normalize_path(file_path)

        # Check if note already exists
        if self.path_utils.note_exists(normalized_path):
            return False, f"Note already exists for {file_path}"

        # Set file path in note data
        note_data['filePath'] = normalized_path

        # Validate schema
        is_valid, error = NoteSchema.validate(note_data)
        if not is_valid:
            return False, f"Schema validation failed: {error}"

        # Create note directory
        note_dir = self.path_utils.get_note_dir(normalized_path)
        os.makedirs(note_dir, exist_ok=True)

        # Write note file
        note_path = self.path_utils.get_note_path(normalized_path)
        try:
            with open(note_path, 'w', encoding='utf-8') as f:
                json.dump(note_data, f, indent=2)
        except IOError as e:
            return False, f"Failed to write note file: {e}"

        # Update index
        try:
            self._add_to_index(normalized_path, note_data)
        except Exception as e:
            # Rollback: delete the note file
            os.remove(note_path)
            return False, f"Failed to update index: {e}"

        return True, None

    def _add_to_index(self, file_path: str, note_data: Dict[str, Any]):
        """Add a note entry to the index."""
        index = self._load_index()

        # Compute hash
        path_hash = self.path_utils.compute_hash(file_path)

        # Extract summary
        design_intent_summary = note_data.get('designIntent', {}).get('purpose', 'No description')

        # Check if entry already exists
        for entry in index['notes']:
            if entry['filePathHash'] == path_hash:
                # Update existing entry
                entry['filePath'] = file_path
                entry['updatedAt'] = note_data['updatedAt']
                entry['designIntentSummary'] = design_intent_summary
                self._save_index(index)
                return

        # Add new entry
        index['notes'].append({
            'filePathHash': path_hash,
            'filePath': file_path,
            'createdAt': note_data['createdAt'],
            'updatedAt': note_data['updatedAt'],
            'designIntentSummary': design_intent_summary,
            'critical': note_data.get('requiresAcknowledgment', False)
        })

        self._save_index(index)

    def load_note(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Load a design note.

        Args:
            file_path: The file to load note for

        Returns:
            Note dictionary or None if not found
        """
        normalized_path = self.path_utils.normalize_path(file_path)
        note_path = self.path_utils.get_note_path(normalized_path)

        if not os.path.isfile(note_path):
            return None

        try:
            with open(note_path, 'r', encoding='utf-8') as f:
                note = json.load(f)

            # Validate schema
            is_valid, error = NoteSchema.validate(note)
            if not is_valid:
                raise ValueError(f"Invalid note schema: {error}")

            return note
        except (IOError, json.JSONDecodeError, ValueError) as e:
            print(f"Error loading note: {e}", flush=True)
            return None

    def update_note(self, file_path: str, note_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Update an existing design note.

        Args:
            file_path: The file to update note for
            note_data: The new note data

        Returns:
            (success, error_message) tuple
        """
        normalized_path = self.path_utils.normalize_path(file_path)

        if not self.path_utils.note_exists(normalized_path):
            return False, f"Note does not exist for {file_path}"

        # Update timestamp
        note_data['updatedAt'] = datetime.utcnow().isoformat() + 'Z'
        note_data['filePath'] = normalized_path

        # Validate schema
        is_valid, error = NoteSchema.validate(note_data)
        if not is_valid:
            return False, f"Schema validation failed: {error}"

        # Write note file
        note_path = self.path_utils.get_note_path(normalized_path)
        try:
            with open(note_path, 'w', encoding='utf-8') as f:
                json.dump(note_data, f, indent=2)
        except IOError as e:
            return False, f"Failed to write note file: {e}"

        # Update index
        try:
            self._add_to_index(normalized_path, note_data)
        except Exception as e:
            return False, f"Failed to update index: {e}"

        return True, None

    def delete_note(self, file_path: str) -> tuple[bool, Optional[str]]:
        """
        Delete a design note.

        Args:
            file_path: The file to delete note for

        Returns:
            (success, error_message) tuple
        """
        normalized_path = self.path_utils.normalize_path(file_path)

        if not self.path_utils.note_exists(normalized_path):
            return False, f"Note does not exist for {file_path}"

        # Delete note file and directory
        note_path = self.path_utils.get_note_path(normalized_path)
        note_dir = self.path_utils.get_note_dir(normalized_path)

        try:
            os.remove(note_path)
            os.rmdir(note_dir)  # Remove directory if empty
        except IOError as e:
            return False, f"Failed to delete note: {e}"

        # Remove from index
        try:
            self._remove_from_index(normalized_path)
        except Exception as e:
            return False, f"Failed to update index: {e}"

        return True, None

    def _remove_from_index(self, file_path: str):
        """Remove a note entry from the index."""
        index = self._load_index()
        path_hash = self.path_utils.compute_hash(file_path)

        index['notes'] = [
            entry for entry in index['notes']
            if entry['filePathHash'] != path_hash
        ]

        self._save_index(index)

    def list_notes(self) -> List[Dict[str, Any]]:
        """
        List all notes in the index.

        Returns:
            List of note metadata entries
        """
        index = self._load_index()
        return index.get('notes', [])

    def migrate_note(self, old_path: str, new_path: str) -> tuple[bool, Optional[str]]:
        """
        Migrate a note from old path to new path (for file renames).

        Args:
            old_path: The old file path
            new_path: The new file path

        Returns:
            (success, error_message) tuple
        """
        # Load old note
        note = self.load_note(old_path)
        if note is None:
            return False, f"No note found for {old_path}"

        # Update file path in note
        note['filePath'] = self.path_utils.normalize_path(new_path)
        note['updatedAt'] = datetime.utcnow().isoformat() + 'Z'

        # Add migration history
        if 'migrationHistory' not in note:
            note['migrationHistory'] = []
        note['migrationHistory'].append({
            'timestamp': note['updatedAt'],
            'oldPath': old_path,
            'newPath': new_path
        })

        # Create new note
        success, error = self.create_note(new_path, note)
        if not success:
            return False, f"Failed to create note at new path: {error}"

        # Delete old note
        success, error = self.delete_note(old_path)
        if not success:
            # Rollback: delete the new note
            self.delete_note(new_path)
            return False, f"Failed to delete old note: {error}"

        return True, None
