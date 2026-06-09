import { createContext } from "react";

export type QuestionType = "text" | "single_choice" | "multiple_choice" | "rating" | "ranking" | "likert";

export interface Question {
  id: string;
  text: string;
  type: QuestionType;
  options: string[];
  required: boolean;
}

export interface InvoiceItem {
  invNum: string;
  invDate: string;
  description: string;
  amount: string;
  sellerName: string;
  quantity?: string;
  unitPrice?: string;
}

export interface ReportType {
  summary: string;
  happy_top3: string[];
  stress_top3: string[];
  suggestions: string[];
}

export type AnswerValue = string | string[] | number;

export interface AppContextType {
  accessToken: string;
  setAccessToken: (v: string) => void;
  refreshToken: string;
  setRefreshToken: (v: string) => void;
  phone: string;
  setPhone: (v: string) => void;
  password: string;
  setPassword: (v: string) => void;
  loading: boolean;
  setLoading: (v: boolean) => void;
  startYear: string;
  setStartYear: (v: string) => void;
  startMonth: string;
  setStartMonth: (v: string) => void;
  endYear: string;
  setEndYear: (v: string) => void;
  endMonth: string;
  setEndMonth: (v: string) => void;
  year: string;
  setYear: (v: string) => void;
  month: string;
  setMonth: (v: string) => void;
  items: InvoiceItem[];
  setItems: (v: InvoiceItem[]) => void;
  carrierId: string;
  setCarrierId: (v: string) => void;
  email: string;
  setEmail: (v: string) => void;
  questions: Question[];
  setQuestions: (v: Question[]) => void;
  answers: Record<string, AnswerValue>;
  setAnswers: (v: Record<string, AnswerValue> | ((prev: Record<string, AnswerValue>) => Record<string, AnswerValue>)) => void;
  report: ReportType | null;
  setReport: (v: ReportType | null) => void;
  qsSessionId: string;
  setQsSessionId: (v: string) => void;
  error: string;
  setError: (v: string) => void;
  refreshAccessToken: () => Promise<{ access_token: string; refresh_token: string } | null>;
  logout: () => void;
}

export const AppContext = createContext<AppContextType | null>(null);
