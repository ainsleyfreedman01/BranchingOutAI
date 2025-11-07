# BranchingOutAI

BranchingOutAI is an interactive career exploration tool that uses a graph-based AI agent
to help users explore industries, jobs, and skills. The frontend visualizes branching career paths 
using JointJS, and the backend handles AI reasoning, memory, and job data integration.

## Tech Stack

- Frontend: Next.js + Tailwind CSS
- Backend: FastAPI + LangGraph + OpenAI
- Database: Supabase
- Job Data: TheirStack API

## Setup Instructions

1. Clone repo
2. Frontend: `cd frontend` → `npm install` → `npm run dev`
3. Backend: `cd backend` → `python3 -m venv .venv` → `source .venv/bin/activate` → `pip install -r requirements.txt` → `uvicorn app.main:app --reload`
4. Create `.env` with API keys for OpenAI, Supabase, and TheirStack