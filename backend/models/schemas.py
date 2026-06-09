from pydantic import BaseModel
from typing import Optional


class InvoiceItem(BaseModel):
    rowNum: str
    description: str
    quantity: str
    unitPrice: str
    amount: str


class InvoiceDetail(BaseModel):
    invNum: str
    invDate: str
    sellerName: str
    amount: str
    sellerBan: Optional[str] = ""
    invoiceTime: Optional[str] = ""
    details: list[InvoiceItem]


class InvoiceHeader(BaseModel):
    invNum: str
    sellerName: str
    amount: str
    invDate: str
    invPeriod: str
    sellerBan: str
    invoiceTime: str


class ClassifiedExpense(BaseModel):
    category: str
    description: str
    amount: str
    sellerName: str
    invDate: str
    invoiceTime: str


class QuestionnaireAnswer(BaseModel):
    question: str
    answer: str


class UserSession(BaseModel):
    phone_barcode: str
    card_encrypt: str


class HappinessReport(BaseModel):
    summary: str
    happy_top3: list[str]
    stress_top3: list[str]
    suggestions: list[str]
