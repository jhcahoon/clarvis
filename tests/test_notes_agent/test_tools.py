"""Tests for Notes Agent tools."""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from clarvis_agents.notes_agent.storage import NotesStorage
from clarvis_agents.notes_agent.tools import (
    # Implementation functions (testable)
    create_note_impl,
    add_to_list_impl,
    remove_from_list_impl,
    get_note_impl,
    list_notes_impl,
    update_note_impl,
    delete_note_impl,
    clear_list_impl,
    # Storage management
    set_storage,
    get_storage,
)


class TestNotesTools:
    """Test suite for Notes Agent tools."""

    @pytest.fixture(autouse=True)
    def setup_temp_storage(self):
        """Setup temporary storage for each test."""
        with TemporaryDirectory() as tmpdir:
            storage = NotesStorage(notes_dir=Path(tmpdir))
            set_storage(storage)
            yield storage

    @pytest.mark.asyncio
    async def test_create_note_list(self):
        """Test creating a list note."""
        result = await create_note_impl(
            title="Grocery List",
            note_type="list",
            items=["milk", "bread"],
        )

        assert "Grocery List" in result or "grocery list" in result.lower()
        assert "2 items" in result or "Created" in result

    @pytest.mark.asyncio
    async def test_create_note_general(self):
        """Test creating a general note."""
        result = await create_note_impl(
            title="Garage Code",
            note_type="general",
            content="1234",
        )

        assert "Garage Code" in result or "garage code" in result.lower()
        assert "Saved" in result or "Created" in result

    @pytest.mark.asyncio
    async def test_add_to_list(self):
        """Test adding items to a list."""
        result = await add_to_list_impl(list_name="grocery", items=["milk", "bread"])

        assert "milk" in result.lower() or "added" in result.lower()

    @pytest.mark.asyncio
    async def test_add_to_list_creates_list(self):
        """Test that add_to_list creates a new list if needed."""
        result = await add_to_list_impl(list_name="new list", items=["item1"])

        assert "item1" in result.lower() or "added" in result.lower()

    @pytest.mark.asyncio
    async def test_add_to_list_no_duplicates(self):
        """Test that duplicate items show appropriate message."""
        # Add first time
        await add_to_list_impl(list_name="grocery", items=["milk"])

        # Add same item again
        result = await add_to_list_impl(list_name="grocery", items=["milk"])

        assert "already" in result.lower()

    @pytest.mark.asyncio
    async def test_remove_from_list(self):
        """Test removing items from a list."""
        await add_to_list_impl(list_name="grocery", items=["milk", "bread"])

        result = await remove_from_list_impl(list_name="grocery", items=["milk"])

        assert "milk" in result.lower() or "removed" in result.lower()

    @pytest.mark.asyncio
    async def test_remove_from_list_not_found(self):
        """Test removing from non-existent list."""
        result = await remove_from_list_impl(list_name="nonexistent", items=["item"])

        assert "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_get_note_list(self):
        """Test getting a list note."""
        await add_to_list_impl(list_name="grocery", items=["milk", "bread"])

        result = await get_note_impl(note_name="grocery")

        assert "milk" in result.lower()
        assert "bread" in result.lower()

    @pytest.mark.asyncio
    async def test_get_note_empty_list(self):
        """Test getting an empty list."""
        await create_note_impl(title="Empty List", note_type="list")

        result = await get_note_impl(note_name="empty list")

        assert "empty" in result.lower()

    @pytest.mark.asyncio
    async def test_get_note_not_found(self):
        """Test getting a non-existent note."""
        result = await get_note_impl(note_name="nonexistent")

        assert "couldn't find" in result.lower()

    @pytest.mark.asyncio
    async def test_get_note_general(self):
        """Test getting a general note."""
        await create_note_impl(title="Garage Code", note_type="general", content="1234")

        result = await get_note_impl(note_name="garage code")

        assert "1234" in result

    @pytest.mark.asyncio
    async def test_list_notes_empty(self):
        """Test listing notes when none exist."""
        result = await list_notes_impl()

        assert "don't have any" in result.lower()

    @pytest.mark.asyncio
    async def test_list_notes_with_notes(self):
        """Test listing notes."""
        await create_note_impl(title="Note 1", note_type="list")
        await create_note_impl(title="Note 2", note_type="general")

        result = await list_notes_impl()

        assert "2" in result or "two" in result.lower()

    @pytest.mark.asyncio
    async def test_list_notes_filtered(self):
        """Test listing notes by type."""
        await create_note_impl(title="List 1", note_type="list")
        await create_note_impl(title="General 1", note_type="general")

        result = await list_notes_impl(note_type="list")

        assert "list" in result.lower()
        # Should only mention one note
        assert "1" in result or "one" in result.lower()

    @pytest.mark.asyncio
    async def test_update_note(self):
        """Test updating a note."""
        await create_note_impl(title="Code", note_type="general", content="1234")

        result = await update_note_impl(note_name="code", content="5678")

        assert "updated" in result.lower()

    @pytest.mark.asyncio
    async def test_update_note_not_found(self):
        """Test updating non-existent note."""
        result = await update_note_impl(note_name="nonexistent", content="content")

        assert "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_delete_note(self):
        """Test deleting a note."""
        await create_note_impl(title="To Delete", note_type="general")

        result = await delete_note_impl(note_name="to delete")

        assert "deleted" in result.lower()

    @pytest.mark.asyncio
    async def test_delete_note_not_found(self):
        """Test deleting non-existent note."""
        result = await delete_note_impl(note_name="nonexistent")

        assert "couldn't find" in result.lower()

    @pytest.mark.asyncio
    async def test_clear_list(self):
        """Test clearing a list."""
        await add_to_list_impl(list_name="grocery", items=["milk", "bread"])

        result = await clear_list_impl(list_name="grocery")

        assert "cleared" in result.lower()

        # Verify list is empty
        get_result = await get_note_impl(note_name="grocery")
        assert "empty" in get_result.lower()

    @pytest.mark.asyncio
    async def test_clear_list_not_found(self):
        """Test clearing non-existent list."""
        result = await clear_list_impl(list_name="nonexistent")

        assert "not found" in result.lower()


class TestGetSetStorage:
    """Test suite for storage getter/setter."""

    def test_get_storage_creates_default(self):
        """Test that get_storage creates default storage."""
        set_storage(None)  # Reset
        storage = get_storage()
        assert storage is not None
        assert isinstance(storage, NotesStorage)

    def test_set_storage(self):
        """Test that set_storage sets the storage."""
        with TemporaryDirectory() as tmpdir:
            storage = NotesStorage(notes_dir=Path(tmpdir))
            set_storage(storage)
            assert get_storage() is storage


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
