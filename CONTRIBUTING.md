# Contributing to PUBG Clan Tracker Bot

Thank you for your interest in contributing to the PUBG Clan Tracker Discord Bot!

## Getting Started

### Prerequisites

- Python 3.12 or higher
- Discord Bot Token
- PUBG API Key
- Git

### Setup

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/yourusername/Pubg-Tracker.git
   cd Pubg-Tracker
   ```
3. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
6. Edit `.env` and fill in your `DISCORD_TOKEN` and `PUBG_API_KEY`
7. Run the bot:
   ```bash
   python bot.py
   ```

## Development Guidelines

### Code Style

- Follow PEP 8 style guidelines
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and relatively small
- Use type hints where appropriate

### File Structure

```
Pubg-Tracker/
├── bot.py                 # Main bot entry point
├── pubg_api.py           # PUBG API wrapper
├── storage.py            # Database operations
├── translations.py       # Localization
├── history.py            # Historical data management
├── .env                  # Environment variables (not in git)
├── .env.example          # Environment variables template
├── requirements.txt      # Python dependencies
├── commands/             # Discord slash command implementations
│   ├── __init__.py
│   ├── roster.py
│   ├── protected.py
│   ├── analytics.py
│   └── ...
├── modules/              # Core modules
│   ├── config.py
│   ├── scheduler.py
│   ├── maintenance.py
│   ├── reports.py
│   ├── embeds.py
│   └── utils.py
└── assets/               # Static assets (images, icons)
```

### Adding New Commands

1. Create the implementation function in the appropriate `commands/` file
2. Add the command decorator in `bot.py`
3. Import the implementation function in `bot.py`
4. Add error handling with `try/except discord.NotFound` for defer
5. Use `await interaction.response.defer()` immediately
6. Use `await interaction.followup.send()` for responses
7. Test the command thoroughly

Example:
```python
# commands/example.py
async def example_impl(interaction):
    try:
        await interaction.response.defer()
    except discord.NotFound:
        return
    
    # Your logic here
    await interaction.followup.send("Result")

# bot.py
from commands.example import example_impl

@bot.tree.command(description="Example command")
async def example(interaction: discord.Interaction):
    await example_impl(interaction)
```

### Adding Scheduled Tasks

1. Add the task function to `modules/scheduler.py`
2. Use the `@tasks.loop()` decorator
3. Add it to `start_all_scheduled_tasks()` in `modules/scheduler.py`
4. Add maintenance check if appropriate:
   ```python
   try:
       from modules.maintenance import is_in_maintenance
       if is_in_maintenance():
           print(f"[task_name] Skipped - servers in maintenance")
           return
   except ImportError:
       pass
   ```

### Testing

- Test commands manually in Discord
- Check PM2 logs for errors
- Verify defer/followup pattern
- Test with expired interactions
- Test maintenance mode behavior

### Commit Messages

Follow conventional commit format:
```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Example:
```
feat(analytics): add 7-day trend analysis

Implements playertrend command that shows improvement/decline
in key stats over the last 7 days using historical snapshots.
```

## Pull Request Process

1. Create a new branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Make your changes
3. Commit with clear messages
4. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```
5. Create a pull request on GitHub
6. Describe your changes in the PR description
7. Wait for review and address any feedback

## Issues

When reporting bugs or requesting features:

1. Check existing issues first
2. Use the issue template if available
3. Provide clear steps to reproduce
4. Include relevant logs and error messages
5. Specify your environment (Python version, OS, etc.)

## Deployment

Production deployment is done via:
1. Committing to `main` branch
2. Pulling on the production server: `git pull origin main`
3. Restarting PM2: `pm2 restart pubg-bot`

Do not deploy directly to production without testing first.

## Code of Conduct

- Be respectful and constructive
- Welcome newcomers and help them learn
- Focus on what is best for the community
- Show empathy towards other community members

## Questions?

Join the [Game Tracker Bot Discord Support Server](https://discord.gg/KEUWmwBYV4) for help.
