import asyncio
import os
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import AsyncSessionLocal, engine
from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User, Role
from app.models.department import Department
from app.models.document import Document, DocumentVersion, DocumentChunk
from app.models.chat import Chat, Message
from app.services.parser_service import ParserService
from app.services.chunking_service import ChunkingService
from app.rag.vectorstore.vector_service import VectorService
from app.utils.logger import logger

# Default role permissions mapping
DEFAULT_ROLES = [
    {
        "id": "ADMIN",
        "description": "System Administrator - full system access",
        "permissions": [
            "users:read", "users:write",
            "doc:upload", "doc:read", "doc:write",
            "chat:read", "chat:write",
            "analytics:read", "settings:write"
        ]
    },
    {
        "id": "MANAGER",
        "description": "Department Manager - upload and manage departmental documents",
        "permissions": [
            "doc:upload", "doc:read", "doc:write",
            "chat:read", "chat:write",
            "analytics:read"
        ]
    },
    {
        "id": "ENGINEER",
        "description": "Engineer - upload documents and interact with chatbot",
        "permissions": [
            "doc:upload", "doc:read",
            "chat:read", "chat:write"
        ]
    },
    {
        "id": "OPERATOR",
        "description": "Operator - interact with chatbot only",
        "permissions": [
            "chat:read", "chat:write"
        ]
    },
    {
        "id": "VIEWER",
        "description": "Viewer - read-only access to documents and public chats",
        "permissions": [
            "doc:read", "chat:read"
        ]
    }
]

