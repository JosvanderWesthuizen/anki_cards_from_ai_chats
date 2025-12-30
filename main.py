#!/usr/bin/env python3
"""
Process AI conversations and create Anki flashcards using Gemini.
"""

import json
import os
import requests
from dotenv import load_dotenv
from google import genai

load_dotenv()

import claude_formatter
import google_formatter
import openai_formatter

# Configuration
ANKICONNECT_URL = "http://localhost:8765"
DECK_NAME = "AI Conversations"
DATA_PATH = "data"
MODEL_NAME = "gemini-3-pro-preview"
REJECTION_RULES_FILE = os.path.join("rejection_rules.txt")
CHECKPOINT_FILE = ".checkpoint.json"

# User interests - used to guide flashcard creation
INTERESTS = [
    "Mathematics",
    "AI",
    "Machine Learning",
    "Programming",
    "Science",
    "Physics",
    "Linguistics/Vocabulary",
    "History"
]


def configure_gemini(api_key):
    """Configure Gemini API."""
    return genai.Client(api_key=api_key)


def load_checkpoint():
    """Load checkpoint from file. Returns tuple of (conversation_index, cards_added)."""
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'r') as f:
                data = json.load(f)
                return data.get('conversation_index', 0), data.get('cards_added', 0)
        except (json.JSONDecodeError, IOError):
            return 0, 0
    return 0, 0


def save_checkpoint(conversation_index, cards_added):
    """Save current progress to checkpoint file."""
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump({'conversation_index': conversation_index, 'cards_added': cards_added}, f)


def clear_checkpoint():
    """Remove checkpoint file when processing is complete."""
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)


def load_rejection_rules():
    """Load rejection rules from file if it exists."""
    if os.path.exists(REJECTION_RULES_FILE):
        with open(REJECTION_RULES_FILE, 'r') as f:
            return f.read().strip()
    return ""


def summarize_rejection(client, flashcards, conversation_text, user_feedback=None, existing_rules=None):
    """
    Ask Gemini to summarize why the user rejected these flashcards.
    Returns a short rule/tip about what NOT to create flashcards for.
    
    Args:
        client: Gemini client
        flashcards: List of rejected flashcard dicts
        conversation_text: The source conversation text
        user_feedback: Optional user-provided reason for rejection
        existing_rules: Optional string of existing rejection rules to avoid duplicates
    """
    cards_text = "\n".join([
        f"- Front: {card['front']}\n  Back: {card['back']}"
        for card in flashcards
    ])
    
    feedback_section = ""
    if user_feedback:
        feedback_section = f"""
IMPORTANT - The user provided this feedback explaining their rejection:
"{user_feedback}"

Use this feedback as the PRIMARY basis for generating the rule.
"""
    
    existing_rules_section = ""
    if existing_rules:
        existing_rules_section = f"""
EXISTING RULES (do NOT duplicate these - create a new, specific rule that is different):
{existing_rules}

"""

    interests_text = ", ".join(INTERESTS)
    
    prompt = f"""The user was presented with the following proposed Anki flashcards and REJECTED them:

{cards_text}

These flashcards were generated from this conversation:
{conversation_text[:2000]}...
{feedback_section}
The user's interests are: {interests_text}
{existing_rules_section}
The user didn't want these flashcards added. Please analyze WHY they rejected them and write a SHORT, SPECIFIC rule (1-2 sentences) about what type of information should NOT be turned into flashcards.

Focus on identifying patterns like:
- Too basic/obvious information
- Too specific to one-time tasks
- Information the user likely already knows
- Overly verbose or poorly formatted cards
- Context-dependent information that won't be useful later

Return ONLY the rule, nothing else. Be concise and actionable. Make sure your rule is DIFFERENT from the existing rules listed above.
Example: "Don't create flashcards for basic Git commands like 'git status' or 'git add' that any developer would know."
"""

    try:
        response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Error summarizing rejection: {e}")
        return None


