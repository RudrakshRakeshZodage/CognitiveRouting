import os
from typing import List, Dict
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.docstore.document import Document

load_dotenv()

class PersonaRouter:
    def __init__(self):
        # Using OpenAI embeddings by default
        self.embeddings = OpenAIEmbeddings()
        # Initialize in-memory ChromaDB
        self.vector_store = Chroma(
            collection_name="bot_personas",
            embedding_function=self.embeddings
        )
        self._initialize_personas()

    def _initialize_personas(self):
        personas = [
            {
                "id": "Bot A (Tech Maximalist)",
                "text": "I believe AI and crypto will solve all human problems. I am highly optimistic about technology, Elon Musk, and space exploration. I dismiss regulatory concerns."
            },
            {
                "id": "Bot B (Doomer / Skeptic)",
                "text": "I believe late-stage capitalism and tech monopolies are destroying society. I am highly critical of AI, social media, and billionaires. I value privacy and nature."
            },
            {
                "id": "Bot C (Finance Bro)",
                "text": "I strictly care about markets, interest rates, trading algorithms, and making money. I speak in finance jargon and view everything through the lens of ROI."
            }
        ]
        
        documents = [
            Document(page_content=p["text"], metadata={"id": p["id"]})
            for p in personas
        ]
        self.vector_store.add_documents(documents)

    def route_post_to_bots(self, post_content: str, threshold: float = 0.85) -> List[str]:
        """
        [CORE LOGIC]: Queries the vector store and returns bots with cosine similarity > threshold.
        This ensures that only bots with a persona relevant to the post topic are selected.
        """
        # relevance_score_fn in LangChain Chroma often returns 1 - distance
        results = self.vector_store.similarity_search_with_relevance_scores(post_content, k=3)
        
        matched_bots = []
        for doc, score in results:
            if score > threshold:
                matched_bots.append(doc.metadata["id"])
        
        return matched_bots

if __name__ == "__main__":
    router = PersonaRouter()
    test_post = "OpenAI just released a new model that might replace junior developers."
    matches = router.route_post_to_bots(test_post)
    print(f"Post: {test_post}")
    print(f"Matched Bots: {matches}")
