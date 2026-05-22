"""MCP schemas for search_fitness_knowledge tool."""

from pydantic import BaseModel, Field
from typing import Optional


class MCPSearchKnowledgeRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Fitness question to search for")
    top_k: int = Field(default=3, ge=1, le=10, description="Max results (1-10)")
