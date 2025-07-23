from pydantic import BaseModel
from typing import Dict
from datetime import date

class StatsSummary(BaseModel):
    """Overall statistics summary"""
    total_deeds: int
    total_cooperatives: int
    status_distribution: Dict[str, int]
    average_borrowers_per_deed: float

class StatusDurationStats(BaseModel):
    """Statistics about time spent in each status"""
    status: str
    average_duration_hours: float
    min_duration_hours: float
    max_duration_hours: float

class TimelineStats(BaseModel):
    """Daily statistics for deeds"""
    date: date
    new_deeds: int
    completed_deeds: int 