def save_rejection_rule(rule):
    """Append a new rejection rule to the rules file."""
    dir_name = os.path.dirname(REJECTION_RULES_FILE)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    with open(REJECTION_RULES_FILE, 'a') as f:
        f.write(f"- {rule}\n")


def analyze_conversation(client, conversation_text):
    """
    Ask Gemini to analyze the conversation and create flashcards if worthwhile.
    Returns a dict with 'has_value' (bool) and 'flashcards' (list).
    """
    # Load any existing rejection rules
    rejection_rules = load_rejection_rules()
    rules_section = ""
    if rejection_rules:
        rules_section = f"""
IMPORTANT - The user has previously rejected flashcards. Learn from these patterns and AVOID creating similar cards:
{rejection_rules}

"""

    interests_text = ", ".join(INTERESTS)
    
    prompt = f"""Analyze the following conversation between a user and an AI assistant.

{conversation_text}

I want to remember the things that I learn from AI. Thus I'm planning to add useful concepts to Anki to leverage spaced repetition learning for better long term retention of what I learn.

My interests are: {interests_text}. Prioritize creating flashcards for information related to these topics.
{rules_section}
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


def check_anki_running():
    """Check if Anki is running by attempting to connect to AnkiConnect."""
    try:
        ankiconnect_request('version')
        return True
    except requests.exceptions.ConnectionError:
        return False
    except Exception:
        # If we get any other error, AnkiConnect responded so Anki is running
        return True


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
    """
    Ask user to confirm before adding flashcards.
    Returns a tuple: (accepted: bool, feedback: str or None)
    """
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
    
    if response == 'y':
        return True, None
    
    # Ask for optional feedback on rejection
    print("\n💭 Why did you reject these cards? (Press Enter to skip)")
    feedback = input("Feedback: ").strip()
    
    return False, feedback if feedback else None


def process_conversation(client, conversation, deck_name):
    """Process a single conversation and return count of flashcards added."""
    print(f"\n  Analyzing: {conversation['name']}")

    analysis = analyze_conversation(client, conversation['text'])

    if not (analysis.get('has_value') and analysis.get('flashcards')):
        print("    No valuable information found")
        return 0

    flashcards = analysis['flashcards']
    accepted, feedback = confirm_flashcards(flashcards, conversation['name'])
    if not accepted:
        print("    Learning from rejection...")
        existing_rules = load_rejection_rules()
        rule = summarize_rejection(client, flashcards, conversation['text'], user_feedback=feedback, existing_rules=existing_rules)
        if rule:
            save_rejection_rule(rule)
            print(f"    📝 Added rule: {rule}")
        print("    Skipped")
        return 0

    added = 0
    for card in flashcards:
        add_flashcard_to_anki(deck_name, card['front'], card['back'], conversation['tag'])
        added += 1

    print(f"    ✓ Added {added} flashcard(s)")
    return added


def main():
    # Check if Anki is running first
    print("Checking if Anki is running...")
    if not check_anki_running():
        print("Error: Anki is not running.")
        print("Please start Anki and ensure the AnkiConnect add-on is installed.")
        return
    print("✓ Anki is running")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set.")
        print("Create a .env file with: GEMINI_API_KEY=your_api_key_here")
        return

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

    # Load checkpoint to resume from where we left off
    start_index, total_added = load_checkpoint()
    if start_index > 0:
        print(f"\n📌 Resuming from conversation {start_index + 1} (checkpoint found, {total_added} cards added so far)")
    
    # Process all conversations
    print(f"\nProcessing {len(all_conversations)} total conversation(s)...")
    for i, conv in enumerate(all_conversations):
        # Skip already processed conversations
        if i < start_index:
            continue
        
        print(f"\n[{i + 1}/{len(all_conversations)}] {conv['tag']}: {conv['name']}")
        total_added += process_conversation(client, conv, DECK_NAME)
        
        # Save checkpoint after each conversation
        save_checkpoint(i + 1, total_added)

    # Clear checkpoint when complete
    clear_checkpoint()
    print("\n" + "="*80)
    print(f"Processing complete! Added {total_added} flashcards total.")


if __name__ == "__main__":
    main()
