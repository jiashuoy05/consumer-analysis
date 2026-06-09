# AGENTS.md — AI 消費幸福感分析師

## Commands

```bash
# Backend (run from repo root)
pip install -r backend/requirements.txt
playwright install chromium
python backend/main.py                                    # uvicorn on port 8000

# Frontend (run from frontend/)
npm install
npm run dev                                                # Vite dev server on port 5173, proxies /api → :8000
npm run build                                              # production build
npm run lint                                               # ESLint
```

## Repo structure

```
consumer-analysis/
├── backend/                   # FastAPI + LangChain/LangGraph + Playwright
│   ├── main.py                # Entrypoint; inserts parent dir into sys.path
│   ├── .env                   # Env vars, in .gitignore
│   ├── .env.example           # Template with placeholder values
│   ├── requirements.txt
│   ├── models/schemas.py      # Pydantic models
│   ├── services/
│   │   ├── llm_service.py     # LangGraph flow: classify → questions → report; Tavily search
│   │   ├── scraper.py         # Playwright login + scrapes month by month
│   │   ├── report_generator.py  # Markdown 報告格式化 + SMTP email 寄送
│   └── api/
│       ├── routes.py          # POST /session/start, /session/answer, /report/send, etc.
│       └── scraper_routes.py  # POST /scraper/login-and-scrape, /scraper/refresh, /scraper/me
└── frontend/                  # React 19 + Vite + Tailwind CSS v4 (TypeScript)
    ├── src/
    │   ├── main.jsx           # React entry
    │   ├── App.tsx            # 4-page flow: login → invoices → survey → report
    │   ├── pages/
    │   │   ├── LoginPage.tsx  # phone+password → /scraper/login-and-scrape
    │   │   ├── InvoicesPage.tsx  # date-filtered invoice table + start survey
    │   │   ├── SurveyPage.tsx # LLM-generated questions (text/single_choice/multiple_choice/rating/ranking/likert)
    │   │   └── ReportPage.tsx # report display + email send
    │   ├── context/AppContext.ts  # all shared state (token, items, report, etc.)
    │   ├── components/ErrorBanner.tsx
    │   └── utils/
    │       ├── db.ts           # IndexedDB wrapper (get/set/delete/clear)
    │       └── downloadBlob.ts
    ├── vite.config.ts         # Proxies /api → http://127.0.0.1:8000
    └── package.json
```

## Key gotchas

- **`.env` is loaded in `llm_service.py`.** Calls `load_dotenv(Path(__file__).parent.parent / ".env")` at module level. Env vars available regardless of CWD.
- **Gemini API key required.** No mock data. Falls back to "其他" if no key.
- **In-memory session state.** `routes.py` and `scraper_routes.py` store sessions in a plain `dict` — lost on server restart.
- **Scraper loops months individually.** For each month: open datepicker → navigate to target month → select first/last day → Escape → set page size 100 → 查詢 → download CSV pages → navigate back to search page.
- **All clicks via `page.evaluate('el => el.click()', el)`.** Avoids Playwright actionability checks (disabled/enabled issues).
- **CAPTCHA uses alpha channel.** Extract with `np.array` → `[:,:,3]` → `Image.fromarray(arr[:,:,3], mode="L")` → ddddocr.
- **Vue Datepicker readonly.** Arrow buttons `button.dp--arrow-btn-nav`, date IDs `[id="YYYY-MM-DD"]`. Navigate from today: `(today.year - target_y) * 12 + (today.month - target_m)` left arrow clicks.
- **CSV columns use `消費明細_` prefix.** Set `#SelectSizes` to 100 before search.
- **Items stored in IndexedDB.** Cleared only on logout or refresh_token expiry.
- **Tailwind v4.** Uses `@import "tailwindcss"` in CSS and `@tailwindcss/vite` plugin.
- **`Authorization: Bearer` header.** `ACCESS_TTL = 1800s`, `REFRESH_TTL = 86400s`.
- **GEMINI_MODEL** in `.env` set to `gemini-2.5-flash`.
- **Structured questions.** LLM generates JSON with `id`, `text`, `type` (text/single_choice/multiple_choice/rating/ranking/likert), and `options`. Frontend renders per type. Answers use `question_id` key.
- **No DOCX/PDF/charts.** Report is formatted as Markdown and sent via email body only.
- **Frontend proxies `/api` to backend.** `vite.config.ts` proxies `/api` → `http://127.0.0.1:8000`.
