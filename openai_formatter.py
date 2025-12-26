"""
OpenAI ChatGPT conversation formatter.
"""

import json
from pathlib import Path


def extract_text_from_parts(parts):
    """Extract text content from message parts."""
    text = ''
    for part in parts:
        if isinstance(part, str):
            text += part
        elif isinstance(part, dict) and 'text' in part:
            text += part['text']
    return text


def get_message_chain(mapping, current_node):
    """Traverse from current_node backwards to get ordered messages."""
    chain = []
    node_id = current_node

    while node_id:
        node = mapping.get(node_id)
        if not node:
            break

        msg = node.get('message')
        if msg:
            role = msg.get('author', {}).get('role', 'unknown')
            parts = msg.get('content', {}).get('parts', [])
            hidden = msg.get('metadata', {}).get('is_visually_hidden_from_conversation', False)

            text = extract_text_from_parts(parts)
            if not hidden and text.strip() and role in ('user', 'assistant'):
                chain.append({'role': role, 'text': text})

        node_id = node.get('parent')

    return list(reversed(chain))


def format_conversation(conversation):
    """Format an OpenAI conversation for analysis."""
    title = conversation.get('title', 'Untitled')
    formatted = f"Conversation: {title}\n\n"
    formatted += "Messages:\n"

    mapping = conversation.get('mapping', {})
    current_node = conversation.get('current_node')

    if not current_node:
        return formatted

    chain = get_message_chain(mapping, current_node)

    for msg in chain:
        role_label = "USER" if msg['role'] == "user" else "ASSISTANT"
        formatted += f"\n{role_label}:\n{msg['text']}\n"

    return formatted


def get_conversations(data_path):
    """Get all OpenAI conversations from the data path."""
    openai_path = Path(data_path) / "openai"
    conversations_file = openai_path / "conversations.json"

    if not conversations_file.exists():
        return []

    conversations = []
    with open(conversations_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for conv in data:
        title = conv.get('title', 'Untitled')
        text = format_conversation(conv)

        # Skip empty conversations
        if "USER:" not in text and "ASSISTANT:" not in text:
            continue

        conversations.append({
            'name': title,
            'text': text,
            'tag': 'openai'
        })

    return conversations
