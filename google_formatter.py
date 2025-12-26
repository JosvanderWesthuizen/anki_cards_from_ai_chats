"""
Google Gemini conversation formatter.
"""

import json
from pathlib import Path

SKIP_FILES = {'applet_access_history.json', 'memories.json', 'projects.json', 'users.json'}
MEDIA_EXTENSIONS = {'.mp4', '.m4a', '.png', '.jpg', '.jpeg', '.gif', '.webp'}


def format_conversation(conversation_data, conversation_name):
    """Format a Google conversation for analysis."""
    formatted = f"Conversation: {conversation_name}\n\n"
    formatted += "Messages:\n"

    chunks = conversation_data.get('chunkedPrompt', {}).get('chunks', [])

    for chunk in chunks:
        role = chunk.get('role', 'unknown')
        text = chunk.get('text', '')
        is_thought = chunk.get('isThought', False)

        if is_thought:
            continue

        if text:
            role_label = "USER" if role == "user" else "ASSISTANT"
            formatted += f"\n{role_label}:\n{text}\n"

    return formatted


def is_conversation_file(file_path):
    """Check if a file is a Google conversation file."""
    if file_path.name in SKIP_FILES:
        return False

    if file_path.suffix in MEDIA_EXTENSIONS:
        return False

    if file_path.suffix not in ['.json', '']:
        return False

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return 'chunkedPrompt' in data and 'chunks' in data.get('chunkedPrompt', {})
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False


def get_conversations(data_path):
    """Get all Google conversations from the data path."""
    google_path = Path(data_path) / "google"

    if not google_path.exists():
        return []

    conversations = []
    for file_path in google_path.iterdir():
        if file_path.is_file() and is_conversation_file(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    name = file_path.stem
                    conversations.append({
                        'name': name,
                        'text': format_conversation(data, name),
                        'tag': 'google-gemini'
                    })
            except Exception:
                continue
    return conversations
