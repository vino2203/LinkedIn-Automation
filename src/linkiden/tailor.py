"""Truthfulness check for tailored resumes: every known tech term in the output must exist in the verified skill set."""
from __future__ import annotations
import re
from pathlib import Path

# vocabulary of claim-worthy terms; anything here appearing in a tailored resume must be backed by skills_evidence/resume
VOCAB = ["python", "java", "selenium", "playwright", "pytest", "postman", "jmeter", "langchain", "langgraph", "llamaindex", "crewai", "autogen",
         "openai", "anthropic", "faiss", "pinecone", "chroma", "weaviate", "neo4j", "fastapi", "streamlit", "flask", "docker", "kubernetes",
         "aws", "azure", "gcp", "terraform", "jenkins", "github actions", "deepeval", "ragas", "langsmith", "mcp", "n8n", "pytorch", "tensorflow",
         "hugging face", "mlflow", "kafka", "redis", "mongodb", "postgresql", "mysql", "sql", "rest api", "ci/cd", "bm25", "rag", "graphrag"]

def allowed_skills(root: Path) -> set[str]:
    """Terms present in resume.md + the VERIFIED part of skills_evidence.md (stops before 'Need user confirmation')."""
    ev = (root / "context" / "skills_evidence.md").read_text()
    ev = ev.split("## Need user confirmation")[0]
    corpus = ((root / "context" / "resume.md").read_text() + ev).lower()
    return {t for t in VOCAB if re.search(rf"(?<![a-z0-9]){re.escape(t)}(?![a-z0-9])", corpus)}

def unverified_claims(text: str, allowed: set[str]) -> set[str]:
    low = text.lower()
    return {t for t in VOCAB if t not in allowed and re.search(rf"(?<![a-z0-9]){re.escape(t)}(?![a-z0-9])", low)}
