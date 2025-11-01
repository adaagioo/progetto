# backend/app/core/config.py
from __future__ import annotations

import os
from typing import List, Optional
from pydantic import AnyUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _csv(value: str | None, default: list[str] | None = None) -> list[str]:
	if value is None or value.strip() == "":
		return default or []
	return [v.strip() for v in value.split(",") if v.strip()]


class Settings(BaseSettings):
	model_config = SettingsConfigDict(
		env_file=".env",
		env_file_encoding="utf-8",
		extra="ignore",
	)

	# App
	APP_NAME: str = "RistoBrain API"
	ENV: str = Field(default="development", description="development|staging|production")
	DEBUG: bool = False
	LOG_LEVEL: str = "INFO"

	# CORS
	ALLOW_ORIGINS: List[str] = Field(default_factory=lambda: ["http://localhost:3000"])
	ALLOW_METHODS: List[str] = Field(default_factory=lambda: ["*"])
	ALLOW_HEADERS: List[str] = Field(default_factory=lambda: ["*"])

	# Frontend URL (per link in email, ecc.)
	APP_URL: str = "http://localhost:3000"

	# Database (Mongo)
	MONGO_URI: str = "mongodb://localhost:27017/ristobrain"
	MONGO_DB_NAME: str = "ristobrain"

	# Auth / JWT
	JWT_SECRET: str = os.getenv("JWT_SECRET")
	ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
	REFRESH_TOKEN_EXPIRE_DAYS: int = 30

	# Email
	SMTP_HOST: str = ""
	SMTP_PORT: int = 587
	SMTP_USER: str = ""
	SMTP_PASS: str = ""
	MAIL_FROM: str = "RistoBrain <no-reply@ristobrain.app>"

	# Storage
	STORAGE_DRIVER: str = "local"  # local|s3
	STORAGE_LOCAL_PATH: str = "/data/storage"
	S3_ENDPOINT_URL: Optional[AnyUrl] = None
	S3_REGION: Optional[str] = None
	S3_ACCESS_KEY: Optional[str] = None
	S3_SECRET_KEY: Optional[str] = None
	S3_BUCKET: Optional[str] = None

	# Locale / Currency
	DEFAULT_CURRENCY: str = "EUR"
	DEFAULT_LOCALE: str = "it-IT"
	SUPPORTED_CURRENCIES: List[str] = Field(default_factory=lambda: ["EUR", "USD"])
	SUPPORTED_LOCALES: List[str] = Field(default_factory=lambda: ["en-US", "it-IT"])

	@classmethod
	def from_env(cls) -> "Settings":
		s = cls()
		import os
		s.ALLOW_ORIGINS = _csv(os.getenv("ALLOW_ORIGINS"), s.ALLOW_ORIGINS)
		s.SUPPORTED_CURRENCIES = _csv(os.getenv("SUPPORTED_CURRENCIES"), s.SUPPORTED_CURRENCIES)
		s.SUPPORTED_LOCALES = _csv(os.getenv("SUPPORTED_LOCALES"), s.SUPPORTED_LOCALES)
		return s


settings = Settings.from_env()
