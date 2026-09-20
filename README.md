# Command Centre // Personal Life & Academic OS

A full-stack personal "Command Centre" multi-workspace platform consolidating:
1. **Day-to-Day / Life Workspace (`/daily`)**: Automated physical activity metrics from **Garmin Connect**, free-form daily journaling with structured **LLM extraction** for nutritional estimates (`NutritionLog`) and social/entity CRM profiles (`Person`, `Interaction`), and daily balance summaries.
2. **University Academic Workspace (`/uni`)**: Complete academic tracking inspired by the student dashboard architecture (modules, coursework deadlines countdown with urgency badges `< 48h`, `< 7d`, grade weightings, and study task checklist).
3. **People Network CRM (`/people`)**: Searchable directory of contacts, cumulative notes/facts, and reverse-chronological interaction timelines.
4. **AI Intelligence Assistant (`/chat`)**: Unified conversational chat interface with full context and structured retrieval tools across both Life and Uni, featuring SSE streaming and expandable source citation pills.

---

## Workspaces & Core Modules

### 1. Day-to-Day Life Workspace (`/daily`)
- **Garmin Connect Ingestion**:
  - Pulls daily steps, active/resting calories, distance, resting HR, sleep duration & score, and workout breakdown.
  - Session token persistence in `.garmin_tokens` directory to prevent repeated 2FA challenges.
  - Background sync via **APScheduler** (daily at 23:30) and on-demand manual **"Sync Now"** button.
  - Realistic offline simulation fallback when credentials are not supplied or Garmin is offline.
- **Daily Journaling & AI Extraction**:
  - Free-form text input with instant JSON schema extraction.
  - **Nutrition Analysis**: Food/drink items, portion sizes, calories, and macronutrient splits (protein, carbs, fat) written to the `NutritionLog` table.
  - **Entity & People CRM**: Identifies mentioned individuals, context, sentiment, locations, and newly learned facts; automatically creates/updates `Person` and logs `Interaction`.
  - **Themes & Sentiment**: 1-sentence summary, mood badge, and thematic hashtags.
- **Command Stat Cards**:
  - Steps progress ring against goal (SVG circle).
  - Energy Balance: Calories burned (Garmin active + BMR) vs. calories consumed (Journal nutrition log) with net surplus/deficit tag.
  - Sleep duration & recovery score.
  - Day wellness and focus summary.

### 2. University Academic Workspace (`/uni`)
- **Modules Overview**:
  - Track academic modules (e.g. `COMP3001 Distributed Systems`, `COMP3002 Machine Learning`, `COMP3003 Cybersecurity`, `MATH2005 Applied Statistics`).
  - Color-coded badges, term, credits, and active deliverables count.
- **Deadlines Urgency Countdown**:
  - Coursework, deliverables, and exams with calculated countdowns:
    - **Urgent** (`< 48h` / Due Today / Due Tomorrow) with bright alert badge.
    - **Soon** (`< 7d`) with priority tags.
    - **Upcoming** with due dates and percentage grade weightings.
    - **Completed** toggle with grade badge and resource link (e.g. Moodle).
- **Study Task Checklist**:
  - Interactive todo list tied to specific modules and priorities (High, Medium, Low).

### 3. People Network CRM (`/people`)
- Searchable, filterable directory with tag filters.
- Contact cards with touch count, last seen date, and key facts.
- Interactive profile slide-over with editable notes/tags and reverse chronological interaction timeline.

### 4. Conversational AI Assistant (`/chat`)
- Unified multi-domain executive assistant with structured retrieval tools:
  - `query_journal(start_date, end_date, keyword)`
  - `get_person_dossier(person_name)`
  - `get_garmin_metrics(date)`
  - `get_upcoming_deadlines(days_ahead)`
  - `get_academic_tasks(status, module_code)`
  - `get_nutrition_summary(date)`
- SSE streaming response with word chunks.
- Expandable **Source Citations / Evidence Pills** showing which records informed the answer.

---

