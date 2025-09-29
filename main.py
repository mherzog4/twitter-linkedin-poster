import os
import requests
from datetime import datetime
from typing import List, Dict
from dotenv import load_dotenv
import anthropic

load_dotenv()


class GitHubClient:
    def __init__(self, token: str):
        self.token = token
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
            }
        )

    def get_user_repos(self, username: str) -> List[Dict]:
        """Fetch all public repositories for a user"""
        repos = []
        page = 1
        per_page = 100

        while True:
            url = f"https://api.github.com/users/{username}/repos"
            params = {"page": page, "per_page": per_page, "type": "public"}

            response = self.session.get(url, params=params)
            response.raise_for_status()

            page_repos = response.json()
            if not page_repos:
                break

            repos.extend(page_repos)
            page += 1

        return repos

    def get_recent_merged_prs(
        self, owner: str, repo: str, limit: int = 5
    ) -> List[Dict]:
        """Get recently merged PRs for a repository"""
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
        params = {
            "state": "closed",
            "sort": "updated",
            "direction": "desc",
            "per_page": limit * 2,  # Get more to filter for merged ones
        }

        response = self.session.get(url, params=params)
        response.raise_for_status()

        prs = response.json()
        merged_prs = [pr for pr in prs if pr.get("merged_at")]

        return merged_prs[:limit]

    def get_pr_details(self, owner: str, repo: str, pr_number: int) -> Dict:
        """Get detailed information about a specific PR"""
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
        response = self.session.get(url, params={"state": "closed"})
        response.raise_for_status()
        return response.json()

    def get_recent_commits(self, owner: str, repo: str, limit: int = 5) -> List[Dict]:
        """Get recent commits from a repository"""
        url = f"https://api.github.com/repos/{owner}/{repo}/commits"
        params = {"per_page": limit, "author": owner}

        response = self.session.get(url, params=params)
        response.raise_for_status()

        return response.json()

    def get_pr_comments(self, owner: str, repo: str, pr_number: int) -> List[Dict]:
        """Get all comments for a specific PR"""
        comments = []

        # Get issue comments (general PR comments)
        url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"
        response = self.session.get(url)
        response.raise_for_status()
        comments.extend(response.json())

        # Get review comments (code-specific comments)
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/comments"
        response = self.session.get(url)
        response.raise_for_status()
        comments.extend(response.json())

        # Get PR reviews (overall reviews)
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
        response = self.session.get(url)
        response.raise_for_status()
        reviews = response.json()

        # Add review bodies as comments
        for review in reviews:
            if review.get("body"):
                comments.append(
                    {
                        "body": review["body"],
                        "user": review["user"],
                        "created_at": review.get("submitted_at"),
                        "type": "review",
                    }
                )

        return comments

    def extract_coderabbit_insights(self, comments: List[Dict]) -> Dict:
        """Extract CodeRabbit insights from PR comments"""
        coderabbit_data = {
            "summary": None,
            "key_changes": [],
            "suggestions": [],
            "quality_insights": [],
        }

        for comment in comments:
            user_login = comment.get("user", {}).get("login", "").lower()
            body = comment.get("body", "")

            # Check if this is a CodeRabbit comment
            if "coderabbitai" in user_login or "coderabbit" in user_login:
                # Extract summary (usually in first comment)
                if "## Summary" in body or "**Summary**" in body:
                    coderabbit_data["summary"] = body

                # Extract key changes
                if "## Changes" in body or "**Changes**" in body:
                    coderabbit_data["key_changes"].append(body)

                # Extract suggestions/recommendations
                if any(
                    keyword in body.lower()
                    for keyword in ["suggest", "recommend", "consider", "improvement"]
                ):
                    coderabbit_data["suggestions"].append(body)

                # Extract quality insights
                if any(
                    keyword in body.lower()
                    for keyword in [
                        "quality",
                        "security",
                        "performance",
                        "best practice",
                    ]
                ):
                    coderabbit_data["quality_insights"].append(body)

        return coderabbit_data


