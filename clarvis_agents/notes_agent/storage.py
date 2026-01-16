"""Storage layer for Notes Agent - JSON file-based persistence."""

import json
import logging
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

logger = logging.getLogger(__name__)

NoteType = Literal["list", "reminder", "general"]


@dataclass
class Note:
    """Represents a note or list."""

    id: str
    title: str
    note_type: NoteType
    items: list[str]  # For lists
    content: str  # For general notes
    created_at: str
    updated_at: str

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Note":
        """Create a Note from dictionary."""
        return cls(
            id=data["id"],
            title=data["title"],
            note_type=data["note_type"],
            items=data.get("items", []),
            content=data.get("content", ""),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )


def _slugify(text: str) -> str:
    """Convert text to a valid filename slug.

    Args:
        text: The text to slugify

    Returns:
        A lowercase, hyphen-separated slug
    """
    # Convert to lowercase and replace spaces with hyphens
    slug = text.lower().strip()
    # Remove non-alphanumeric characters except hyphens
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    # Replace spaces with hyphens
    slug = re.sub(r"[\s]+", "-", slug)
    # Remove multiple consecutive hyphens
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def _fuzzy_match(query: str, candidates: list[str]) -> Optional[str]:
    """Find the best fuzzy match for a query among candidates.

    Args:
        query: The query string to match
        candidates: List of candidate strings

    Returns:
        The best matching candidate or None
    """
    query_lower = query.lower().strip()
    query_slug = _slugify(query)

    # First try exact match
    for candidate in candidates:
        if candidate.lower() == query_lower:
            return candidate

    # Try slug match
    for candidate in candidates:
        if _slugify(candidate) == query_slug:
            return candidate

    # Try contains match
    for candidate in candidates:
        candidate_lower = candidate.lower()
        if query_lower in candidate_lower or candidate_lower in query_lower:
            return candidate

    # Try partial word match
    query_words = set(query_lower.split())
    best_match = None
    best_score = 0

    for candidate in candidates:
        candidate_words = set(candidate.lower().split())
        # Count matching words
        matches = len(query_words & candidate_words)
        if matches > best_score:
            best_score = matches
            best_match = candidate

    return best_match if best_score > 0 else None