## Tech Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy (SQLite zero-config), Pydantic v2, APScheduler, HTTPX, `garminconnect`.
- **Frontend**: React 18, Vite, Tailwind CSS, Lucide Icons.
- **Database**: SQLite (`command_centre.db`).
- **Containerization**: Docker & Docker Compose.

---

## Project Structure

```
command-centre/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, lifespan startup
│   │   ├── config.py            # Pydantic Settings
│   │   ├── database.py          # SQLite engine & session factory
│   │   ├── models/              # SQLAlchemy ORM models
│   │   │   ├── daily_metrics.py # DailyMetrics table
│   │   │   ├── journal.py       # JournalEntry table
│   │   │   ├── nutrition.py     # NutritionLog table
│   │   │   ├── crm.py           # Person & Interaction tables
│   │   │   └── university.py    # Module, Deadline, AcademicTask tables
│   │   ├── schemas/             # Pydantic validation schemas
│   │   │   ├── metrics.py
│   │   │   ├── journal.py
│   │   │   ├── crm.py
│   │   │   └── university.py
│   │   ├── services/            # Core business logic
│   │   │   ├── garmin_service.py# Ingestion & token caching
│   │   │   ├── llm_service.py   # Gemini / OpenAI / Heuristic NLP
│   │   │   ├── crm_service.py   # People resolution & facts graph
│   │   │   ├── scheduler_service.py # APScheduler daily sync
│   │   │   ├── agent_tools.py   # AI Agent database retrieval tools
│   │   │   └── chat_service.py  # Conversational streaming & citations
│   │   └── routes/              # REST API routers
│   │       ├── metrics.py       # /api/metrics, /api/garmin/sync
│   │       ├── journal.py       # /api/journal, /api/journal/nutrition
│   │       ├── crm.py           # /api/people, /api/interactions
│   │       ├── university.py    # /api/modules, /api/deadlines, /api/tasks
│   │       ├── chat.py          # /api/chat, /api/chat/stream
│   │       └── seed.py          # /api/seed (Life + Uni demo seeder)
│   ├── tests/                   # 17 comprehensive pytest unit & integration tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/client.js        # API client for Life, Uni, and Chat
│   │   ├── components/
│   │   │   ├── Sidebar.jsx              # Multi-workspace switcher & navigation
│   │   │   ├── UniversityDashboard.jsx  # Academic modules, deadlines & tasks
│   │   │   ├── ChatAssistant.jsx        # Streaming chat & source citation pills
│   │   │   ├── DateNavigator.jsx        # Day switcher & calendar picker
│   │   │   ├── SummaryCards.jsx         # Steps ring, Energy balance, Sleep, Mood
│   │   │   ├── JournalEditor.jsx        # Free-form input & live AI extraction
│   │   │   ├── ExtractedIntelligence.jsx# Nutrition macro bars & social pills
│   │   │   ├── DailyTimeline.jsx        # Unified Garmin workouts, meals, meetings
│   │   │   ├── PeopleDirectory.jsx      # Searchable CRM directory & tag filters
│   │   │   ├── PersonModal.jsx          # Profile inspector & interaction timeline
│   │   │   └── SettingsModal.jsx        # Garmin/LLM config & Demo Seeder
│   │   ├── utils/dateUtils.js
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.frontend
├── run.bat                      # Windows 1-click launcher
├── run.sh                       # Linux/macOS launcher
├── .env.example
└── README.md
```

---

## Quick Start (Local Development)

### 1. Backend Setup

```bash
cd backend

# Create & activate virtual environment
python -m venv venv
.\venv\Scripts\activate   # Windows
# source venv/bin/activate # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Run test suite
pytest

# Start server
uvicorn app.main:app --reload --port 8000
```

The backend is live at `http://localhost:8000` with interactive API docs at `http://localhost:8000/docs`.

### 2. Frontend Setup

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

### 3. Windows 1-Click Launch

Simply double-click `run.bat` or run:

```cmd
.\run.bat
```

---

## Docker Compose Setup

Run the full stack in Docker containers:

```bash
docker compose up --build
```

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
