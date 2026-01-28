# Start DEV

1. Start Database and LLM with Docker:
      docker-compose up db ollama -d

2. Start Backend Locally (for faster iteration):
      cd backend
   source venv/bin/activate  # or create venv if needed
    DATABASE_URL=postgresql://postgres:postgres@localhost:5432/community_resilience \
    OLLAMA_BASE_URL=http://localhost:11434 \
    uvicorn app:app --host 0.0.0.0 --port 8000 --reload

The backend should now start successfully and be accessible at:

- API: <http://localhost:8000>
-Documentation: <http://localhost:8000/docs>

3. Start Frontend Locally:
      cd frontend
   pnpm run dev

Access Points:

- Frontend: <http://localhost:5173>
- Backend API: <http://localhost:8000>
- API Documentation: <http://localhost:8000/docs>
- Database: localhost:5432
- Ollama API: <http://localhost:11434>
