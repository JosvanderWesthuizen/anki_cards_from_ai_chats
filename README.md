# Anki Cards from AI Chats

Automatically generate Anki flashcards from your AI conversation histories using the Gemini API. This tool processes exported conversations from **Claude**, **Google Gemini**, and **OpenAI ChatGPT**, analyzes them for valuable learning content, and creates spaced-repetition flashcards.

## Features

- **Multi-source support**: Import conversations from Claude, Google Gemini, and OpenAI ChatGPT
- **AI-powered analysis**: Uses Gemini to identify flashcard-worthy content
- **Interactive workflow**: Review and approve/reject proposed flashcards
- **Learning from rejections**: System generates rules from rejected cards to improve future suggestions
- **Checkpoint system**: Resumable processing - pick up where you left off
- **AnkiConnect integration**: Directly imports approved cards into Anki

## Prerequisites

- Python 3.13+
- [Anki](https://apps.ankiweb.net/) desktop application
- [AnkiConnect](https://ankiweb.net/shared/info/2055492159) plugin installed in Anki
- Google Gemini API key

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd anki_cards_from_ai_chats

# Using uv (recommended)
uv sync

# Or using pip
python3.13 -m venv .venv
source .venv/bin/activate
pip install google-genai>=1.56.0 python-dotenv>=1.0.0 requests>=2.32.5
```

## Configuration

1. **API Key**: Create a `.env` file in the project root with your Gemini API key:
   ```bash
   GEMINI_API_KEY=your_api_key_here
   ```
   
   You can get a Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey).

2. **Anki Setup**: Ensure Anki is running with AnkiConnect plugin enabled (default port 8765)

## Data Folder Structure

Place your exported conversation data in the `data/` folder with the following structure:

```
data/
├── claude/
│   ├── conversations.json    # Required - Main conversation export
│   ├── memories.json         # Optional - Ignored by processor
│   ├── projects.json         # Optional - Ignored by processor
│   └── users.json            # Optional - Ignored by processor
│
├── google/
│   ├── <conversation_name>   # Individual conversation files (no extension)
│   ├── <conversation_name>   # e.g., "Bézier Curves Explained"
│   ├── ...                   # Each file is a separate conversation
│   └── applet_access_history.json  # Optional - Ignored by processor
│
└── openai/
    ├── conversations.json    # Required - Main conversation export
    └── shared_conversations.json  # Optional - Ignored by processor
```

### Obtaining Your Data

#### Claude
1. Go to [claude.ai](https://claude.ai)
2. Settings > Account > Export Data
3. Extract the downloaded archive
4. Copy files to `data/claude/`

#### Google Gemini
1. Go to [Google Takeout](https://takeout.google.com/)
2. Select "Gemini Apps" and export
3. Extract the downloaded archive
4. Copy conversation files to `data/google/`

#### OpenAI ChatGPT
1. Go to [chat.openai.com](https://chat.openai.com)
2. Settings > Data controls > Export data
3. Extract the downloaded archive
4. Copy files to `data/openai/`

### Expected File Formats

#### `data/claude/conversations.json`
```json
[
  {
    "uuid": "conversation-id",
    "name": "Conversation Title",
    "summary": "Brief summary",
    "chat_messages": [
      {
        "sender": "human",
        "content": [{"type": "text", "text": "User message"}]
      },
      {
        "sender": "assistant",
        "content": [{"type": "text", "text": "Assistant response"}]
      }
    ]
  }
]
```

#### `data/google/<conversation_name>` (no file extension)
```json
{
  "runSettings": {
    "model": "models/gemini-2.0-flash"
  },
  "chunkedPrompt": {
    "chunks": [
      {"role": "user", "text": "User message"},
      {"role": "assistant", "text": "Assistant response"}
    ]
  }
}
```

#### `data/openai/conversations.json`
```json
[
  {
    "title": "Conversation Title",
    "current_node": "last-message-id",
    "mapping": {
      "message-id": {
        "message": {
          "author": {"role": "user"},
          "content": {"parts": ["Message text"]}
        },
        "parent": "parent-message-id"
      }
    }
  }
]
```

After about 2 years of AI usage, I had around 6K conversations. Your total will be shown when you run the script.

## Usage

1. Ensure Anki is running with AnkiConnect enabled
2. Place your conversation exports in the `data/` folder
3. Run the script:

```bash
python main.py
```

4. For each conversation with valuable content, you'll see proposed flashcards:
   ```
   === Conversation: "Python List Comprehensions" ===

   Proposed flashcards:
   1. Q: What is a list comprehension in Python?
      A: A concise way to create lists using a single line...

   Add these flashcards to Anki? (y/n):
   ```

5. Enter `y` to add cards, or `n` to reject
6. If rejected, optionally provide feedback to improve future suggestions

## Files Generated

| File | Description |
|------|-------------|
| `.checkpoint.json` | Tracks progress for resumable processing |
| `rejection_rules.txt` | Learned rules about what NOT to create cards for |

## Project Structure

```
anki_cards_from_ai_chats/
├── main.py              # Main orchestration script
├── claude_formatter.py  # Claude conversation parser
├── google_formatter.py  # Google Gemini conversation parser
├── openai_formatter.py  # OpenAI ChatGPT conversation parser
├── rejection_rules.txt  # Learned rejection rules
├── pyproject.toml       # Project dependencies
├── .env                 # Your API key (create this, gitignored)
├── data/                # Conversation data (gitignored)
└── README.md
```

## How It Works

1. **Load**: Conversations from all three sources are loaded and normalized
2. **Analyze**: Each conversation is sent to Gemini with rejection rules
3. **Propose**: Gemini identifies flashcard-worthy content and formats Q&A pairs
4. **Review**: User approves or rejects proposed flashcards
5. **Learn**: Rejected cards generate new rules to avoid similar content
6. **Import**: Approved flashcards are added to Anki via AnkiConnect

## Rejection Rules

The system learns from your rejections. Example rules:
- Don't create flashcards for one-time configuration steps
- Avoid trivia or pop culture details
- Skip basic commands that are easily searchable

Rules are stored in `rejection_rules.txt` and automatically included in future prompts.

## License

MIT