class ContentGenerator:
    def __init__(self, anthropic_api_key: str):
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)

    def generate_linkedin_post(
        self, pr_data: Dict, repo_name: str, coderabbit_insights: Dict = None
    ) -> str:
        """Generate a LinkedIn post about a merged PR"""
        coderabbit_context = ""
        if coderabbit_insights and any(coderabbit_insights.values()):
            coderabbit_context = "\n\nCodeRabbit AI Review Insights:"
            if coderabbit_insights.get("summary"):
                coderabbit_context += (
                    f"\n- Summary: {coderabbit_insights['summary'][:200]}..."
                )
            if coderabbit_insights.get("suggestions"):
                coderabbit_context += f"\n- Key suggestions: {len(coderabbit_insights['suggestions'])} improvements identified"
            if coderabbit_insights.get("quality_insights"):
                coderabbit_context += f"\n- Quality insights: {len(coderabbit_insights['quality_insights'])} quality improvements noted"

        prompt = f"""
Create a professional LinkedIn post about this merged pull request. 
Make it engaging and highlight the technical achievement without being too technical for a general audience.

Repository: {repo_name}
PR Title: {pr_data["title"]}
PR Description: {pr_data.get("body", "No description provided")}
Author: {pr_data["user"]["login"]}
Changes: {pr_data.get("additions", 0)} additions, {pr_data.get("deletions", 0)} deletions{coderabbit_context}

Make the post:
- Professional but approachable
- Include relevant hashtags
- Highlight the impact or improvement
- If CodeRabbit insights are available, mention that AI code review was used to ensure quality
- Keep it under 1300 characters
- Don't use overly technical jargon
"""

        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text.strip()

    def generate_tweet(
        self, pr_data: Dict, repo_name: str, coderabbit_insights: Dict = None
    ) -> str:
        """Generate a Twitter thread about a merged PR"""
        coderabbit_context = ""
        if coderabbit_insights and any(coderabbit_insights.values()):
            insights_count = sum(
                len(v) if isinstance(v, list) else (1 if v else 0)
                for v in coderabbit_insights.values()
            )
            coderabbit_context = (
                f"\nAI-reviewed with {insights_count} insights from CodeRabbit"
            )

        prompt = f"""
Create a concise Twitter post (under 280 characters) about this merged pull request.
Make it engaging and use relevant hashtags.

Repository: {repo_name}
PR Title: {pr_data["title"]}
PR Description: {pr_data.get("body", "No description provided")}
Author: {pr_data["user"]["login"]}{coderabbit_context}

Make the tweet:
- Concise and engaging
- Include relevant hashtags like #OpenSource #Development #Code #AI
- If CodeRabbit insights available, mention AI code review briefly
- Highlight the key achievement
- Stay under 280 characters
"""

        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text.strip()

    def generate_commit_linkedin_post(self, commit_data: Dict, repo_name: str) -> str:
        """Generate a LinkedIn post about a recent commit"""
        commit_message = commit_data["commit"]["message"]
        commit_sha = commit_data["sha"][:7]
        author = commit_data["commit"]["author"]["name"]

        prompt = f"""
Create a professional LinkedIn post about this recent code commit.
Make it engaging and highlight the development progress without being too technical.

Repository: {repo_name}
Commit Message: {commit_message}
Commit SHA: {commit_sha}
Author: {author}

Make the post:
- Professional but approachable  
- Include relevant hashtags like #Development #Coding #OpenSource
- Highlight the progress or improvement made
- Keep it under 1300 characters
- Focus on the value/impact rather than technical details
"""

        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text.strip()

    def generate_commit_tweet(self, commit_data: Dict, repo_name: str) -> str:
        """Generate a Twitter post about a recent commit"""
        commit_message = commit_data["commit"]["message"]
        commit_sha = commit_data["sha"][:7]

        prompt = f"""
Create a concise Twitter post (under 280 characters) about this recent code commit.
Make it engaging and use relevant hashtags.

Repository: {repo_name}
Commit Message: {commit_message}
Commit SHA: {commit_sha}

Make the tweet:
- Concise and engaging
- Include relevant hashtags like #Coding #Development #OpenSource
- Highlight the key progress made
- Stay under 280 characters
- Use an enthusiastic but professional tone
"""

        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text.strip()


