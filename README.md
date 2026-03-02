# سند AI — Sanad AI Legal Assistant

مستشار قانوني ذكي متخصص في الأنظمة السعودية

## Architecture

- **Backend**: FastAPI + Python 3.11 + Claude AI (Anthropic)
- **Frontend**: Next.js 14 + React 18 + TypeScript + Tailwind CSS
- **Database**: Supabase (PostgreSQL) with Row Level Security
- **Vector DB**: ChromaDB with multilingual embeddings
- **Payments**: Moyasar + PayPal
- **Deployment**: Render (backend) + Vercel (frontend)

## Legal Systems Covered

1. نظام الأحوال الشخصية (Personal Status Law)
2. نظام الإثبات (Evidence Law) + Electronic Evidence Procedures
3. نظام المرافعات الشرعية (Sharia Procedures Law)
4. نظام المعاملات المدنية (Civil Transactions Law)
5. نظام المحاكم التجارية (Commercial Courts Law)

## Features

- AI-powered legal consultation (streaming)
- Contract analysis (PDF/DOCX)
- Verdict prediction (real judicial patterns)
- Legal document drafting
- Deadline calculator
- Articles browser
- 4-tier subscription system

## Development

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Tests
```bash
pytest backend/tests/ -v
```

## Environment Variables

See `.env.example` for required environment variables.

## License

Proprietary — All rights reserved.
