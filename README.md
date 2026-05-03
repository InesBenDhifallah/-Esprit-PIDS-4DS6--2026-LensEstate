# 🏠 LensEstate — AI Solution for Tunisian Real Estate Market Analysis

## Overview

TuniEstate is an AI-powered platform designed to address the lack of transparency and reliable data in the Tunisian real estate market. By combining autonomous data ingestion agents, machine learning models, and a generative AI assistant, TuniEstate centralizes fragmented property listings, estimates fair market prices, and delivers actionable insights to buyers, sellers, investors, and agencies — all through an intuitive, accessible interface.

---

## Features

- 🤖 **AI Data Collection Agents** — AI agents autonomously collect, clean, deduplicate, and normalize real estate data from multiple sources (online platforms, social media, informal listings)
- 💰 **Multi-Modal Valuation Models** — ML models combining property features, location, and market data to ensure fair and objective pricing
- 📈 **Regional Trend Prediction** — Time-series models to anticipate price shifts and market evolution across Tunisian regions
- 💬 **Conversational GenAI Assistant** — Natural language chatbot that simplifies market access and delivers personalized insights on demand
- 🏗️ **2D Property Reconstruction** — Visual reconstruction of property layouts to improve how properties are presented and understood
---

## Tech Stack
### Frontend
| Technology | Purpose |
|---|---|
| `React + TypeScript` | UI Framework |
| `Vite` | Build Tool |
| `TanStack Router` | Routing |
| `Tailwind CSS` | Styling |
| `Framer Motion` | Animations |
| `Bun` | Package Manager |

### Backend
| Technology | Purpose |
|---|---|
| `Django + DRF` | REST API Framework |
| `PostgreSQL` | Database |
| `ChromaDB` | Vector Database (RAG) |
| `Sentence Transformers` | Embeddings |
| `LLaMA 3.1 70B` | AI Language Model |
| `OpenAI SDK` | LLM API Client |
| `JWT` | Authentication |
| `ReportLab` | PDF Generation |
---

## Architecture

```
tuniEstate/
├── frontend/                  # Client-side application
│   ├── components/
│   ├── pages/
│   └── ...
├── backend/                   # Server-side application
│   ├── agents/                # Autonomous data ingestion agents
│   ├── models/                # ML price estimation & forecasting
│   ├── genai/                 # Conversational AI assistant
│   ├── api/                   # REST API routes & controllers
│   └── ...
├── data/                      # Raw & processed datasets
└── README.md
```

---

## Contributors

| Name | Role |
|---|---|
| **Ben Dhifallah Ines** | Project Manager |
| **Mohamed Khalil Kamessi** | Solution Architect |
| **Mohamed Ali Jabri** | Data Scientist |
| **Najeh Ben Rebah** | Project Lead |
| **Feryel Ifaoui** | Data Scientist |

---

## Academic Context

> 🎓 This project was developed as part of a Data Science academic program at **Esprit School of Engineering**, during the academic year ` 2025–2026`.

**Supervisor:** `Mme Wiem Trabelsi & Mr Bilel Farah`

This project aligns with the following **UN Sustainable Development Goals**:

| SDG | Relevance |
|---|---|
| 🎓 **SDG 4** — Quality Education | Transforms complex market data into accessible insights |
| 💼 **SDG 8** — Decent Work & Economic Growth | Supports informed real estate decision-making |
| 🏭 **SDG 9** — Industry, Innovation & Infrastructure | Applies AI/ML to structure Tunisian real estate data |
| 🏙️ **SDG 11** — Sustainable Cities & Communities | Supports urban development analysis across regions |

---

## Getting Started

### Prerequisites
- `Python >= 3.11`
- `Node.js >= 18`
- `Bun >= 1.3`
- `PostgreSQL >= 18`

### Installation
```bash
# Clone the repository
git clone https://github.com/InesBenDhifallah/-Esprit-PIDS-4DS6--2026-LensEstate.git
cd -Esprit-PIDS-4DS6--2026-LensEstate

# Create and activate virtual environment
python -m venv venv
venv\Scripts\Activate.ps1  # Windows

# Install backend dependencies
cd backend && pip install -r requirements.txt

# Install frontend dependencies
cd ../frontend && bun install
```

### Running the App
```bash
# Start the backend
cd backend && python manage.py runserver

# Start the frontend (in a separate terminal)
cd frontend && bun run dev
```

### Environment Variables
Create a `.env` file in the `backend/` directory:
```env
SECRET_KEY=your_secret_key
DEBUG=True
DB_NAME=LensEstate
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432
EMAIL_HOST_USER=your_email
EMAIL_HOST_PASSWORD=your_email_password
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
```

Create a `.env.local` file in the root directory:
```env
API_KEY=your_api_key
VITE_API_URL=http://localhost:8000
VITE_GOOGLE_CLIENT_ID=your_google_client_id
```

## Acknowledgments

- Tunisian real estate data sources and online listing platforms
- Open-source ML and NLP libraries powering the analytical engine


---

> Built with ❤️ by the LensEstate team — making the Tunisian real estate market transparent, fair, and accessible for all.
