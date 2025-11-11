from ..llm.claude_client import ClaudeClient

def analyze_property(text: str) -> str:
    client = ClaudeClient()
    prompt = f"Analyze the following Swiss real estate document and extract key metrics:\n\n{text[:4000]}"
    return client.simple_completion(prompt)


