# Slack FAQ Bot

A Python Slack bot that automatically answers questions in threads using an FAQ source as the single source of truth, powered by Claude for answer generation.

## Features

- **Automatic Question Detection**: Detects questions in Slack channels and responds in threads
- **Flexible FAQ Sources**: Supports both Notion and Markdown files as knowledge bases
- **Semantic Search**: Uses Sentence Transformers embeddings and FAISS for retrieval
- **Confidence Gating**: Only answers when confident to prevent hallucinations
- **Claude-Powered**: Generates grounded answers with source citations
- **Thread Deduplication**: Prevents multiple responses in the same thread
- **Automatic FAQ Sync**: Periodically refreshes content from source

## Architecture

```
Slack Message → Filters → Question Detection → Thread Dedup Check
    ↓
FAQ Source (Notion/Markdown) → Chunks (heading-based) → Embeddings (Sentence Transformers)
    ↓
Semantic Search → Confidence Gating → Claude Answer → Slack Thread Reply
```

## Setup

### Prerequisites

- Python 3.10+
- A Slack workspace with admin access
- An Anthropic API key
- **Either**: A Notion account with an FAQ page **OR** a local Markdown file

### FAQ Source Setup

Choose one of the following FAQ sources:

#### Option 1: Markdown File (Recommended for Testing)

The easiest way to get started. Create a `faq.md` file in the project root with your FAQ content. A sample file is included.

Markdown format:
```markdown
# Question or Topic

Answer content here.

## Another Question

More answer content.
```

In your `.env` file:
```bash
FAQ_SOURCE=markdown
FAQ_FILE_PATH=./faq.md
```

**Pros**: No API keys needed, instant testing, version control friendly
**Cons**: Manual updates (restart bot to reload), no collaborative editing

#### Option 2: Notion (For Production)

### 1. Notion OAuth Setup

The bot uses OAuth authentication for secure Notion access (no API keys stored).

1. **Create a Notion OAuth integration** at https://www.notion.so/my-integrations
   - Click "New integration"
   - Select **"OAuth"** as the integration type (not Internal)
   - Name: "FAQ Bot OAuth"
   - Set redirect URI to: `https://localhost:8443/callback`
   - Note your **Client ID** and **Client Secret**

2. **Add credentials to `.env`**:
   ```bash
   NOTION_OAUTH_CLIENT_ID=your-client-id
   NOTION_OAUTH_CLIENT_SECRET=your-client-secret
   ```

3. **Run OAuth setup script**:
   ```bash
   python scripts/notion_oauth_setup.py
   ```

   The script will:
   - Start a local HTTPS server
   - Open your browser to authorize the integration
   - Prompt you to select your workspace and grant access
   - Display your refresh token

4. **Add the refresh token to `.env`**:
   ```bash
   NOTION_OAUTH_REFRESH_TOKEN=your-refresh-token-from-script
   ```

5. **Share your FAQ page with the integration**:
   - Open your Notion FAQ page
   - Click Share → Invite → Select "FAQ Bot OAuth"

6. **Get the page ID from the URL**:
   - URL: `https://www.notion.so/My-FAQ-abc123def456`
   - Page ID: `abc123def456`
   - Add to `.env`:
   ```bash
   FAQ_SOURCE=notion
   NOTION_FAQ_PAGE_ID=abc123def456
   ```

**Token Refresh**: Access tokens are automatically refreshed by the bot. If you need to re-authorize, simply re-run the OAuth setup script.

**Pros**: Real-time collaboration, automatic sync, no bot restart needed, secure OAuth authentication
**Cons**: Initial OAuth setup required, tokens need occasional re-authorization

### 2. Slack Setup

1. Create a Slack app at https://api.slack.com/apps
   - "Create New App" → "From scratch"
   - Name: "FAQ Bot"

2. Enable Socket Mode:
   - Go to "Socket Mode" → Enable
   - Generate token, copy `xapp-...` token

