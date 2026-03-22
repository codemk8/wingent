# Wingent - Quick Start Guide

## Installation

### 1. Activate Virtual Environment
```bash
source /data/barracuda/.venv/wingent_dev/bin/activate
```

### 2. Install Dependencies
```bash
pip install anthropic openai
```

## Running the Application

```bash
python3 simple_canvas.py
```

## Usage

### Visual Editor

#### Creating Agents
- **Method 1**: `Edit` menu → `Add Agent` (or `Ctrl+A`)
- **Method 2**: Right-click on empty canvas → `Add New Agent`

#### Configuring Agents
- **Double-click** on any agent node
- Or click the **⚙ gear icon** on the node
- Or right-click → `Configure Agent`

**Configuration Options**:
- Agent Name
- Provider (Anthropic, OpenAI, Local)
- Model (provider-specific dropdown)
- System Prompt / Role
- Temperature (0.0 - 2.0)
- Max Tokens

#### Creating Links
1. Right-click on source agent
2. Select `Create Link From Here`
3. Click on target agent

#### Moving Agents
- Click and drag any agent node

#### Deleting Agents
- Right-click on agent → `Delete Agent`

### File Operations

#### New Workflow
- `File` → `New` (or `Ctrl+N`)

#### Open Workflow
- `File` → `Open` (or `Ctrl+O`)
- Select JSON workflow file

#### Save Workflow
- `File` → `Save` (or `Ctrl+S`)
- First time: prompts for filename
- Subsequent saves: overwrites current file

#### Save As
- `File` → `Save As` (or `Ctrl+Shift+S`)
- Saves with new filename

### Running Workflows

#### Start Execution
1. `Run` → `Start Execution` (or `F5`)
2. Select target agent
3. Enter initial message
4. Click `Send`

#### Stop Execution
- `Run` → `Stop Execution` (or `F6`)
- Or click `⬛ Stop` in Execution Monitor

### Execution Monitor

**Features**:
- Real-time message log
- Color-coded messages (timestamp, sender, recipient)
- Statistics: messages, tokens, estimated cost
- Auto-scroll to latest messages

**Buttons**:
- `▶ Start`: Begin execution (disabled during run)
- `⬛ Stop`: Stop execution (disabled when idle)
- `Clear`: Clear message log

## Example Workflows

### 1. Load Research Pipeline
```bash
# File → Open → examples/research_pipeline.json
```

This workflow includes:
- Research Specialist → Content Writer
- Research Specialist → Fact Checker
- Content Writer → Editor
- Fact Checker → Editor

### 2. Create Custom Workflow

**Example: Customer Support**

1. Create agents:
   - **Classifier** (OpenAI GPT-4)
     - System: "Classify customer inquiries into categories"
   - **Technical Support** (Anthropic Claude)
     - System: "Handle technical support questions"
   - **Billing Support** (Anthropic Claude)
     - System: "Handle billing and payment questions"
   - **Response Formatter** (OpenAI GPT-3.5)
     - System: "Format responses for customer communication"

2. Create links:
   - Classifier → Technical Support
   - Classifier → Billing Support
   - Technical Support → Response Formatter
   - Billing Support → Response Formatter

3. Save: `File` → `Save As` → `customer_support.json`

## Keyboard Shortcuts

### File Operations
- `Ctrl+N` - New workflow
- `Ctrl+O` - Open workflow
- `Ctrl+S` - Save workflow
- `Ctrl+Shift+S` - Save As

### Edit Operations
- `Ctrl+A` - Add new agent
- `Ctrl+L` - Show link creation instructions

### Execution
- `F5` - Start execution
- `F6` - Stop execution

## Tips

### Provider Selection
- **Anthropic (Claude)**: Best for reasoning, analysis, writing
- **OpenAI (GPT)**: Fast, good for classification, extraction
- **Local (Ollama)**: Free, private, no API costs

### Temperature Guide
- **0.0 - 0.3**: Factual, deterministic (fact-checking, code)
- **0.4 - 0.7**: Balanced (general tasks)
- **0.8 - 1.0**: Creative (writing, brainstorming)
- **1.1 - 2.0**: Very creative (experimental)

### Workflow Design
- **Linear**: A → B → C (sequential processing)
- **Parallel**: A → B, A → C (simultaneous processing)
- **Convergent**: A → C, B → C (merge results)
- **Circular**: A → B → C → A (iterative refinement)

### Performance
- Start with shorter max_tokens for faster responses
- Use cheaper models (Haiku, GPT-3.5) for simple tasks
- Monitor token usage in statistics bar

## Troubleshooting

### Application Won't Start
```bash
# Check Python version (requires 3.7+)
python3 --version

# Reinstall dependencies
pip install --upgrade anthropic openai
```

### Dialog Won't Open
- Make sure application window is visible
- Try clicking on canvas first to focus window

### Execution Errors
- Verify API keys are set:
  ```bash
  export ANTHROPIC_API_KEY="your-key"
  export OPENAI_API_KEY="your-key"
  ```
- Check provider is installed:
  ```bash
  pip list | grep anthropic
  pip list | grep openai
  ```

### Can't Save Workflow
- Check file permissions in current directory
- Ensure filename ends with `.json`

## API Keys

### Anthropic
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### OpenAI
```bash
export OPENAI_API_KEY="sk-..."
```

### Local Models (Ollama)
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Download a model
ollama pull llama3

# No API key needed!
```

## Next Steps

1. **Explore Examples**: Open `examples/research_pipeline.json`
2. **Create Your Own**: Design a custom workflow
3. **Test Execution**: Run with mock providers first
4. **Go Live**: Add API keys and run with real LLMs

---

**For detailed testing results, see**: `TESTING_SUMMARY.md`
