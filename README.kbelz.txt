cd backend
source .venv/bin/activate
which -a python   
python -m uvicorn app.main:app --reload --port 8000

cd frontend
npm run dev