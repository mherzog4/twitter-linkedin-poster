# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python project that fetches merged pull requests from your GitHub repositories and generates social media content (LinkedIn posts and Twitter tweets) using Anthropic's Claude API. It includes integration with CodeRabbit AI code review insights to enhance the generated content with code quality information. It uses uv for dependency management and Python 3.13+ as the minimum requirement.

## Setup

1. Copy the environment template and fill in your credentials:
```bash
cp .env.example .env
```

2. Set up your environment variables in `.env`:
   - `GITHUB_TOKEN`: Your GitHub personal access token (with repo read permissions)
   - `GITHUB_USERNAME`: Your GitHub username
   - `ANTHROPIC_API_KEY`: Your Anthropic API key

## Development Commands

### Running the Application
```bash
# Install dependencies first
uv sync

# Run the main application
python main.py
```

### Code Quality
```bash
# Lint and format code
ruff check .
ruff format .

# Fix auto-fixable issues
ruff check --fix .
```

### Dependency Management
```bash
# Install dependencies
uv sync

# Add new dependency
uv add <package>

# Update dependencies
uv lock --upgrade
```

## Project Structure

- `main.py`: Entry point with basic hello world functionality
- `pyproject.toml`: Project configuration and dependencies
- `uv.lock`: Locked dependency versions
- `.gitignore`: Standard Python gitignore with uv-specific additions

## Code Architecture

### Core Components

- **GitHubClient**: Handles GitHub API interactions
  - `get_user_repos()`: Fetches all public repositories for a user
  - `get_recent_merged_prs()`: Gets recently merged PRs from a repository
  - `get_pr_details()`: Fetches detailed PR information
  - `get_pr_comments()`: Retrieves all comments and reviews from a PR
  - `extract_coderabbit_insights()`: Parses CodeRabbit AI review data from comments

- **ContentGenerator**: Generates social media content using Anthropic's API
  - `generate_linkedin_post()`: Creates professional LinkedIn posts
  - `generate_tweet()`: Creates concise Twitter posts

### Workflow

1. Fetches all public repositories for the configured GitHub user
2. Searches through repositories to find the most recently merged PR
3. **If merged PR found:**
   - Fetches all PR comments, reviews, and CodeRabbit insights
   - Extracts CodeRabbit AI review data (summaries, suggestions, quality insights)
   - Uses this data to enhance social media content generation
4. **If no merged PRs found:**
   - Falls back to finding the most recent commit across all repositories
   - Generates content based on commit information
5. Uses Anthropic's Claude API to generate appropriate content for both LinkedIn and Twitter
6. Displays the generated content for review

### API Integrations

- **GitHub API v3**: For repository and pull request data
- **Anthropic API**: For AI-generated social media content using Claude
- **CodeRabbit Integration**: Parses CodeRabbit AI review comments from PR discussions

## Development Notes

- Uses uv for fast Python package management
- Ruff is configured for code linting and formatting
- Requires Python 3.13 or higher