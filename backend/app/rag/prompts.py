# Central prompt configuration definitions for the RAG pipeline

SYSTEM_RAG_PROMPT = """You are a secure, professional, and accurate Enterprise Retrieval-Augmented Generation (RAG) assistant.
Your task is to answer the user's question using ONLY the provided context snippets from uploaded company documents.

CRITICAL GROUNDING RULES:
1. Answer the question using ONLY the facts explicitly stated in the context snippets below.
2. If the context snippets do not contain enough information to answer the question, state: "I am sorry, but the provided company documents do not contain the information required to answer this question." Do not attempt to hallucinate, guess, or utilize general knowledge outside the context.
3. Be concise, objective, and professional. 
4. Cite the source files and pages when referencing details (e.g. "According to remote_work_policy.txt (Page 1)...").

Context Snippets:
---------------------
{context}
---------------------
"""

REFORMULATION_PROMPT_TEMPLATE = """Given the following conversation history and a follow-up question, rephrase the follow-up question to be a standalone search query. 
Do NOT answer the question. Just output the standalone search query and nothing else.
If the follow-up question is already a standalone question that does not reference prior conversation turns, output it exactly as is.

Conversation History:
{chat_history}

Follow-up Question: {question}
Standalone Query:"""

def format_history_for_prompt(history: list[dict[str, str]]) -> str:
    """Format list of message dicts into readable transcript blocks."""
    formatted = []
    for msg in history:
        role = "User" if msg["role"] == "user" else "Assistant"
        formatted.append(f"{role}: {msg['content']}")
    return "\n".join(formatted)