3. Add bot scopes (OAuth & Permissions):
   - `channels:history` - Read messages
   - `channels:read` - View channel info
   - `chat:write` - Send messages

4. Subscribe to events (Event Subscriptions):
   - Enable events
   - Subscribe to `message.channels`

5. Install to workspace:
   - Go to "Install App"
   - Copy bot token (starts with `xoxb-`)

6. Invite bot to channels:
   - In each channel: `/invite @FAQ Bot`
   - Get channel IDs: Run `python scripts/print_channel_id.py` after setup

### 3. Claude Setup

1. Get an API key from https://console.anthropic.com/
2. Create a new key and copy it (starts with `sk-ant-`)

### 4. Local Development

```bash
# Clone repository
cd devex-slackbot

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env

# Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -e .

# Test FAQ source
# For Markdown:
python scripts/test_markdown_source.py

# For Notion:
python scripts/sync_faq_once.py

# Get Slack channel IDs
python scripts/print_channel_id.py

# Start the bot
./scripts/run_local.sh
# or
python -m src.faqbot.main
```

## Configuration

Edit your `.env` file with the following variables:

```bash
# Slack
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
SLACK_ALLOWED_CHANNELS=C123456789,C987654321  # Comma-separated channel IDs

# FAQ Source (choose one: "markdown" or "notion")
FAQ_SOURCE=markdown

# Markdown FAQ (only needed if FAQ_SOURCE=markdown)
FAQ_FILE_PATH=./faq.md

# Notion OAuth (only needed if FAQ_SOURCE=notion)
# Run `python scripts/notion_oauth_setup.py` to obtain these tokens
NOTION_OAUTH_CLIENT_ID=your-client-id
NOTION_OAUTH_CLIENT_SECRET=your-client-secret
NOTION_OAUTH_REFRESH_TOKEN=your-refresh-token
NOTION_FAQ_PAGE_ID=your-page-id

# Claude
ANTHROPIC_API_KEY=sk-ant-your-key

# Retrieval (optional)
TOP_K=5                # Number of chunks to retrieve
MIN_SIMILARITY=0.70    # Minimum similarity threshold
MIN_GAP=0.15          # Minimum gap between top results
FAQ_SYNC_INTERVAL=30  # Minutes between FAQ refreshes
```

## Testing

Test individual components:

```bash
# Test markdown source (if using markdown)
python scripts/test_markdown_source.py

# Test Notion integration (if using Notion)
python scripts/sync_faq_once.py

# Test retrieval system (works with both sources)
python scripts/test_retrieval.py

# Test answer generation
python scripts/test_claude.py

# Get Slack channel IDs
python scripts/print_channel_id.py
```

## How It Works

### Message Processing

1. **Filtering**: Ignores bot messages, edits, and messages from non-allowed channels
2. **Question Detection**: Checks for question marks or question words (how, what, etc.)
3. **Thread Deduplication**: Ensures only one response per thread

### Answer Generation

1. **Chunking**: Splits FAQ content by headings (H1, H2, H3)
2. **Embedding**: Generates semantic embeddings using Sentence Transformers
3. **Search**: Finds top-k most relevant chunks using FAISS
4. **Confidence Gating**: Only answers if:
   - Top similarity >= 0.70 (absolute threshold)
   - Gap between top and second >= 0.15 (uncertainty check)
5. **Generation**: Claude generates answer using retrieved context
6. **Response**: Posts answer in thread with source links

### Confidence Gating

The bot uses two-tier confidence gating to prevent low-quality answers:

- **Absolute threshold**: Top result must have similarity >= 0.70
- **Gap threshold**: If multiple results, top must be >= 0.15 ahead of second

This prevents both low-confidence answers and uncertain answers when multiple chunks are equally relevant.

## Project Structure

