# backend/app/utils/logger.py
"""
Centralized logging configuration for the application.
Provides structured logging with consistent format across all modules.
"""
from __future__ import annotations
import logging
import sys
from typing import Optional

# Configure logging format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_LEVEL = logging.INFO


def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
	"""
	Get a configured logger instance.

	Args:
		name: Logger name (usually __name__ of the calling module)
		level: Optional log level override (default: INFO)

	Returns:
		Configured logger instance
	"""
	logger = logging.getLogger(name)

	# Only configure if not already configured
	if not logger.handlers:
		logger.setLevel(level or LOG_LEVEL)

		# Console handler
		handler = logging.StreamHandler(sys.stdout)
		handler.setLevel(level or LOG_LEVEL)

		# Formatter
		formatter = logging.Formatter(LOG_FORMAT)
		handler.setFormatter(formatter)

		logger.addHandler(handler)

	return logger
