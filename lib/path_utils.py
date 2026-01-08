"""
Path utilities for Design Intent Layer plugin.
Handles path normalization, hashing, and caching.
"""

import os
import hashlib
import json
from pathlib import Path
from typing import Optional, Dict

CACHE_FILE = ".claude/notes/.cache/path-hash-cache.json"


class PathUtils:
    """Utilities for path normalization and hashing."""

    def __init__(self, project_root: Optional[str] = None):
        """Initialize with optional project root."""
        self.project_root = project_root or os.getcwd()
        self.cache: Dict[str, str] = {}
        self._load_cache()

    def normalize_path(self, file_path: str) -> str:
        """
        Normalize a file path to canonical form.
        - Resolves relative paths to absolute
        - Resolves symlinks
        - Converts to OS-appropriate separators
        - Handles Windows vs Unix path differences

        Args:
            file_path: The path to normalize

        Returns:
            Normalized absolute path
        """
        # Convert to absolute path if relative
        if not os.path.isabs(file_path):
            file_path = os.path.join(self.project_root, file_path)

        # Resolve symlinks and normalize
        try:
            normalized = os.path.realpath(file_path)
        except (OSError, ValueError):
            # If realpath fails (e.g., file doesn't exist yet), use abspath
            normalized = os.path.abspath(file_path)

        # Normalize separators (important for Windows)
        normalized = os.path.normpath(normalized)

        return normalized

    def compute_hash(self, file_path: str) -> str:
        """
        Compute SHA1 hash of normalized file path.

        Args:
            file_path: The file path to hash

        Returns:
            SHA1 hash as hex string
        """
        normalized = self.normalize_path(file_path)

        # Check cache first
        if normalized in self.cache:
            return self.cache[normalized]

        # Compute hash
        hash_obj = hashlib.sha1(normalized.encode('utf-8'))
        path_hash = hash_obj.hexdigest()

        # Update cache
        self.cache[normalized] = path_hash
        self._save_cache()

        return path_hash

    def get_note_dir(self, file_path: str) -> str:
        """
        Get the directory path for storing a note.

        Args:
            file_path: The file path to get note directory for

        Returns:
            Absolute path to note directory
        """
        path_hash = self.compute_hash(file_path)
        note_dir = os.path.join(self.project_root, ".claude", "notes", path_hash)
        return note_dir

    def get_note_path(self, file_path: str) -> str:
        """
        Get the full path to the note.json file.

        Args:
            file_path: The file path to get note for

        Returns:
            Absolute path to note.json
        """
        note_dir = self.get_note_dir(file_path)
        return os.path.join(note_dir, "note.json")

    def note_exists(self, file_path: str) -> bool:
        """
        Check if a note exists for the given file.

        Args:
            file_path: The file path to check

        Returns:
            True if note exists, False otherwise
        """
        note_path = self.get_note_path(file_path)
        return os.path.isfile(note_path)

    def _load_cache(self):
        """Load path-hash cache from disk."""
        cache_path = os.path.join(self.project_root, CACHE_FILE)

        if os.path.isfile(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.cache = data.get('cache', {})
            except (json.JSONDecodeError, IOError):
                # Cache corrupted or unreadable, start fresh
                self.cache = {}

    def _save_cache(self):
        """Save path-hash cache to disk."""
        cache_path = os.path.join(self.project_root, CACHE_FILE)

        # Ensure cache directory exists
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)

        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'version': '1.0',
                    'cache': self.cache
                }, f, indent=2)
        except IOError as e:
            # Non-fatal: cache write failure just means slower lookups
            print(f"Warning: Could not save path cache: {e}", flush=True)

    def clear_cache(self):
        """Clear the path-hash cache."""
        self.cache = {}
        cache_path = os.path.join(self.project_root, CACHE_FILE)
        if os.path.isfile(cache_path):
            try:
                os.remove(cache_path)
            except IOError:
                pass


# Convenience functions for module-level usage
def normalize_path(file_path: str, project_root: Optional[str] = None) -> str:
    """Normalize a file path to canonical form."""
    utils = PathUtils(project_root)
    return utils.normalize_path(file_path)


def compute_hash(file_path: str, project_root: Optional[str] = None) -> str:
    """Compute SHA1 hash of normalized file path."""
    utils = PathUtils(project_root)
    return utils.compute_hash(file_path)


def get_note_path(file_path: str, project_root: Optional[str] = None) -> str:
    """Get the full path to the note.json file."""
    utils = PathUtils(project_root)
    return utils.get_note_path(file_path)


def note_exists(file_path: str, project_root: Optional[str] = None) -> bool:
    """Check if a note exists for the given file."""
    utils = PathUtils(project_root)
    return utils.note_exists(file_path)