def main():
    github_token = os.getenv("GITHUB_TOKEN")
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    github_username = os.getenv("GITHUB_USERNAME")

    if not all([github_token, anthropic_api_key, github_username]):
        print("Missing required environment variables:")
        print("- GITHUB_TOKEN: Your GitHub personal access token")
        print("- ANTHROPIC_API_KEY: Your Anthropic API key")
        print("- GITHUB_USERNAME: Your GitHub username")
        return

    try:
        # Initialize clients
        github_client = GitHubClient(github_token)
        content_generator = ContentGenerator(anthropic_api_key)

        # Get user repositories
        print(f"Fetching repositories for {github_username}...")
        repos = github_client.get_user_repos(github_username)
        print(f"Found {len(repos)} public repositories")

        # Find the most recent merged PR across all repos
        most_recent_pr = None
        most_recent_date = None
        most_recent_repo = None

        for repo in repos:
            repo_name = repo["name"]
            owner = repo["owner"]["login"]

            print(f"Checking {repo_name} for recent PRs...")
            try:
                merged_prs = github_client.get_recent_merged_prs(
                    owner, repo_name, limit=5
                )

                if merged_prs:
                    print(f"  Found {len(merged_prs)} merged PR(s) in {repo_name}")
                    for i, pr in enumerate(merged_prs):
                        merged_date = datetime.fromisoformat(
                            pr["merged_at"].replace("Z", "+00:00")
                        )
                        print(
                            f"    {i + 1}. '{pr['title']}' merged on {merged_date.strftime('%Y-%m-%d')}"
                        )

                        if most_recent_date is None or merged_date > most_recent_date:
                            most_recent_pr = pr
                            most_recent_date = merged_date
                            most_recent_repo = repo_name
                else:
                    print(f"  No merged PRs found in {repo_name}")
            except requests.exceptions.RequestException as e:
                print(f"  Error checking {repo_name}: {e}")
                continue

        if not most_recent_pr:
            print("\nNo recent merged PRs found. Looking for recent commits instead...")

            # Fallback to recent commits
            most_recent_commit = None
            most_recent_commit_date = None
            most_recent_commit_repo = None

            for repo in repos:
                repo_name = repo["name"]
                owner = repo["owner"]["login"]

                try:
                    commits = github_client.get_recent_commits(
                        owner, repo_name, limit=3
                    )
                    if commits:
                        for commit in commits:
                            commit_date = datetime.fromisoformat(
                                commit["commit"]["author"]["date"].replace(
                                    "Z", "+00:00"
                                )
                            )

                            if (
                                most_recent_commit_date is None
                                or commit_date > most_recent_commit_date
                            ):
                                most_recent_commit = commit
                                most_recent_commit_date = commit_date
                                most_recent_commit_repo = repo_name
                except requests.exceptions.RequestException:
                    continue

            if not most_recent_commit:
                print("No recent commits found either.")
                return

            print(f"\nMost recent commit found in {most_recent_commit_repo}:")
            print(f"Message: {most_recent_commit['commit']['message']}")
            print(f"Date: {most_recent_commit_date.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            print(f"SHA: {most_recent_commit['sha'][:7]}")
            print(f"URL: {most_recent_commit['html_url']}")

            # Generate content for commit
            print("\nGenerating LinkedIn post...")
            linkedin_post = content_generator.generate_commit_linkedin_post(
                most_recent_commit, most_recent_commit_repo
            )

            print("\nGenerating Twitter post...")
            twitter_post = content_generator.generate_commit_tweet(
                most_recent_commit, most_recent_commit_repo
            )

            # Display results
            print("\n" + "=" * 60)
            print("GENERATED CONTENT (Based on Recent Commit)")
            print("=" * 60)
            print("\nLINKEDIN POST:")
            print("-" * 40)
            print(linkedin_post)

            print("\nTWITTER POST:")
            print("-" * 40)
            print(twitter_post)
            print("\n" + "=" * 60)

            return

        print(f"\nMost recent PR found in {most_recent_repo}:")
        print(f"Title: {most_recent_pr['title']}")
        print(f"Merged: {most_recent_date.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"URL: {most_recent_pr['html_url']}")

        # Fetch CodeRabbit insights from PR comments
        print("\nFetching CodeRabbit insights from PR comments...")
        pr_number = most_recent_pr["number"]
        owner = most_recent_pr["base"]["repo"]["owner"]["login"]

        try:
            pr_comments = github_client.get_pr_comments(
                owner, most_recent_repo, pr_number
            )
            coderabbit_insights = github_client.extract_coderabbit_insights(pr_comments)

            if any(coderabbit_insights.values()):
                print(
                    f"Found CodeRabbit insights: {sum(len(v) if isinstance(v, list) else (1 if v else 0) for v in coderabbit_insights.values())} total insights"
                )
            else:
                print("No CodeRabbit insights found in PR comments")
                coderabbit_insights = None
        except Exception as e:
            print(f"Error fetching PR comments: {e}")
            coderabbit_insights = None

        # Generate content
        print("\nGenerating LinkedIn post...")
        linkedin_post = content_generator.generate_linkedin_post(
            most_recent_pr, most_recent_repo, coderabbit_insights
        )

        print("\nGenerating Twitter post...")
        twitter_post = content_generator.generate_tweet(
            most_recent_pr, most_recent_repo, coderabbit_insights
        )

        # Display results
        print("\n" + "=" * 60)
        print("GENERATED CONTENT")
        print("=" * 60)
        print("\nLINKEDIN POST:")
        print("-" * 40)
        print(linkedin_post)

        print("\nTWITTER POST:")
        print("-" * 40)
        print(twitter_post)
        print("\n" + "=" * 60)

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
