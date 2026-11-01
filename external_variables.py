from pydantic import BaseModel
from typing import List, Optional

# Individual message item format matching Amazon Nova's expected schema
class MessageContent(BaseModel):
    text: str

class ChatMessage(BaseModel):
    role: str  # Must alternatingly be "user" or "assistant"
    content: List[MessageContent]

# Request schema accepting the entire message thread history
class MultiTurnRequest(BaseModel):
    messages: List[ChatMessage]
    max_tokens: int = 512
    temperature: float = 0.7
    system_prompt: Optional[str] = """You are a snarky and sarcastic assistant. You provide witty and humorous responses to user queries, 
    often with a touch of irony. Your goal is to entertain while assisting, making the interaction enjoyable and memorable."""