class NotesStorage:
    """File-based storage for notes and lists.

    Each note is stored as a separate JSON file in the notes directory.
    """

    def __init__(self, notes_dir: Optional[Path] = None):
        """Initialize storage.

        Args:
            notes_dir: Directory for storing notes. Defaults to ~/.clarvis/notes/
        """
        self.notes_dir = notes_dir or (Path.home() / ".clarvis" / "notes")
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        """Ensure the notes directory exists."""
        self.notes_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Notes directory: {self.notes_dir}")

    def _get_note_path(self, note_id: str) -> Path:
        """Get the path for a note file.

        Args:
            note_id: The note ID (slug)

        Returns:
            Path to the note's JSON file
        """
        return self.notes_dir / f"{note_id}.json"

    def _now_iso(self) -> str:
        """Get current time in ISO format."""
        return datetime.now().isoformat()

    def create_note(
        self,
        title: str,
        note_type: NoteType,
        content: str = "",
        items: Optional[list[str]] = None,
    ) -> Note:
        """Create a new note.

        Args:
            title: Human-readable title
            note_type: Type of note (list, reminder, general)
            content: Content for general notes
            items: Initial items for lists

        Returns:
            The created Note
        """
        note_id = _slugify(title)

        # Check if already exists
        existing = self.get_note_by_id(note_id)
        if existing:
            logger.warning(f"Note '{note_id}' already exists, returning existing")
            return existing

        now = self._now_iso()
        note = Note(
            id=note_id,
            title=title,
            note_type=note_type,
            items=items or [],
            content=content,
            created_at=now,
            updated_at=now,
        )

        self._save_note(note)
        logger.info(f"Created note: {note_id}")
        return note

    def _save_note(self, note: Note) -> None:
        """Save a note to disk.

        Args:
            note: The note to save
        """
        path = self._get_note_path(note.id)
        with open(path, "w") as f:
            json.dump(note.to_dict(), f, indent=2)
        logger.debug(f"Saved note to {path}")

    def get_note_by_id(self, note_id: str) -> Optional[Note]:
        """Get a note by its ID.

        Args:
            note_id: The note ID (slug)

        Returns:
            The Note or None if not found
        """
        path = self._get_note_path(note_id)
        if not path.exists():
            return None

        try:
            with open(path) as f:
                data = json.load(f)
            return Note.from_dict(data)
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error reading note {note_id}: {e}")
            return None

    def get_note(self, query: str) -> Optional[Note]:
        """Get a note by name with fuzzy matching.

        Args:
            query: The note name to search for

        Returns:
            The best matching Note or None
        """
        # First try exact ID match
        note_id = _slugify(query)
        note = self.get_note_by_id(note_id)
        if note:
            return note

        # Try fuzzy match on titles
        all_notes = self.list_notes()
        titles = [n.title for n in all_notes]
        matched_title = _fuzzy_match(query, titles)

        if matched_title:
            for n in all_notes:
                if n.title == matched_title:
                    return n

        return None

    def list_notes(self, note_type: Optional[NoteType] = None) -> list[Note]:
        """List all notes, optionally filtered by type.

        Args:
            note_type: Filter by note type (list, reminder, general)

        Returns:
            List of notes
        """
        notes = []
        for path in self.notes_dir.glob("*.json"):
            try:
                with open(path) as f:
                    data = json.load(f)
                note = Note.from_dict(data)
                if note_type is None or note.note_type == note_type:
                    notes.append(note)
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Error reading note {path}: {e}")

        # Sort by updated_at descending
        notes.sort(key=lambda n: n.updated_at, reverse=True)
        return notes

    def add_to_list(
        self, note_name: str, items: list[str], create_if_missing: bool = True
    ) -> tuple[Note, list[str]]:
        """Add items to a list.

        Args:
            note_name: Name of the list
            items: Items to add
            create_if_missing: Create the list if it doesn't exist

        Returns:
            Tuple of (updated Note, list of actually added items)

        Raises:
            ValueError: If note not found and create_if_missing is False
        """
        note = self.get_note(note_name)

        if note is None:
            if create_if_missing:
                # Create a new list
                note = self.create_note(
                    title=note_name.title(),
                    note_type="list",
                    items=[],
                )
            else:
                raise ValueError(f"Note '{note_name}' not found")

        if note.note_type != "list":
            # Convert to list if it wasn't
            note.note_type = "list"
            note.items = []

        # Add items that aren't already in the list (case-insensitive)
        existing_lower = {item.lower() for item in note.items}
        added = []
        for item in items:
            if item.lower() not in existing_lower:
                note.items.append(item)
                existing_lower.add(item.lower())
                added.append(item)

        note.updated_at = self._now_iso()
        self._save_note(note)

        logger.info(f"Added {len(added)} items to {note.id}")
        return note, added

    def remove_from_list(self, note_name: str, items: list[str]) -> tuple[Note, list[str]]:
        """Remove items from a list.

        Args:
            note_name: Name of the list
            items: Items to remove

        Returns:
            Tuple of (updated Note, list of actually removed items)

        Raises:
            ValueError: If note not found
        """
        note = self.get_note(note_name)
        if note is None:
            raise ValueError(f"Note '{note_name}' not found")

        if note.note_type != "list":
            raise ValueError(f"'{note.title}' is not a list")

        # Remove items (case-insensitive)
        items_lower = {item.lower() for item in items}
        original_items = note.items.copy()
        note.items = [item for item in note.items if item.lower() not in items_lower]

        removed = [item for item in original_items if item.lower() in items_lower]

        note.updated_at = self._now_iso()
        self._save_note(note)

        logger.info(f"Removed {len(removed)} items from {note.id}")
        return note, removed

    def clear_list(self, note_name: str) -> Note:
        """Clear all items from a list.

        Args:
            note_name: Name of the list

        Returns:
            The updated Note

        Raises:
            ValueError: If note not found or not a list
        """
        note = self.get_note(note_name)
        if note is None:
            raise ValueError(f"Note '{note_name}' not found")

        if note.note_type != "list":
            raise ValueError(f"'{note.title}' is not a list")

        note.items = []
        note.updated_at = self._now_iso()
        self._save_note(note)

        logger.info(f"Cleared list {note.id}")
        return note

    def update_note(self, note_name: str, content: str) -> Note:
        """Update the content of a note.

        Args:
            note_name: Name of the note
            content: New content

        Returns:
            The updated Note

        Raises:
            ValueError: If note not found
        """
        note = self.get_note(note_name)
        if note is None:
            raise ValueError(f"Note '{note_name}' not found")

        note.content = content
        note.updated_at = self._now_iso()
        self._save_note(note)

        logger.info(f"Updated note {note.id}")
        return note

    def delete_note(self, note_name: str) -> bool:
        """Delete a note.

        Args:
            note_name: Name of the note

        Returns:
            True if deleted, False if not found
        """
        note = self.get_note(note_name)
        if note is None:
            return False

        path = self._get_note_path(note.id)
        try:
            path.unlink()
            logger.info(f"Deleted note {note.id}")
            return True
        except OSError as e:
            logger.error(f"Error deleting note {note.id}: {e}")
            return False
