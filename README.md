# StartObserving

AI-powered business data analyst that proactively pushes insights to users.

## Project Structure

```
├── frontend/          # Vue 3 + Vite + TypeScript
│   ├── src/
│   │   ├── api/       # API client (to be implemented)
│   │   ├── components/
│   │   ├── router/    # Vue Router config
│   │   ├── stores/    # Pinia state management
│   │   ├── types/     # TypeScript types
│   │   └── views/     # Page components
│   └── ...
│
└── backend/           # Python FastAPI (to be implemented)
    └── app/
        ├── api/       # Route handlers
        ├── core/      # Config, auth, db
        ├── models/    # SQLAlchemy models
        ├── schemas/   # Pydantic schemas
        └── services/  # Business logic + AI
```

## Getting Started

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at http://localhost:3000

### Backend (Coming Soon)

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Tech Stack

- **Frontend**: Vue 3, Vite, TypeScript, Tailwind CSS, Pinia, Vue Router
- **Backend**: Python, FastAPI, SQLAlchemy, PostgreSQL
- **AI**: Claude API for data analysis
