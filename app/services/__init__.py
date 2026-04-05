"""Пакет services — бизнес-логика (оркестрация pipeline + DB)."""

from app.services.training import TrainingService
from app.services.scoring import ScoringService

__all__ = ['TrainingService', 'ScoringService']
