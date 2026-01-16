"""Native tools for Notes Agent using Claude Agent SDK."""

from typing import Optional

from claude_agent_sdk import create_sdk_mcp_server, tool

from .storage import NotesStorage, NoteType

# Module-level storage instance - initialized when module loads
_storage: Optional[NotesStorage] = None


def get_storage() -> NotesStorage:
    """Get or create the storage instance."""
    global _storage
    if _storage is None:
        _storage = NotesStorage()
    return _storage


def set_storage(storage: Optional[NotesStorage]) -> None:
    """Set the storage instance (for testing or custom configuration)."""
    global _storage
    _storage = storage


# Implementation functions (testable without SDK)


async def create_note_impl(
    title: str,
    note_type: NoteType,
    content: str = "",
    items: Optional[list[str]] = None,
) -> str:
    """Create a new note or list.

    Args:
        title: Title for the note
        note_type: Type of note (list, reminder, general)
        content: Content for general notes
        items: Initial items for lists

    Returns:
        Confirmation message
    """
    storage = get_storage()

    try:
        note = storage.create_note(
            title=title,
            note_type=note_type,
            content=content,
            items=items or [],
        )

        if note_type == "list":
            if note.items:
                return f"Created '{note.title}' with {len(note.items)} items."
            else:
                return f"Created empty list '{note.title}'."
        elif note_type == "reminder":
            return f"Created reminder '{note.title}'."
        else:
            return f"Saved note '{note.title}'."

    except Exception as e:
        return f"Error creating note: {str(e)}"


async def add_to_list_impl(list_name: str, items: list[str]) -> str:
    """Add items to a list.

    Args:
        list_name: Name of the list
        items: Items to add

    Returns:
        Confirmation message
    """
    storage = get_storage()

    try:
        note, added = storage.add_to_list(list_name, items, create_if_missing=True)

        if len(added) == 1:
            return f"Added {added[0]} to your {note.title.lower()}."
        elif len(added) > 1:
            return f"Added {len(added)} items to your {note.title.lower()}."
        else:
            # Items were already in the list
            if len(items) == 1:
                return f"{items[0]} is already on your {note.title.lower()}."
            else:
                return f"Those items are already on your {note.title.lower()}."

    except Exception as e:
        return f"Error adding to list: {str(e)}"


async def remove_from_list_impl(list_name: str, items: list[str]) -> str:
    """Remove items from a list.

    Args:
        list_name: Name of the list
        items: Items to remove

    Returns:
        Confirmation message
    """
    storage = get_storage()

    try:
        note, removed = storage.remove_from_list(list_name, items)

        if len(removed) == 1:
            return f"Removed {removed[0]} from your {note.title.lower()}."
        elif len(removed) > 1:
            return f"Removed {len(removed)} items from your {note.title.lower()}."
        else:
            if len(items) == 1:
                return f"{items[0]} wasn't on your {note.title.lower()}."
            else:
                return f"Those items weren't on your {note.title.lower()}."

    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"Error removing from list: {str(e)}"


async def get_note_impl(note_name: str) -> str:
    """Get a note by name.

    Args:
        note_name: Name of the note

    Returns:
        Note content or list items
    """
    storage = get_storage()

    try:
        note = storage.get_note(note_name)

        if note is None:
            return f"I couldn't find a note called '{note_name}'."

        if note.note_type == "list":
            if not note.items:
                return f"Your {note.title.lower()} is empty."
            elif len(note.items) == 1:
                return f"Your {note.title.lower()} has {note.items[0]}."
            else:
                items_str = ", ".join(note.items[:-1]) + f", and {note.items[-1]}"
                return f"Your {note.title.lower()} has {items_str}."
        else:
            if note.content:
                return f"{note.title}: {note.content}"
            else:
                return f"The note '{note.title}' is empty."

    except Exception as e:
        return f"Error retrieving note: {str(e)}"


async def list_notes_impl(note_type: Optional[NoteType] = None) -> str:
    """List all notes.

    Args:
        note_type: Filter by note type (optional)

    Returns:
        List of note names
    """
    storage = get_storage()

    try:
        notes = storage.list_notes(note_type=note_type)

        if not notes:
            if note_type:
                return f"You don't have any {note_type} notes."
            else:
                return "You don't have any notes yet."

        type_label = f"{note_type} " if note_type else ""

        if len(notes) == 1:
            return f"You have one {type_label}note: {notes[0].title}."
        else:
            titles = [n.title for n in notes]
            titles_str = ", ".join(titles[:-1]) + f", and {titles[-1]}"
            return f"You have {len(notes)} {type_label}notes: {titles_str}."

    except Exception as e:
        return f"Error listing notes: {str(e)}"


async def update_note_impl(note_name: str, content: str) -> str:
    """Update a note's content.

    Args:
        note_name: Name of the note
        content: New content

    Returns:
        Confirmation message
    """
    storage = get_storage()

    try:
        note = storage.update_note(note_name, content)
        return f"Updated '{note.title}'."

    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"Error updating note: {str(e)}"


