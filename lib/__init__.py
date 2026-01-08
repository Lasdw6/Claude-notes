"""
Design Intent Layer library modules.
"""

from .path_utils import PathUtils, normalize_path, compute_hash, get_note_path, note_exists
from .note_manager import NoteManager, NoteSchema

__all__ = [
    'PathUtils',
    'normalize_path',
    'compute_hash',
    'get_note_path',
    'note_exists',
    'NoteManager',
    'NoteSchema',
]
