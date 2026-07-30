import os
import subprocess
import urllib.request
import json
from openai import OpenAI

def get_git_diff():
    """Gets the changes between the PR branch and the target branch."""
    try:
        target_branch = os.environ.get("GITHUB_BASE_REF", "main")
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
    """Sends the diff to OpenRouter using Nvidia Nemotron 3 Ultra."""
    # Initialize the client pointing to OpenRouter
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ.get("OPENROUTER_API_KEY")
    )
    
    prompt = (
        "You are an expert code reviewer. Review the following git diff for bugs, "
        "security vulnerabilities, performance issues, and clean code practices. "
        "Provide constructive feedback with code examples where applicable. "
        "Keep your response concise and formatted in Markdown.\n\n"
        f"```diff\n{diff_content}\n```"
    )

    # OpenRouter free tier models require extra headers passed via extra_headers
    response = client.chat.completions.create(
        model="nvidia/nemotron-3-ultra-550b-a55b:free", 
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        extra_headers={
            "HTTP-Referer": "https://github.com", # Required by OpenRouter free-tier
            "X-Title": "GitHub Actions AI Code Reviewer"
        }
    )
    return response.choices.message.content

def post_github_comment(comment):
    """Posts the AI review as a comment on the Pull Request."""
    token = os.environ["GITHUB_TOKEN"]
    repo = os.environ["REPO"]
    pr_number = os.environ["PR_NUMBER"]
    
    url = f"https://github.com{repo}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    data = json.dumps({"body": comment}).encode("utf-8")
    
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 201:
                print("Review comment posted successfully.")
    except Exception as e:
        print(f"Failed to post comment to GitHub: {e}")

def main():
    diff = get_git_diff()
    if not diff or diff.strip() == "":
        print("No code changes detected or error fetching diff.")
        return

    print("Analyzing code changes with NVIDIA Nemotron-3-Ultra...")
    review = get_ai_review(diff)
    
    print("Posting review to Pull Request...")
    post_github_comment(review)

if __name__ == "__main__":
    main()
