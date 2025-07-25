def find_last_user_message(messages: list) -> str | None:
    """
    Finds and returns the content of the last user message in a list of messages.
    """
    for msg in reversed(messages):
        if msg.get("role") == "user":
            return msg.get("content")
    return None