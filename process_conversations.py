#!/usr/bin/env python3
"""
Process Claude conversations and create Anki flashcards using Gemini 3 Pro.
"""

import json
import os
import requests
from pathlib import Path
import google.generativeai as genai

# Configuration
ANKICONNECT_URL = "http://localhost:8765"
DECK_NAME = "Claude Conversations"


def configure_gemini(api_key):
    """Configure Gemini API."""
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-3.0-pro-preview')


def load_conversations(json_path):
    """Load conversations from JSON file."""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def format_conversation(conversation):
    """Format a conversation for Gemini analysis."""
    formatted = f"Conversation: {conversation['name']}\n\n"
    formatted += f"Summary: {conversation['summary']}\n\n"
    formatted += "Messages:\n"

    for msg in conversation['chat_messages']:
        sender = msg['sender']
        # Extract text from content blocks
        text_parts = []
        for content_block in msg.get('content', []):
            if content_block.get('type') == 'text':
                text_parts.append(content_block.get('text', ''))

        if text_parts:
            formatted += f"\n{sender.upper()}:\n{' '.join(text_parts)}\n"

    return formatted


def analyze_conversation(model, conversation_text):
    """
    Ask Gemini to analyze the conversation and create flashcards if worthwhile.
    Returns a dict with 'has_value' (bool) and 'flashcards' (list).
    """
    prompt = f"""Analyze the following conversation between a user and Claude AI.

{conversation_text}

Your task:
1. Determine if there is information worth remembering (useful facts, commands, solutions, concepts, etc.)
2. If yes, create Anki flashcards for this information

Return your response as JSON with this exact format:
{{
    "has_value": true/false,
    "flashcards": [
        {{
            "front": "Question or prompt",
            "back": "Answer or information"
        }}
    ]
}}

Guidelines for flashcards:
- Make them concise and focused on one concept
- Include practical information like commands, configurations, solutions
- Use clear, specific questions
- Include context when needed
- If has_value is false, return an empty flashcards array

Only create flashcards if the information is genuinely useful to remember.
"""

    try:
        response = model.generate_content(prompt)
        # Parse JSON from response
        response_text = response.text.strip()
        # Remove markdown code blocks if present
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.startswith('```'):
            response_text = response_text[3:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        result = json.loads(response_text)
        return result
    except Exception as e:
        print(f"Error analyzing conversation: {e}")
        return {"has_value": False, "flashcards": []}


def ankiconnect_request(action, **params):
    """Make a request to AnkiConnect."""
    payload = {
        'action': action,
        'version': 6,
        'params': params
    }
    response = requests.post(ANKICONNECT_URL, json=payload)
    response.raise_for_status()
    result = response.json()
    if result.get('error'):
        raise Exception(f"AnkiConnect error: {result['error']}")
    return result.get('result')


def ensure_deck_exists(deck_name):
    """Ensure the Anki deck exists."""
    try:
        ankiconnect_request('createDeck', deck=deck_name)
    except:
        pass  # Deck already exists


def add_flashcard_to_anki(deck_name, front, back):
    """Add a flashcard to Anki."""
    note = {
        'deckName': deck_name,
        'modelName': 'Basic',
        'fields': {
            'Front': front,
            'Back': back
        },
        'tags': ['claude-conversation']
    }
    ankiconnect_request('addNote', note=note)


def confirm_flashcards(flashcards):
    """Ask user to confirm before adding flashcards."""
    print("\n" + "="*80)
    print(f"Found {len(flashcards)} flashcard(s) to add:")
    print("="*80)

    for i, card in enumerate(flashcards, 1):
        print(f"\nFlashcard {i}:")
        print(f"  Front: {card['front']}")
        print(f"  Back: {card['back']}")

    print("\n" + "="*80)
    response = input("\nAdd these flashcards to Anki? (y/n): ").strip().lower()
    return response == 'y'


def main():
    api_key = "YOUR_API_KEY_HERE" # Coplay key

    # Configure Gemini
    print("Configuring Gemini...")
    model = configure_gemini(api_key)

    # Ensure Anki deck exists
    print(f"Ensuring deck '{DECK_NAME}' exists...")
    ensure_deck_exists(DECK_NAME)

    # Find all conversation files
    claude_data_path = Path("claude_data")
    conversation_files = list(claude_data_path.glob("*/conversations.json"))

    if not conversation_files:
        print("No conversation files found in claude_data folder!")
        return

    print(f"\nFound {len(conversation_files)} conversation file(s)")

    # Process each file
    for file_path in conversation_files:
        print(f"\nProcessing: {file_path}")
        conversations = load_conversations(file_path)
        print(f"  Loaded {len(conversations)} conversations")

        for i, conversation in enumerate(conversations, 1):
            print(f"\n  [{i}/{len(conversations)}] Analyzing: {conversation['name']}")

            # Format and analyze conversation
            conv_text = format_conversation(conversation)
            analysis = analyze_conversation(model, conv_text)

            if analysis.get('has_value') and analysis.get('flashcards'):
                flashcards = analysis['flashcards']
                if confirm_flashcards(flashcards):
                    for card in flashcards:
                        try:
                            add_flashcard_to_anki(
                                DECK_NAME,
                                card['front'],
                                card['back']
                            )
                        except Exception as e:
                            print(f"    Error adding flashcard: {e}")
                    print(f"    ✓ Added {len(flashcards)} flashcard(s)")
                else:
                    print("    Skipped")
            else:
                print("    No valuable information found")

    print("\n" + "="*80)
    print("Processing complete!")


if __name__ == "__main__":
    main()
