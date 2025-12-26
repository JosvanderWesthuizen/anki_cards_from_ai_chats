"""
Claude conversation formatter.
"""

import json
from pathlib import Path


def format_conversation(conversation):
    """Format a Claude conversation for analysis."""
    formatted = f"Conversation: {conversation['name']}\n\n"
    formatted += f"Summary: {conversation['summary']}\n\n"
    formatted += "Messages:\n"

    for msg in conversation['chat_messages']:
        sender = msg['sender']
        text_parts = []
        for content_block in msg.get('content', []):
            if content_block.get('type') == 'text':
                text_parts.append(content_block.get('text', ''))

        if text_parts:
            formatted += f"\n{sender.upper()}:\n{' '.join(text_parts)}\n"

    return formatted


def get_conversations(data_path):
    """Get all Claude conversations from the data path."""
    claude_path = Path(data_path) / "claude"
    conversation_files = list(claude_path.glob("*/conversations.json"))

    conversations = []
    for file_path in conversation_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            convs = json.load(f)
            for conv in convs:
                conversations.append({
                    'name': conv['name'],
                    'text': format_conversation(conv),
                    'tag': 'claude'
                })
    return conversations
