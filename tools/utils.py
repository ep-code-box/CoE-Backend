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
        if msg.get("role") == role:
            return msg.get("content")
    return None