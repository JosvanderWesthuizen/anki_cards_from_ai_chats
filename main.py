#!/usr/bin/env python3
"""
Process AI conversations and create Anki flashcards using Gemini.
"""

import json
import os
import requests
from google import genai

import claude_formatter
import google_formatter
import openai_formatter

# Configuration
ANKICONNECT_URL = "http://localhost:8765"
DECK_NAME = "AI Conversations"
DATA_PATH = "data"
MODEL_NAME = "gemini-3-pro-preview"
REJECTION_RULES_FILE = os.path.join(DATA_PATH, "rejection_rules.txt")


def configure_gemini(api_key):
    """Configure Gemini API."""
    return genai.Client(api_key=api_key)


def analyze_conversation(client, conversation_text):
    """
    Ask Gemini to analyze the conversation and create flashcards if worthwhile.
    Returns a dict with 'has_value' (bool) and 'flashcards' (list).
    """
    prompt = f"""Analyze the following conversation between a user and an AI assistant.

{conversation_text}

I want to remember the things that I learn from AI. Thus I'm planning to add useful concepts to Anki to leverage spaced repetition learning for better long term retention of what I learn.

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
- Avoid rote learning, include reasoning and explanation
- Include practical information like commands, configurations, solutions
- Use clear, specific questions
- Include context when needed
- If has_value is false, return an empty flashcards array

Only create flashcards if the information is genuinely useful to remember.
"""

    try:
        response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
        response_text = response.text.strip()

        # Remove markdown code blocks if present
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.startswith('```'):
            response_text = response_text[3:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]

        return json.loads(response_text.strip())
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
        pass


def add_flashcard_to_anki(deck_name, front, back, tag):
    """Add a flashcard to Anki."""
    note = {
        'deckName': deck_name,
        'modelName': 'Basic',
        'fields': {
            'Front': front,
            'Back': back
        },
        'tags': [tag]
    }
    ankiconnect_request('addNote', note=note)


def confirm_flashcards(flashcards, conversation_name):
    """Ask user to confirm before adding flashcards."""
    print("\n" + "="*80)
    print(f"Conversation: {conversation_name}")
    print(f"Found {len(flashcards)} flashcard(s) to add:")
    print("="*80)

    for i, card in enumerate(flashcards, 1):
        print(f"\nFlashcard {i}:")
        print(f"  Front: {card['front']}")
        print(f"  Back: {card['back']}")

    print("\n" + "="*80)
    response = input("\nAdd these flashcards to Anki? (y/n): ").strip().lower()
    return response == 'y'


def process_conversation(client, conversation, deck_name):
    """Process a single conversation and return count of flashcards added."""
    print(f"\n  Analyzing: {conversation['name']}")

    analysis = analyze_conversation(client, conversation['text'])

    if not (analysis.get('has_value') and analysis.get('flashcards')):
        print("    No valuable information found")
        return 0

    flashcards = analysis['flashcards']
    if not confirm_flashcards(flashcards, conversation['name']):
        print("    Skipped")
        return 0

    added = 0
    for card in flashcards:
        try:
            add_flashcard_to_anki(deck_name, card['front'], card['back'], conversation['tag'])
            added += 1
        except Exception as e:
            print(f"    Error adding flashcard: {e}")

    print(f"    ✓ Added {added} flashcard(s)")
    return added


def main():
    api_key = "YOUR_API_KEY_HERE"  # Coplay key

    print("Configuring Gemini...")
    client = configure_gemini(api_key)

    print(f"Ensuring deck '{DECK_NAME}' exists...")
    ensure_deck_exists(DECK_NAME)

    # Gather all conversations from all sources
    all_conversations = []

    print("\nLoading Claude conversations...")
    claude_convs = claude_formatter.get_conversations(DATA_PATH)
    print(f"  Found {len(claude_convs)} Claude conversation(s)")
    all_conversations.extend(claude_convs)

    print("\nLoading Google conversations...")
    google_convs = google_formatter.get_conversations(DATA_PATH)
    print(f"  Found {len(google_convs)} Google conversation(s)")
    all_conversations.extend(google_convs)

    print("\nLoading OpenAI conversations...")
    openai_convs = openai_formatter.get_conversations(DATA_PATH)
    print(f"  Found {len(openai_convs)} OpenAI conversation(s)")
    all_conversations.extend(openai_convs)

    if not all_conversations:
        print("\nNo conversations found!")
        return

    # Process all conversations
    print(f"\nProcessing {len(all_conversations)} total conversation(s)...")
    total_added = 0
    for i, conv in enumerate(all_conversations, 1):
        print(f"\n[{i}/{len(all_conversations)}] {conv['tag']}: {conv['name']}")
        total_added += process_conversation(client, conv, DECK_NAME)

    print("\n" + "="*80)
    print(f"Processing complete! Added {total_added} flashcards total.")


if __name__ == "__main__":
    main()
