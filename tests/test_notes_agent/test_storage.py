"""Tests for Notes Agent storage layer."""

import json
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from clarvis_agents.notes_agent.storage import (
    NotesStorage,
    Note,
    _slugify,
    _fuzzy_match,
)


class TestSlugify:
    """Test suite for _slugify function."""

    def test_basic_text(self):
        """Test basic text slugification."""
        assert _slugify("Hello World") == "hello-world"

    def test_removes_special_characters(self):
        """Test that special characters are removed."""
        assert _slugify("Hello! World?") == "hello-world"

    def test_multiple_spaces(self):
        """Test that multiple spaces become single hyphens."""
        assert _slugify("Hello   World") == "hello-world"

    def test_leading_trailing_spaces(self):
        """Test that leading/trailing spaces are trimmed."""
        assert _slugify("  Hello World  ") == "hello-world"

    def test_mixed_case(self):
        """Test that text is lowercased."""
        assert _slugify("Grocery List") == "grocery-list"

    def test_numbers_preserved(self):
        """Test that numbers are preserved."""
        assert _slugify("List 123") == "list-123"


class TestFuzzyMatch:
    """Test suite for _fuzzy_match function."""

    def test_exact_match(self):
        """Test exact match."""
        candidates = ["Grocery List", "Shopping List", "To-Do"]
        assert _fuzzy_match("Grocery List", candidates) == "Grocery List"

    def test_case_insensitive(self):
        """Test case insensitive matching."""
        candidates = ["Grocery List", "Shopping List"]
        assert _fuzzy_match("grocery list", candidates) == "Grocery List"

    def test_partial_match(self):
        """Test partial matching."""
        candidates = ["Grocery List", "Shopping List"]
        assert _fuzzy_match("grocery", candidates) == "Grocery List"

    def test_word_match(self):
        """Test word-based matching."""
        candidates = ["My Grocery List", "Shopping List"]
        assert _fuzzy_match("grocery", candidates) == "My Grocery List"

    def test_no_match(self):
        """Test no match returns None."""
        candidates = ["Grocery List", "Shopping List"]
        assert _fuzzy_match("reminders", candidates) is None

    def test_empty_candidates(self):
        """Test empty candidates returns None."""
        assert _fuzzy_match("anything", []) is None


class TestNotesStorage:
    """Test suite for NotesStorage class."""

    @pytest.fixture
    def temp_storage(self):
        """Create a temporary storage for testing."""
        with TemporaryDirectory() as tmpdir:
            storage = NotesStorage(notes_dir=Path(tmpdir))
            yield storage

    def test_initialization_creates_directory(self, temp_storage: NotesStorage):
        """Test that initialization creates the notes directory."""
        assert temp_storage.notes_dir.exists()
        assert temp_storage.notes_dir.is_dir()

    def test_create_note_list(self, temp_storage: NotesStorage):
        """Test creating a list note."""
        note = temp_storage.create_note(
            title="Grocery List",
            note_type="list",
            items=["milk", "bread"],
        )

        assert note.id == "grocery-list"
        assert note.title == "Grocery List"
        assert note.note_type == "list"
        assert note.items == ["milk", "bread"]
        assert note.content == ""

    def test_create_note_general(self, temp_storage: NotesStorage):
        """Test creating a general note."""
        note = temp_storage.create_note(
            title="Garage Code",
            note_type="general",
            content="1234",
        )

        assert note.id == "garage-code"
        assert note.title == "Garage Code"
        assert note.note_type == "general"
        assert note.content == "1234"
        assert note.items == []

    def test_create_note_persists_to_file(self, temp_storage: NotesStorage):
        """Test that created note is persisted to disk."""
        note = temp_storage.create_note(
            title="Test Note",
            note_type="general",
            content="Test content",
        )

        # Check file exists
        note_path = temp_storage._get_note_path(note.id)
        assert note_path.exists()

        # Check file content
        with open(note_path) as f:
            data = json.load(f)
        assert data["id"] == "test-note"
        assert data["title"] == "Test Note"
        assert data["content"] == "Test content"

    def test_create_duplicate_returns_existing(self, temp_storage: NotesStorage):
        """Test creating a duplicate note returns existing."""
        note1 = temp_storage.create_note(title="Test", note_type="list")
        note2 = temp_storage.create_note(title="Test", note_type="list")

        assert note1.id == note2.id

    def test_get_note_by_id(self, temp_storage: NotesStorage):
        """Test getting a note by ID."""
        temp_storage.create_note(title="My Note", note_type="general", content="Hello")

        note = temp_storage.get_note_by_id("my-note")
        assert note is not None
        assert note.title == "My Note"

    def test_get_note_by_id_not_found(self, temp_storage: NotesStorage):
        """Test getting a non-existent note returns None."""
        note = temp_storage.get_note_by_id("nonexistent")
        assert note is None

    def test_get_note_fuzzy_match(self, temp_storage: NotesStorage):
        """Test getting a note with fuzzy matching."""
        temp_storage.create_note(title="Grocery List", note_type="list")

        note = temp_storage.get_note("grocery")
        assert note is not None
        assert note.title == "Grocery List"

    def test_list_notes_empty(self, temp_storage: NotesStorage):
        """Test listing notes when none exist."""
        notes = temp_storage.list_notes()
        assert notes == []

    def test_list_notes_all(self, temp_storage: NotesStorage):
        """Test listing all notes."""
        temp_storage.create_note(title="Note 1", note_type="list")
        temp_storage.create_note(title="Note 2", note_type="general")
        temp_storage.create_note(title="Note 3", note_type="reminder")

        notes = temp_storage.list_notes()
        assert len(notes) == 3

    def test_list_notes_filtered(self, temp_storage: NotesStorage):
        """Test listing notes filtered by type."""
        temp_storage.create_note(title="Note 1", note_type="list")
        temp_storage.create_note(title="Note 2", note_type="general")

        lists = temp_storage.list_notes(note_type="list")
        assert len(lists) == 1
        assert lists[0].title == "Note 1"


