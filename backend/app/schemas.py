from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, EmailStr, Field, StringConstraints

TxType = Literal["income", "expense"]

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
Money = Annotated[float, Field(gt=0, le=1_000_000_000), AfterValidator(lambda v: round(v, 2))]


# ---------- Users / auth ----------

class UserCreate(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Categories ----------

class CategoryIn(BaseModel):
    name: Name
    type: TxType


class CategoryOut(BaseModel):
    id: str
    name: str
    type: TxType


# ---------- Transactions ----------

class TransactionIn(BaseModel):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    amount: Money
    type: TxType
    category: Name
    description: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] = ""
    date: date


class TransactionOut(BaseModel):
    id: str
    title: str
    amount: float
    type: TxType
    category: str
    description: str
    date: date


class TransactionPage(BaseModel):
    items: list[TransactionOut]
    total: int
    page: int
    page_size: int


# ---------- Budgets ----------

class BudgetIn(BaseModel):
    category: Name
    monthly_limit: Money
    month: int = Field(ge=1, le=12)
    year: int = Field(ge=2000, le=2100)


class BudgetOut(BaseModel):
    id: str
    category: str
    monthly_limit: float
    month: int
    year: int
    spent: float
    remaining: float
    percent_used: float


# ---------- Analytics ----------

class CategoryTotal(BaseModel):
    category: str
    total: float


class MonthlySummary(BaseModel):
    month: int
    year: int
    income: float
    expense: float
    savings: float  # income - expense for the month
    savings_rate: float | None  # savings as % of income; None when there is no income
    total_balance: float  # all income minus all expenses up to the end of the month
    expense_by_category: list[CategoryTotal]
    income_by_category: list[CategoryTotal]
    recent_transactions: list[TransactionOut]


class Breakdown(BaseModel):
    year: int
    month: int | None  # None = the whole year
    income: float
    expense: float
    expense_by_category: list[CategoryTotal]
    income_by_category: list[CategoryTotal]


class CategoryChange(BaseModel):
    category: str
    current: float
    previous: float
    change: float
    change_pct: float | None  # None when previous is 0


class MonthComparison(BaseModel):
    month: int
    year: int
    previous_month: int
    previous_year: int
    current_total: float
    previous_total: float
    categories: list[CategoryChange]


class TrendPoint(BaseModel):
    month: int
    income: float
    expense: float


class YearTrend(BaseModel):
    year: int
    points: list[TrendPoint]
