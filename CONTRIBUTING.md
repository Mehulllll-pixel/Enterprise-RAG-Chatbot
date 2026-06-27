# Contributing to Enterprise RAG Chatbot

Thank you for your interest in contributing to our project! We welcome contributions from developers of all skill levels.

---

## 1. Code of Conduct

Please read and adhere to our [Code of Conduct](CODE_OF_CONDUCT.md) in all community interactions.

## 2. Getting Started

1.  **Fork the Repository:** Create a personal fork on GitHub.
2.  **Clone Locally:** Clone your fork using:
    ```bash
    git clone https://github.com/your-username/enterprise-rag-chatbot.git
    ```
3.  **Configure Environment:** Follow the local setup instructions in the [README.md](README.md).

## 3. Branching Strategy

We follow a structured branching model:
*   `master` / `main`: Production-ready releases.
*   `develop`: Integration branch for active features.
*   `feature/<name>`: Feature-specific branches branched off `develop`.
*   `bugfix/<name>`: Bugfix branches branched off `develop`.

## 4. Development Workflow

1.  Create a branch from `develop`:
    ```bash
    git checkout -b feature/amazing-feature
    ```
2.  Implement your changes, writing tests where appropriate.
3.  Format your code and verify test suite runs cleanly:
    *   **Backend:** `pytest`
    *   **Frontend:** `npm run build`
4.  Commit your work using semantic commit messages:
    *   `feat: add support for doc previews`
    *   `fix: resolve JWT expiration race condition`
    *   `docs: update API endpoints guides`
5.  Push your branch to GitHub and submit a Pull Request to `develop`.

## 5. Coding Standards

### Backend (Python)
*   Adhere to **PEP 8** style guidelines.
*   Add descriptive docstrings and type hints to all public functions and classes.
*   Keep files focused and modular following clean architecture.

### Frontend (React/TypeScript)
*   Ensure all code compiles under strict compiler configurations.
*   Maintain responsive layouts utilizing Tailwind CSS styling classes.
*   Avoid using placeholder/untyped variables.