class TestNotesStorageListOperations:
    """Test suite for NotesStorage list operations."""

    @pytest.fixture
    def temp_storage(self):
        """Create a temporary storage for testing."""
        with TemporaryDirectory() as tmpdir:
            storage = NotesStorage(notes_dir=Path(tmpdir))
            yield storage

    def test_add_to_list(self, temp_storage: NotesStorage):
        """Test adding items to a list."""
        temp_storage.create_note(title="Grocery", note_type="list")

        note, added = temp_storage.add_to_list("Grocery", ["milk", "bread"])

        assert len(added) == 2
        assert "milk" in note.items
        assert "bread" in note.items

    def test_add_to_list_creates_if_missing(self, temp_storage: NotesStorage):
        """Test that add_to_list creates the list if it doesn't exist."""
        note, added = temp_storage.add_to_list("New List", ["item1"])

        assert note.title == "New List"
        assert "item1" in note.items

    def test_add_to_list_no_duplicates(self, temp_storage: NotesStorage):
        """Test that duplicate items are not added."""
        temp_storage.create_note(title="Grocery", note_type="list", items=["milk"])

        note, added = temp_storage.add_to_list("Grocery", ["milk", "bread"])

        assert len(added) == 1  # Only bread was added
        assert added == ["bread"]
        assert note.items == ["milk", "bread"]

    def test_add_to_list_case_insensitive(self, temp_storage: NotesStorage):
        """Test that duplicate checking is case-insensitive."""
        temp_storage.create_note(title="Grocery", note_type="list", items=["Milk"])

        note, added = temp_storage.add_to_list("Grocery", ["milk"])

        assert len(added) == 0  # milk not added (Milk exists)

    def test_remove_from_list(self, temp_storage: NotesStorage):
        """Test removing items from a list."""
        temp_storage.create_note(
            title="Grocery", note_type="list", items=["milk", "bread", "eggs"]
        )

        note, removed = temp_storage.remove_from_list("Grocery", ["milk", "eggs"])

        assert len(removed) == 2
        assert note.items == ["bread"]

    def test_remove_from_list_not_found(self, temp_storage: NotesStorage):
        """Test removing items that don't exist."""
        temp_storage.create_note(
            title="Grocery", note_type="list", items=["milk"]
        )

        note, removed = temp_storage.remove_from_list("Grocery", ["bread"])

        assert len(removed) == 0
        assert note.items == ["milk"]

    def test_remove_from_list_nonexistent_list(self, temp_storage: NotesStorage):
        """Test removing from non-existent list raises error."""
        with pytest.raises(ValueError, match="not found"):
            temp_storage.remove_from_list("NonExistent", ["item"])

    def test_clear_list(self, temp_storage: NotesStorage):
        """Test clearing a list."""
        temp_storage.create_note(
            title="Grocery", note_type="list", items=["milk", "bread"]
        )

        note = temp_storage.clear_list("Grocery")

        assert note.items == []
        assert note.title == "Grocery"  # List still exists

    def test_clear_list_nonexistent(self, temp_storage: NotesStorage):
        """Test clearing non-existent list raises error."""
        with pytest.raises(ValueError, match="not found"):
            temp_storage.clear_list("NonExistent")


class TestNotesStorageUpdateDelete:
    """Test suite for NotesStorage update and delete operations."""

    @pytest.fixture
    def temp_storage(self):
        """Create a temporary storage for testing."""
        with TemporaryDirectory() as tmpdir:
            storage = NotesStorage(notes_dir=Path(tmpdir))
            yield storage

    def test_update_note(self, temp_storage: NotesStorage):
        """Test updating a note's content."""
        temp_storage.create_note(title="Code", note_type="general", content="1234")

        note = temp_storage.update_note("Code", "5678")

        assert note.content == "5678"

    def test_update_note_not_found(self, temp_storage: NotesStorage):
        """Test updating non-existent note raises error."""
        with pytest.raises(ValueError, match="not found"):
            temp_storage.update_note("NonExistent", "content")

    def test_delete_note(self, temp_storage: NotesStorage):
        """Test deleting a note."""
        temp_storage.create_note(title="ToDelete", note_type="general")

        result = temp_storage.delete_note("ToDelete")

        assert result is True
        assert temp_storage.get_note("ToDelete") is None

    def test_delete_note_not_found(self, temp_storage: NotesStorage):
        """Test deleting non-existent note returns False."""
        result = temp_storage.delete_note("NonExistent")
        assert result is False


class TestNote:
    """Test suite for Note dataclass."""

    def test_to_dict(self):
        """Test converting note to dictionary."""
        note = Note(
            id="test",
            title="Test",
            note_type="list",
            items=["a", "b"],
            content="",
            created_at="2026-01-16T10:00:00",
            updated_at="2026-01-16T10:00:00",
        )

        d = note.to_dict()

        assert d["id"] == "test"
        assert d["title"] == "Test"
        assert d["items"] == ["a", "b"]

    def test_from_dict(self):
        """Test creating note from dictionary."""
        data = {
            "id": "test",
            "title": "Test",
            "note_type": "general",
            "items": [],
            "content": "Hello",
            "created_at": "2026-01-16T10:00:00",
            "updated_at": "2026-01-16T10:00:00",
        }

        note = Note.from_dict(data)

        assert note.id == "test"
        assert note.content == "Hello"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
