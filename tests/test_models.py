"""领域模型：字段校验（confidence 边界等）与基本可用性。"""
import pytest
from pydantic import ValidationError

from app.models import AnalysisReport, QueryPlan, QueryStep


def test_report_confidence_bounds():
    with pytest.raises(ValidationError):
        AnalysisReport(answer="x", key_findings=[], evidence="", confidence=1.5)
    r = AnalysisReport(answer="x", key_findings=[], evidence="", confidence=0.97)
    assert r.confidence == 0.97


def test_query_plan_roundtrip():
    step = QueryStep(step=1, purpose="p", sql="SELECT 1")
    plan = QueryPlan(steps=[step])
    assert plan.steps[0].sql == "SELECT 1"
