# 🏠 LensEstate — AI Solution for Tunisian Real Estate Market Analysis

## Overview

TuniEstate is an AI-powered platform designed to address the lack of transparency and reliable data in the Tunisian real estate market. By combining autonomous data ingestion agents, machine learning models, and a generative AI assistant, TuniEstate centralizes fragmented property listings, estimates fair market prices, and delivers actionable insights to buyers, sellers, investors, and agencies — all through an intuitive, accessible interface.

---

## Features

- 🤖 **Automated Data Ingestion** — AI agents autonomously collect, clean, deduplicate, and normalize real estate data from multiple sources (online platforms, social media, informal listings)
- 💰 **AI-Powered Price Estimation** — ML models benchmark property prices based on characteristics, location, and market dynamics to detect overpriced or undervalued listings
- 📈 **Market Trend Forecasting** — Time-series and predictive models track price evolution, detect seasonality, and anticipate market shifts
- 💬 **Conversational AI Assistant** — A GenAI chatbot that answers user queries, generates analytical reports, and provides personalized recommendations in natural language
- 🗺️ **Regional Market Analysis** — Comparative insights across Tunisian governorates, cities, and neighborhoods to highlight spatial disparities
- 🌍 **Multi-currency Support** — Standardized price normalization across different currency formats

---

## Tech Stack

### Frontend

| Technology | Purpose |
|---|---|
| `<!-- e.g. React / Next.js -->` | UI Framework |


### Backend

| Technology | Purpose |
|---|---|
| `<!-- e.g. Python -->` | AI/ML Processing |


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

> 🎓 This project was developed as part of a Data Science academic program at **Esprit School of Engineering**, during the academic year `<!-- e.g. 2025–2026 -->`.

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

- `<!-- e.g. Python >= 3.10 -->`

### Installation

```bash
# Clone the repository
git clone https://github.com/InesBenDhifallah/-Esprit-PIDS-4DS6--2026-LensEstate
.git
cd -Esprit-PIDS-4DS6--2026-LensEstate

# Install backend dependencies
cd backend && pip install -r requirements.txt

# Install frontend dependencies
cd ../frontend && npm install
```

### Running the App

```bash
# Start the backend
cd backend && python app.py

# Start the frontend
cd frontend && npm start
```

### Environment Variables

Create a `.env` file in the `backend/` directory:

```env
DATABASE_URL=your_database_url
API_KEY=your_api_key
GENAI_API_KEY=your_genai_key
```

---

## Acknowledgments

- Tunisian real estate data sources and online listing platforms
- Open-source ML and NLP libraries powering the analytical engine


---

> Built with ❤️ by the TuniEstate team — making the Tunisian real estate market transparent, fair, and accessible for all.
