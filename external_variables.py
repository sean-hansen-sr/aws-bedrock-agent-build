from pydantic import BaseModel, Field
from typing import Optional

class Request(BaseModel):
    # The unique identifier for this conversation/user session
    session_id: str = Field(
        ..., 
        description="The unique session ID from the front end to fetch chat history from DynamoDB"
    )
    
    # The new incoming message from the user
    current_message: str = Field(
        ..., 
        description="The latest input text from the user to pass to the agent"
    )
    
    # Optional runtime configuration overrides for the Bedrock Model
    system_prompt: Optional[str] = Field(
        default= """You are a snarky and sarcastic assistant. You provide witty and humorous responses to user queries, 
                often with a touch of irony. Your goal is to entertain while assisting, making the interaction enjoyable and memorable."""
    )

    temperature: Optional[float] = Field(
        default=0.7, 
        ge=0.0, 
        le=1.0, 
        description="Controls creativity of the model response"
    )
    
    max_tokens: Optional[int] = Field(
        default=2048, 
        gt=0, 
        description="Maximum number of tokens to generate in the response"
    )