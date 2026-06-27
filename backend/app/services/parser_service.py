import os
from typing import List, Dict, Any
from pypdf import PdfReader
from docx import Document
from app.core.exceptions import ValidationException
from app.utils.logger import logger

class ParsedPage:
    """Represents a single page or segment of parsed text content."""
    def __init__(self, text: str, page_number: int):
        self.text = text
        self.page_number = page_number

class ParserService:
    """Service responsible for extracting text from PDF, DOCX, TXT, and Markdown files."""
    
    @staticmethod
    def parse_pdf(file_path: str) -> List[ParsedPage]:
        """Extract text page by page from PDF using PyPDF."""
        parsed_pages: List[ParsedPage] = []
        try:
            reader = PdfReader(file_path)
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                # Simple text normalization
                text = text.strip()
                parsed_pages.append(ParsedPage(text=text, page_number=i + 1))
            logger.info(f"Successfully parsed PDF at {file_path} (Pages: {len(parsed_pages)})")
            return parsed_pages
        except Exception as e:
            logger.error(f"Error parsing PDF at {file_path}: {str(e)}")
            raise ValidationException(f"Failed to parse PDF document: {str(e)}")

    @staticmethod
    def parse_docx(file_path: str) -> List[ParsedPage]:
        """Extract text from Docx using python-docx."""
        parsed_pages: List[ParsedPage] = []
        try:
            doc = Document(file_path)
            # Word documents don't have explicit pages in python-docx, so we group paragraphs
            # We treat blocks of paragraphs (e.g. every 10 paragraphs) as a "page" to support citations
            current_text: List[str] = []
            page_counter = 1
            
            for i, para in enumerate(doc.paragraphs):
                if para.text.strip():
                    current_text.append(para.text.strip())
                
                # Treat every 10 non-empty paragraphs as a page
                if len(current_text) >= 10:
                    page_text = "\n\n".join(current_text)
                    parsed_pages.append(ParsedPage(text=page_text, page_number=page_counter))
                    current_text = []
                    page_counter += 1
            
            # Catch leftover paragraphs
            if current_text:
                page_text = "\n\n".join(current_text)
                parsed_pages.append(ParsedPage(text=page_text, page_number=page_counter))
                
            logger.info(f"Successfully parsed DOCX at {file_path} (Pseudo-Pages: {len(parsed_pages)})")
            return parsed_pages
        except Exception as e:
            logger.error(f"Error parsing DOCX at {file_path}: {str(e)}")
            raise ValidationException(f"Failed to parse DOCX document: {str(e)}")

    @staticmethod
    def parse_txt(file_path: str) -> List[ParsedPage]:
        """Extract text from a plain text file, handling encoding fallbacks."""
        try:
            # Try UTF-8 first, fallback to CP1252/latin-1
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except UnicodeDecodeError:
                with open(file_path, "r", encoding="cp1252") as f:
                    content = f.read()

            content = content.strip()
            # Text files are read as a single page
            logger.info(f"Successfully parsed TXT file at {file_path}")
            return [ParsedPage(text=content, page_number=1)]
        except Exception as e:
            logger.error(f"Error parsing TXT at {file_path}: {str(e)}")
            raise ValidationException(f"Failed to parse TXT file: {str(e)}")

    @staticmethod
    def parse_markdown(file_path: str) -> List[ParsedPage]:
        """Extract text from Markdown file. Handled similarly to TXT."""
        # Markdown is processed as text, chunking will split logically
        try:
            pages = ParserService.parse_txt(file_path)
            logger.info(f"Successfully parsed Markdown file at {file_path}")
            return pages
        except Exception as e:
            logger.error(f"Error parsing Markdown at {file_path}: {str(e)}")
            raise

    def parse_file(self, file_path: str, extension: str) -> List[ParsedPage]:
        """Orchestrate parsing based on file extension."""
        ext = extension.lower()
        if ext == ".pdf":
            return self.parse_pdf(file_path)
        elif ext == ".docx":
            return self.parse_docx(file_path)
        elif ext == ".txt":
            return self.parse_txt(file_path)
        elif ext == ".md":
            return self.parse_markdown(file_path)
        else:
            raise ValidationException(f"Unsupported file type extension: {extension}")
