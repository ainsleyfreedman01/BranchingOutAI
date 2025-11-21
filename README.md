# BranchingOutAI

BranchingOutAI is an interactive career exploration tool that uses a graph-based AI agent
to help users explore industries, jobs, and skills. Instead of static recommendations,
it allows users to move through non-linear career paths and visually see how roles connect
and evolve.

The frontend visualizes branching career paths using JointJS, and the backend handles
AI reasoning, memory, and live job data integration.

This project is currently an **in-progress build** and is being actively designed and iterated on.

## Tech Stack

**Frontend**
- Next.js  
- Tailwind CSS  
- JointJS (graph visualization)

**Backend**
- FastAPI  
- LangGraph  
- OpenAI API  

**Database / Storage**
- Supabase  

**External Data**
- TheirStack API (live job market data)

## Memory & Personalization

User memory, stored in **Supabase**, tracks:

- Stated interests  
- Visited roles  
- Explored career paths  
- Session interactions  

This enables personalized recommendations, avoids repetition, and maintains long-term exploration continuity.

It also lays the groundwork for future features like user accounts, saved dashboards, and progress tracking.

## Current Challenges

Active development challenges include:

- Designing the LangGraph agent to reason structurally, not just textually  
- Preventing graph clutter as paths expand  
- Balancing open exploration with guided direction  
- Handling TheirStack API rate limits and response latency  
- Ensuring the UI stays intuitive despite complex underlying logic  

## Planned Features & Roadmap

Future planned or proposed improvements:

- User authentication & profiles  
- Exportable career roadmaps  
- Skill gap analysis and recommendations  
- Learning resource suggestions  
- Multi-path comparison mode  
- Improved graph layout algorithms  
- Mobile responsiveness  
- Accessibility improvements  

## Design Philosophy

BranchingOutAI is built around the idea that career exploration shouldn’t feel like a test
or a one-directional funnel.

Instead of forcing users into narrow outcomes, it treats careers like a connected system,
where exploration, curiosity, and iteration are part of the process.

The goal is to make users feel like they are navigating a map of possibilities — not
being told what to do.

## Project Status

BranchingOutAI is currently in active development.

Core architecture and reasoning systems are still evolving as features are added,
behavior is tested, and the user experience is refined through iteration.

## Setup Instructions

1. Clone the repository  
2. Frontend setup:
   ```bash
   cd frontend
   npm install
   npm run dev
3. Backend setup:
   ```bash
   cd backend
   ```
   
    Create and activate a virtual environment
   ```python3 -m venv .venv
   source .venv/bin/activate
   ```
   Install dependencies
 
   ```pip install -r requirements.txt```
   
    Start the FastAPI server

   ```uvicorn app.main:app --reload```
  4. Environment Variables:
     
     Create a ```.env``` file inside the ```backend/``` directory with the following variables:

     ```OPENAI_API_KEY=your_key_here
     SUPABASE_URL=your_url_here
     SUPABASE_KEY=your_key_here
     THEIRSTACK_API_KEY=your_key_here