async def seed_database(db: AsyncSession) -> None:
    """Seed roles, department, default admin, demo user, corporate docs, and sample chats."""
    logger.info("Starting database seeding...")

    # 1. Seed Roles
    for role_data in DEFAULT_ROLES:
        query = select(Role).where(Role.id == role_data["id"])
        result = await db.execute(query)
        db_role = result.scalar_one_or_none()

        if not db_role:
            logger.info(f"Seeding Role: {role_data['id']}")
            role = Role(
                id=role_data["id"],
                description=role_data["description"],
                permissions=role_data["permissions"]
            )
            db.add(role)
        else:
            logger.info(f"Role {role_data['id']} already exists. Updating permissions.")
            db_role.permissions = role_data["permissions"]
            db_role.description = role_data["description"]
            db.add(db_role)

    await db.flush()

    # 2. Seed Default Department
    query = select(Department).where(Department.code == settings.INITIAL_ADMIN_DEPARTMENT_CODE)
    result = await db.execute(query)
    db_dept = result.scalar_one_or_none()

    if not db_dept:
        logger.info(f"Seeding default department: {settings.INITIAL_ADMIN_DEPARTMENT}")
        db_dept = Department(
            name=settings.INITIAL_ADMIN_DEPARTMENT,
            code=settings.INITIAL_ADMIN_DEPARTMENT_CODE
        )
        db.add(db_dept)
        await db.flush()
    else:
        logger.info(f"Department {settings.INITIAL_ADMIN_DEPARTMENT_CODE} already exists.")

    # 3. Seed Admin User
    query = select(User).where(User.email == settings.INITIAL_ADMIN_EMAIL)
    result = await db.execute(query)
    db_admin = result.scalar_one_or_none()

    if not db_admin:
        logger.info(f"Seeding admin user: {settings.INITIAL_ADMIN_EMAIL}")
        admin_pwd = hash_password(settings.INITIAL_ADMIN_PASSWORD)
        admin = User(
            email=settings.INITIAL_ADMIN_EMAIL,
            hashed_password=admin_pwd,
            full_name=settings.INITIAL_ADMIN_FULL_NAME,
            role_id="ADMIN",
            department_id=db_dept.id,
            is_active=True
        )
        db.add(admin)
    else:
        logger.info(f"Admin user {settings.INITIAL_ADMIN_EMAIL} already exists.")

    # 4. Seed Recruiter Demo User
    demo_email = "demo@enterprise-rag.ai"
    query = select(User).where(User.email == demo_email)
    result = await db.execute(query)
    db_demo = result.scalar_one_or_none()

    if not db_demo:
        logger.info(f"Seeding recruiter demo user: {demo_email}")
        demo_pwd = hash_password("Demo@123")
        db_demo = User(
            email=demo_email,
            hashed_password=demo_pwd,
            full_name="Recruiter Demo Session",
            role_id="ENGINEER",  # ENGINEER role can upload/chat, but cannot write other users
            department_id=db_dept.id,
            is_active=True
        )
        db.add(db_demo)
        await db.flush()
    else:
        logger.info(f"Demo user {demo_email} already exists.")

    await db.commit()

    # 5. Seed Corporate Sample Documents
    sample_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "sample_documents"))
    if os.path.exists(sample_dir):
        logger.info(f"Sample documents directory found at {sample_dir}. Running index ingestion...")
        files_to_seed = [
            "leave_policy.txt",
            "information_security_policy.txt",
            "remote_work_policy.txt",
            "it_asset_policy.txt"
        ]
        
        for filename in files_to_seed:
            file_path = os.path.join(sample_dir, filename)
            if not os.path.exists(file_path):
                continue
            
            # Check if already indexed
            doc_query = select(Document).where(Document.filename == filename, Document.department_id == db_dept.id)
            doc_result = await db.execute(doc_query)
            existing_doc = doc_result.scalar_one_or_none()
            
            if existing_doc:
                logger.info(f"Document {filename} is already indexed. Skipping.")
                continue

            logger.info(f"Seeding document index: {filename}")
            
            # Create metadata entry
            doc_id = uuid.uuid4()
            db_doc = Document(
                id=doc_id,
                filename=filename,
                department_id=db_dept.id,
                owner_id=db_demo.id,
                current_version=1,
                status="COMPLETED"
            )
            db.add(db_doc)
            
            # Create version entry
            version_id = uuid.uuid4()
            db_version = DocumentVersion(
                id=version_id,
                document_id=doc_id,
                version=1,
                file_hash=filename,  # mock hash
                file_size=os.path.getsize(file_path),
                file_path=file_path,
                mime_type="text/plain"
            )
            db.add(db_version)
            await db.flush()

            # Parse and chunk document
            parser = ParserService()
            parsed_pages = parser.parse_file(file_path, ".txt")
            
            chunking = ChunkingService()
            chunks_dto = chunking.split_pages(parsed_pages)
            
            vector_service = VectorService()
            texts = [chunk.text for chunk in chunks_dto]
            metadatas = [
                {
                    "document_id": str(doc_id),
                    "version_id": str(version_id),
                    "filename": filename,
                    "page_number": chunk.page_number,
                    "chunk_index": chunk.chunk_index
                }
                for chunk in chunks_dto
            ]
            
            # Load and write to FAISS
            vector_index_ids = vector_service.add_chunks(db_dept.id, texts, metadatas)
            
            # Save chunks to database
            db_chunks = [
                DocumentChunk(
                    document_version_id=version_id,
                    chunk_index=chunk.chunk_index,
                    text_content=chunk.text,
                    page_number=chunk.page_number,
                    vector_index_id=vector_index_ids[chunk.chunk_index]
                )
                for chunk in chunks_dto
            ]
            
            db.add_all(db_chunks)
            db_version.page_count = len(parsed_pages)
            db_version.chunk_count = len(chunks_dto)
            
            await db.commit()
            logger.info(f"Indexed document {filename} successfully ({len(chunks_dto)} chunks created).")

    # 6. Seed Sample Chat Transcript for Recruiter Review
    chat_query = select(Chat).where(Chat.user_id == db_demo.id)
    chat_result = await db.execute(chat_query)
    existing_chat = chat_result.scalars().first()
    
    if not existing_chat:
        logger.info("Seeding sample HR chat history for Demo user...")
        chat_id = uuid.uuid4()
        db_chat = Chat(
            id=chat_id,
            title="HR & Security Compliance Consultation",
            user_id=db_demo.id,
            department_id=db_dept.id
        )
        db.add(db_chat)
        
        # User message
        msg_user_id = uuid.uuid4()
        db_msg_user = Message(
            id=msg_user_id,
            chat_id=chat_id,
            role="user",
            content="Can you summarize the remote work core days and the internet stipend?"
        )
        db.add(db_msg_user)
        
        # Assistant response grounded in remote_work_policy.txt
        msg_assist_id = uuid.uuid4()
        db_msg_assist = Message(
            id=msg_assist_id,
            chat_id=chat_id,
            role="assistant",
            content="According to the Remote Work Policy:\n\n1. **Hybrid Core Days**: Tuesday and Thursday are designated as Mandatory Core Days, requiring in-person attendance at the office. You are eligible to work remotely up to three days per week on other days.\n2. **Internet Stipend**: The company automatically provides a monthly internet and mobile connectivity stipend of $50, added to your salary. A connection of at least 50 Mbps download speed is required.",
            confidence_score=0.98,
            latency_ms=120,
            citations=[
                {
                    "id": "REF-1",
                    "filename": "remote_work_policy.txt",
                    "page_number": 1,
                    "chunk_index": 0,
                    "snippet": "Tuesday and Thursday are designated as Mandatory Core Days, during which all team members are required to attend the office...",
                    "score": 0.12
                },
                {
                    "id": "REF-2",
                    "filename": "remote_work_policy.txt",
                    "page_number": 1,
                    "chunk_index": 2,
                    "snippet": "The company provides a monthly internet and mobile connectivity stipend of $50, added automatically to the monthly salary payment...",
                    "score": 0.15
                }
            ],
            related_questions=[
                "What is the home office ergonomics stipend amount?",
                "How do I submit receipts for reimbursement?",
                "Who is eligible for remote internet stipends?"
            ]
        )
        db.add(db_msg_assist)
        await db.commit()
        logger.info("Sample chat transcript seeded successfully.")

    logger.info("Database seeding successfully completed.")

async def main():
    async with AsyncSessionLocal() as session:
        await seed_database(session)
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