async def delete_note_impl(note_name: str) -> str:
    """Delete a note.

    Args:
        note_name: Name of the note

    Returns:
        Confirmation message
    """
    storage = get_storage()

    try:
        # First get the note to confirm it exists and get the title
        note = storage.get_note(note_name)
        if note is None:
            return f"I couldn't find a note called '{note_name}'."

        title = note.title
        deleted = storage.delete_note(note_name)

        if deleted:
            return f"Deleted your {title.lower()}."
        else:
            return f"Couldn't delete '{note_name}'."

    except Exception as e:
        return f"Error deleting note: {str(e)}"


async def clear_list_impl(list_name: str) -> str:
    """Clear all items from a list.

    Args:
        list_name: Name of the list

    Returns:
        Confirmation message
    """
    storage = get_storage()

    try:
        note = storage.clear_list(list_name)
        return f"Cleared your {note.title.lower()}."

    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"Error clearing list: {str(e)}"


# SDK Tool definitions (decorated functions that call implementations)


@tool(
    name="create_note",
    description="Create a new note or list. Use note_type='list' for grocery lists, shopping lists, todos, reminders. Use note_type='general' for codes, information, free-form notes.",
    input_schema={
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Title for the note (e.g., 'Grocery List', 'Garage Code', 'Reminders')",
            },
            "note_type": {
                "type": "string",
                "enum": ["list", "reminder", "general"],
                "description": "Type of note: 'list' for itemized lists, 'reminder' for reminders, 'general' for free-form notes",
            },
            "content": {
                "type": "string",
                "description": "Content for general notes (e.g., a code, information)",
                "default": "",
            },
            "items": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Initial items for lists",
                "default": [],
            },
        },
        "required": ["title", "note_type"],
    },
)
async def create_note(
    title: str,
    note_type: NoteType,
    content: str = "",
    items: Optional[list[str]] = None,
) -> str:
    """Create a new note or list."""
    return await create_note_impl(title, note_type, content, items)


@tool(
    name="add_to_list",
    description="Add items to a list (grocery, shopping, reminders, etc.). Creates the list if it doesn't exist.",
    input_schema={
        "type": "object",
        "properties": {
            "list_name": {
                "type": "string",
                "description": "Name of the list (e.g., 'grocery', 'shopping', 'reminders')",
            },
            "items": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Items to add to the list",
            },
        },
        "required": ["list_name", "items"],
    },
)
async def add_to_list(list_name: str, items: list[str]) -> str:
    """Add items to a list."""
    return await add_to_list_impl(list_name, items)


@tool(
    name="remove_from_list",
    description="Remove items from a list.",
    input_schema={
        "type": "object",
        "properties": {
            "list_name": {
                "type": "string",
                "description": "Name of the list",
            },
            "items": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Items to remove from the list",
            },
        },
        "required": ["list_name", "items"],
    },
)
async def remove_from_list(list_name: str, items: list[str]) -> str:
    """Remove items from a list."""
    return await remove_from_list_impl(list_name, items)


@tool(
    name="get_note",
    description="Get a note or list by name. Returns the content or items.",
    input_schema={
        "type": "object",
        "properties": {
            "note_name": {
                "type": "string",
                "description": "Name of the note or list to retrieve",
            },
        },
        "required": ["note_name"],
    },
)
async def get_note(note_name: str) -> str:
    """Get a note by name."""
    return await get_note_impl(note_name)


@tool(
    name="list_notes",
    description="List all notes, optionally filtered by type.",
    input_schema={
        "type": "object",
        "properties": {
            "note_type": {
                "type": "string",
                "enum": ["list", "reminder", "general"],
                "description": "Filter by note type (optional)",
            },
        },
        "required": [],
    },
)
async def list_notes(note_type: Optional[NoteType] = None) -> str:
    """List all notes."""
    return await list_notes_impl(note_type)


@tool(
    name="update_note",
    description="Update the content of an existing note.",
    input_schema={
        "type": "object",
        "properties": {
            "note_name": {
                "type": "string",
                "description": "Name of the note to update",
            },
            "content": {
                "type": "string",
                "description": "New content for the note",
            },
        },
        "required": ["note_name", "content"],
    },
)
async def update_note(note_name: str, content: str) -> str:
    """Update a note's content."""
    return await update_note_impl(note_name, content)


@tool(
    name="delete_note",
    description="Delete a note or list.",
    input_schema={
        "type": "object",
        "properties": {
            "note_name": {
                "type": "string",
                "description": "Name of the note to delete",
            },
        },
        "required": ["note_name"],
    },
)
async def delete_note(note_name: str) -> str:
    """Delete a note."""
    return await delete_note_impl(note_name)


@tool(
    name="clear_list",
    description="Clear all items from a list (keeps the list but removes all items).",
    input_schema={
        "type": "object",
        "properties": {
            "list_name": {
                "type": "string",
                "description": "Name of the list to clear",
            },
        },
        "required": ["list_name"],
    },
)
async def clear_list(list_name: str) -> str:
    """Clear all items from a list."""
    return await clear_list_impl(list_name)


# Create the SDK MCP server with all custom tools
notes_tools_server = create_sdk_mcp_server(
    name="notes_tools",
    version="1.0.0",
    tools=[
        create_note,
        add_to_list,
        remove_from_list,
        get_note,
        list_notes,
        update_note,
        delete_note,
        clear_list,
    ],
)
