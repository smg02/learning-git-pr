import os
import sys
import subprocess
import urllib.request
import json
from google import genai

def get_git_diff():
    """Gets the changes between the PR branch and the target branch."""
    try:
        target_branch = os.environ.get("GITHUB_BASE_REF", "main")
        print(f"Fetching target branch: origin/{target_branch}")
        subprocess.run(["git", "fetch", "origin", target_branch], check=True)
        
        result = subprocess.run(
            ["git", "diff", f"origin/{target_branch}...HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error fetching git diff: {e}")
        return None

def get_ai_review(diff_content):
    """Sends the diff to the native Gemini API using the 3.6/3.5 family."""
    api_key = os.environ.get("AI_API_KEY")
    if not api_key:
        print("Error: AI_API_KEY environment variable is missing.")
        sys.exit(1)

    # Initialize native Google GenAI Client
    client = genai.Client(api_key=api_key)
    
    prompt = (
        "You are an expert code reviewer. Review the following git diff for bugs, "
        "security vulnerabilities, performance issues, and clean code practices. "
        "Provide constructive feedback with code examples where applicable. "
        "Keep your response concise and formatted in Markdown.\n\n"
        f"```diff\n{diff_content}\n```"
    )

    # Sequential models fallback list to avoid 503 unavailability issues
    models_to_try = ["gemini-3.6-flash", "gemini-3.5-flash"]
    
    for model_name in models_to_try:
        try:
            print(f"Attempting analysis using model: {model_name}...")
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            if response.text:
                print(f"Successfully obtained code review from {model_name}.")
                return response.text
        except Exception as e:
            print(f"Model {model_name} was unavailable or returned an error: {e}")
            continue

    print("Error: All fallback Gemini models failed or were unavailable.")
    sys.exit(1)

def post_github_comment(comment):
    """Posts the AI review as a comment on the Pull Request."""
    token = os.environ["GITHUB_TOKEN"]
    repo = os.environ["REPO"]
    pr_number = os.environ["PR_NUMBER"]
    
    # Corrected the URL to properly format with a slash delimiter
    url = f"https://github.com{repo}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json"
    }
    data = json.dumps({"body": comment}).encode("utf-8")
    
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 201:
                print("Review comment posted successfully.")
    except Exception as e:
        print(f"Failed to post comment to GitHub API: {e}")

def main():
    diff = get_git_diff()
    if not diff or diff.strip() == "":
        print("No code changes detected or error fetching diff.")
        return

    print("Analyzing code changes with Google Gemini...")
    review = get_ai_review(diff)
    
    print("Posting review to Pull Request...")
    post_github_comment(review)

if __name__ == "__main__":
    main()
