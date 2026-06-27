from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.services.parser_service import ParsedPage
from app.utils.logger import logger

class DocumentChunkDTO:
    """Data Transfer Object containing split text content and its original page number."""
    def __init__(self, text: str, page_number: int, chunk_index: int):
        self.text = text
        self.page_number = page_number
        self.chunk_index = chunk_index

class ChunkingService:
    """Service handling text splitting using recursive separator hierarchies."""
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )

    def split_pages(self, pages: List[ParsedPage]) -> List[DocumentChunkDTO]:
        """Split a list of parsed pages into overlapping document chunks, maintaining page references."""
        chunks: List[DocumentChunkDTO] = []
        chunk_counter = 0

        for page in pages:
            if not page.text.strip():
                continue
            # Split the text of this specific page
            split_texts = self.splitter.split_text(page.text)
            for split_text in split_texts:
                chunks.append(DocumentChunkDTO(
                    text=split_text.strip(),
                    page_number=page.page_number,
                    chunk_index=chunk_counter
                ))
                chunk_counter += 1

        logger.info(
            f"Successfully chunked documents into {len(chunks)} fragments "
            f"(Size: {self.chunk_size}, Overlap: {self.chunk_overlap})"
        )
        return chunks
