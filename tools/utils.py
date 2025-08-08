import re
import httpx

async def is_git_url_reachable(url: str) -> bool:
    """
    Checks if a given URL is reachable via an HTTP HEAD request.
    
    Args:
        url: The URL to check.
        
    Returns:
        True if the URL is reachable and returns a 2xx status code, False otherwise.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.head(url, timeout=5)
            return 200 <= response.status_code < 300
    except httpx.RequestError:
        return False

def find_last_user_message(messages: list, role: str = "user") -> str | None:
    """
    Finds and returns the content of the last message with the specified role.
    
    Args:
        messages: List of message dictionaries
        role: Role to search for (default: "user")
        
    Returns:
        Content of the last message with the specified role, or None if not found
    """
    for msg in reversed(messages):
        if msg.role == role:
            content = msg.content
            return content if content is not None else ""
    return None

def extract_git_url(text: str) -> str | None:
    """
    Extracts a Git repository URL from the given text.
    
    Args:
        text: The input string to search for a Git URL.
        
    Returns:
        The extracted Git URL string, or None if no URL is found.
    """
    # Basic regex for common Git repository URLs (GitHub, GitLab, Bitbucket, etc.)
    # This regex is simplified and might need refinement for edge cases.
    git_url_pattern = r"https?://[\w.-]+(?:/[\w.-]+)+(?:\.git)?(?:/)?"
    match = re.search(git_url_pattern, text)
    if match:
        return match.group(0)
    return None