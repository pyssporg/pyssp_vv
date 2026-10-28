"""Durable, hash-addressed evidence bundles."""

from pyssp_vv.evidence.bundle import EvidenceBundle, InputRef, VerdictRecord
from pyssp_vv.evidence.metrics import (
    METRIC_COLUMNS,
    ComparisonSummary,
    MetricRow,
    MetricRowView,
    as_metric_view,
    read_metric_csv,
    summarize_rows,
    write_metric_csv,
)

__all__ = [
    "METRIC_COLUMNS",
    "ComparisonSummary",
    "EvidenceBundle",
    "InputRef",
    "MetricRow",
    "MetricRowView",
    "VerdictRecord",
    "as_metric_view",
    "read_metric_csv",
    "summarize_rows",
    "write_metric_csv",
]
