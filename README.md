# AI 消費幸福感分析師

以電子發票數據 + LLM 問卷對話，打造個人財務健康報告。

## 流程

```
登入（手機條碼 + 密碼）
  ↓
Playwright 自動登入財政部 + 逐月下載 CSV（近三個月）
  ↓
LLM 分類品名（食/衣/住/行/育/樂）
  ↓
LLM 動態生成個人化問卷
  ↓
使用者填寫問卷
  ↓
LLM 生成「消費幸福感報告」（幸福 Top3 / 壓力 Top3 / 建議）
  ↓
下載 DOCX / PDF，或 Email 寄送
```

## 技術架構

| 組件 | 技術 |
|------|------|
| API 框架 | FastAPI |
| LLM 框架 | LangChain + LangGraph |
| LLM 模型 | Gemini 2.5 Flash |
| 發票爬蟲 | Playwright + stealth + ddddocr |
| 報告產生 | matplotlib + python-docx + fpdf2 |
| 郵件寄送 | SMTP (Gmail) |
| 前端 | React 19 + Vite + Tailwind CSS v4 (TypeScript) |
| 資料儲存 | IndexedDB（發票明細）、localStorage（token） |

## 專案結構

```
consumer-analysis/
├── backend/
│   ├── main.py                    # FastAPI 入口
│   ├── .env.example               # 環境變數範本
│   ├── requirements.txt
│   ├── models/schemas.py          # Pydantic 資料模型
│   ├── services/
│   │   ├── llm_service.py         # LangGraph 流程
│   │   ├── scraper.py             # Playwright 爬蟲
│   │   ├── report_generator.py    # 圖表 + DOCX/PDF + Email
│   └── api/
│       ├── routes.py              # 幸福感 API
│       └── scraper_routes.py      # 爬蟲 + Token API
└── frontend/
    ├── src/
    │   ├── App.tsx                # 路由：登入→發票→問卷→報告
    │   ├── pages/
    │   │   ├── LoginPage.tsx      # 手機+密碼，一鍵登入爬取
    │   │   ├── InvoicesPage.tsx   # 發票明細表 + 日期篩選
    │   │   ├── SurveyPage.tsx     # LLM 問卷填寫
    │   │   └── ReportPage.tsx     # 報告顯示 + 下載 + 寄送
    │   ├── context/AppContext.ts   # 全域狀態
    │   ├── components/
    │   │   └── ErrorBanner.tsx
    │   └── utils/
    │       ├── db.ts              # IndexedDB 操作
    │       └── downloadBlob.ts
    ├── vite.config.ts
    └── package.json
```

## 快速開始

### 安裝

```bash
pip install -r backend/requirements.txt
playwright install chromium
cd frontend && npm install
```

### 設定環境變數

```bash
cp backend/.env.example backend/.env
```

編輯 `backend/.env`：

```env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_password
```

### 啟動

```bash
# 後端（專案根目錄）
python backend/main.py

# 前端（frontend/ 目錄）
npm run dev
```

開啟 `http://localhost:5173` 即可使用。

## API

伺服器啟動後瀏覽 `http://localhost:8000/docs` 查看 Swagger UI。

### 爬蟲

| 方法 | 路徑 | 說明 |
|------|------|------|
| POST | `/api/v1/scraper/login-and-scrape` | 登入 + 爬取發票（預設三個月） |
| POST | `/api/v1/scraper/login` | 僅驗證帳密 |
| POST | `/api/v1/scraper/refresh` | 換發 access_token |
| POST | `/api/v1/scraper/me` | 查詢使用者資訊 |

### 幸福感分析

| 方法 | 路徑 | 說明 |
|------|------|------|
| POST | `/api/v1/session/start` | 啟動 LLM 分類 + 生成問卷 |
| POST | `/api/v1/session/answer` | 提交回答，生成報告 |
| POST | `/api/v1/report/send` | 產生 DOCX/PDF 並 Email 寄送 |
| GET  | `/api/v1/report/download/{id}/{fmt}` | 下載 DOCX 或 PDF |

## 授權

MIT
