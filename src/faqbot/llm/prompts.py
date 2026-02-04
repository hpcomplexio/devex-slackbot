"""Prompt templates for Claude."""

from typing import List
from ..retrieval.store import SearchResult


SYSTEM_PROMPT = """You are a helpful FAQ bot that answers questions based ONLY on the provided context from a Notion FAQ page.

Rules:
1. Answer ONLY using information from the provided context
2. If the context doesn't contain the answer, say "I don't have information about that in the FAQ"
3. Keep answers concise (2-6 bullet points)
4. Always include a "Sources:" section at the end with Notion links
5. Use a helpful, professional tone
6. Do not make up or infer information not in the context"""


def build_user_prompt(question: str, results: List[SearchResult]) -> str:
    """Build user prompt with question and retrieved context.

    Args:
        question: User's question
        results: Search results with relevant FAQ chunks

    Returns:
        Formatted user prompt
    """
    # Build context from results
    context_parts = []
    for i, result in enumerate(results, 1):
        context_parts.append(f"[Context {i}]")
        context_parts.append(f"Heading: {result.chunk.heading}")
        context_parts.append(f"Content: {result.chunk.content}")
        context_parts.append(f"Source: {result.chunk.notion_url}")
        context_parts.append("")  # Blank line

    context = "\n".join(context_parts)

    # Build full prompt
    prompt = f"""Question: {question}

Context from FAQ:
{context}

Please answer the question using only the context provided above. Format your answer as 2-6 bullet points, and include a "Sources:" section at the end with the relevant Notion links."""

    return prompt


def format_answer_for_slack(answer: str) -> str:
    """Format Claude's answer for Slack (optional post-processing).

    Currently just returns the answer as-is, but could add formatting later.
    """
    return answer
