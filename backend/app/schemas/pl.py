# backend/app/schemas/pl.py
from __future__ import annotations
from datetime import date
from pydantic import BaseModel


class PLResponse(BaseModel):
	start: date
	end: date
	revenue: float
	costOfGoods: float
	wastageCost: float
	grossMargin: float
