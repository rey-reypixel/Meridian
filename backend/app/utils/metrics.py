from typing import Dict, Any
from datetime import datetime


class Metrics:
    """In-memory metrics tracking"""

    def __init__(self):
        self.counters: Dict[str, int] = {}
        self.gauges: Dict[str, float] = {}
        self.totals: Dict[str, float] = {}
        self.timestamps: Dict[str, datetime] = {}

    def increment_counter(self, name: str, value: int = 1, labels: Dict[str, str] = None) -> None:
        """Increment a counter"""
        key = self._make_key(name, labels)
        self.counters[key] = self.counters.get(key, 0) + value

    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None) -> None:
        """Set a gauge value"""
        key = self._make_key(name, labels)
        self.gauges[key] = value

    def add_total(self, name: str, value: float, labels: Dict[str, str] = None) -> None:
        """Add to a total"""
        key = self._make_key(name, labels)
        self.totals[key] = self.totals.get(key, 0.0) + value

    def _make_key(self, name: str, labels: Dict[str, str] = None) -> str:
        """Create metric key from name and labels"""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics"""
        return {
            "counters": self.counters,
            "gauges": self.gauges,
            "totals": self.totals
        }

    def get_summary(self) -> Dict[str, Any]:
        """Get summary metrics"""
        total_requests = self.counters.get("requests_total", 0)
        total_cost = self.totals.get("cost_usd_total", 0.0)
        total_savings = self.totals.get("savings_usd_total", 0.0)
        avg_quality = self.gauges.get("quality_score_avg", 0.0)

        return {
            "total_requests": total_requests,
            "total_cost": round(total_cost, 2),
            "total_savings": round(total_savings, 2),
            "avg_quality_score": round(avg_quality, 2),
            "savings_percentage": round((total_savings / total_cost * 100) if total_cost > 0 else 0, 2)
        }

    def clear(self) -> None:
        """Clear all metrics"""
        self.counters.clear()
        self.gauges.clear()
        self.totals.clear()
        self.timestamps.clear()


# Global instance
metrics = Metrics()
