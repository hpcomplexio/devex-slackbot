# Markdown FAQ Source - Quick Start Guide

The Slack FAQ Bot now supports using a local Markdown file as an alternative to Notion. This is perfect for testing without API keys or when Notion permissions aren't available yet.

## Quick Setup

### 1. Configure for Markdown

Edit your `.env` file:

```bash
FAQ_SOURCE=markdown
FAQ_FILE_PATH=./faq.md
```

### 2. Edit the FAQ File

A sample `faq.md` is included. Edit it with your own FAQ content:

```markdown
# How do I reset my password?

To reset your password:
1. Go to the Settings page
2. Click on "Security"
3. Select "Reset Password"

## What are the office hours?

Monday-Friday: 9am-5pm PST
Weekends: Closed
```

### 3. Test It

```bash
# Test markdown parsing
python3 scripts/test_markdown_source.py

# Test retrieval (requires ANTHROPIC_API_KEY in .env)
python3 scripts/test_retrieval.py
```

### 4. Run the Bot

```bash
# Make sure you have Slack tokens configured in .env
python -m src.faqbot.main
```

## How It Works

The markdown adapter splits your FAQ file by headings (# ## ###), creating chunks similar to how Notion pages are processed:

- **Heading** → Section title (e.g., "How do I reset my password?")
- **Content** → All text until the next heading
- **Block ID** → Line number reference
- **URL** → File path with line number (file://path#L123)

## Switching to Notion Later

When you're ready to use Notion:

1. Run OAuth setup (see README for detailed instructions):
```bash
python scripts/notion_oauth_setup.py
```

2. Update `.env`:
```bash
FAQ_SOURCE=notion
NOTION_OAUTH_CLIENT_ID=your-client-id
NOTION_OAUTH_CLIENT_SECRET=your-client-secret
NOTION_OAUTH_REFRESH_TOKEN=your-refresh-token
NOTION_FAQ_PAGE_ID=your-page-id
```

3. Restart the bot

That's it! The rest of the system (retrieval, embeddings, Claude) works the same regardless of source.

## Markdown vs Notion

| Feature | Markdown | Notion |
|---------|----------|--------|
| Setup time | Instant | ~15 min (API setup) |
| API keys needed | No | Yes |
| Permissions needed | No | Yes (workspace admin) |
| Updates | Restart bot | Automatic sync |
| Collaboration | Git-based | Real-time |
| Version control | Native | External |
| Best for | Testing, small teams | Production, large teams |

## Tips

- Use clear, descriptive headings (they become searchable titles)
- Keep content under each heading focused on one topic
- Use H1 (#) for main questions, H2 (##) for sub-topics
- Empty sections are automatically skipped
- The bot automatically reloads the file every `FAQ_SYNC_INTERVAL` minutes

## Example Structure

```markdown
# Category: Account Management

## How do I reset my password?
Step-by-step instructions...

## How do I update my email?
More instructions...

# Category: Billing

## What payment methods do you accept?
Details about payment...

## How do I update my billing information?
Billing update instructions...
```

Each H2 (##) becomes a separate searchable chunk in the vector store.