```
devex-slackbot/
├── src/faqbot/          # Main application code
│   ├── config.py        # Configuration loader
│   ├── logging.py       # Structured logging
│   ├── main.py          # Entry point
│   ├── types.py         # Shared data types
│   ├── notion/          # Notion integration
│   ├── markdown/        # Markdown file integration
│   ├── retrieval/       # Embedding and search
│   ├── llm/            # Claude integration
│   ├── pipeline/       # Answer generation
│   ├── slack/          # Slack integration
│   └── state/          # State management
├── scripts/            # Utility scripts
├── tests/             # Unit tests
├── faq.md             # Sample markdown FAQ
└── pyproject.toml     # Dependencies
```

## Monitoring

The bot logs structured events for monitoring:

- Message filtering (with reasons)
- Question detection
- Retrieval confidence scores
- Answer generation
- Errors with context

Metrics are periodically logged:
- Questions detected
- Answers sent vs skipped
- Filter reasons breakdown
- Active thread count

## Troubleshooting

### Bot doesn't respond

1. Check bot is invited to the channel: `/invite @FAQ Bot`
2. Verify channel ID is in `SLACK_ALLOWED_CHANNELS`
3. Check logs for filtering reasons
4. Verify message contains a question mark or question word

### Bot responds with low confidence

1. Adjust `MIN_SIMILARITY` (lower to be more lenient)
2. Adjust `MIN_GAP` (lower to allow closer matches)
3. Check retrieval scores with `scripts/test_retrieval.py`
4. Improve FAQ content structure and headings

### FAQ not updating

**For Notion:**
1. Check `FAQ_SYNC_INTERVAL` in `.env`
2. Verify Notion integration has access to the page
3. Check logs for sync errors
4. Manually trigger sync by restarting bot

**For Markdown:**
1. Restart the bot after editing the markdown file
2. Verify the file path in `FAQ_FILE_PATH` is correct
3. Check file permissions
4. Consider switching to Notion for automatic sync

## Cloud Deployment

For production deployments, you can run this bot 24/7 on cloud platforms.

### Azure Kubernetes Service (AKS) - Recommended

Deploy to Azure for continuous operation with auto-restart, monitoring, and easy scaling.

**Quick Start**:
1. Install Azure CLI and kubectl
2. Create AKS cluster and Azure Container Registry
3. Build and push Docker image to ACR
4. Deploy to AKS

**Full Guide**: See [docs/AZURE_DEPLOYMENT.md](docs/AZURE_DEPLOYMENT.md) for complete step-by-step instructions.

**Estimated Cost**: ~$110/month (AKS + ACR + VM)

### Generic Kubernetes Deployment

Works with any Kubernetes cluster (GKE, EKS, on-premises, etc.).

#### Quick Start

```bash
# 1. Build and push Docker image
docker build -t <your-registry>/faq-bot:v1.0.0 .
docker push <your-registry>/faq-bot:v1.0.0

# 2. Update k8s/deployment.yaml with your registry and channel IDs

# 3. Deploy to Kubernetes
kubectl apply -f k8s/namespace.yaml
kubectl create secret generic faq-bot-secrets \
  --namespace=faq-bot \
  --from-literal=slack-bot-token="$SLACK_BOT_TOKEN" \
  --from-literal=slack-app-token="$SLACK_APP_TOKEN" \
  --from-literal=anthropic-api-key="$ANTHROPIC_API_KEY"
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml

# 4. Verify
kubectl logs -f deployment/faq-bot -n faq-bot
```

#### Deployment Features

- **Single replica**: Uses singleton pattern for in-memory thread deduplication
- **Resource allocation**: 512Mi RAM / 0.25 CPU (suitable for 100+ questions/hour)
- **Zero-downtime updates**: Rolling update strategy
- **Auto-restart**: Kubernetes automatically restarts failed pods
- **ConfigMap FAQ**: Markdown FAQ stored in ConfigMap for easy version control

For detailed deployment instructions, troubleshooting, and maintenance, see [k8s/README.md](k8s/README.md).

---

## License

MIT
