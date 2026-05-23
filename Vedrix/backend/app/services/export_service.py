"""Export service for CSV and analytics data export."""
import csv
import io
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ExportService:
    """Handles exporting interview data to CSV format."""

    def interviews_to_csv(self, interviews: List[Dict[str, Any]]) -> str:
        """Convert a list of interview records to CSV format.
        
        Args:
            interviews: List of interview dicts with fields like
                candidate_email, job_role, overall_score, ai_feedback, etc.
        
        Returns:
            CSV string with headers and data rows.
        """
        output = io.StringIO()
        fieldnames = [
            "session_id", "candidate_email", "candidate_name", "job_role",
            "drive_title", "overall_score", "technical_accuracy",
            "communication_clarity", "depth_of_knowledge",
            "hire_recommendation", "skills_covered", "date", "status", "duration_minutes"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        for interview in interviews:
            ai_feedback = interview.get("ai_feedback") or {}
            if isinstance(ai_feedback, str):
                try:
                    import json
                    ai_feedback = json.loads(ai_feedback)
                except (json.JSONDecodeError, TypeError):
                    ai_feedback = {}

            skill_matrix = interview.get("skill_matrix") or {}
            if isinstance(skill_matrix, str):
                try:
                    import json
                    skill_matrix = json.loads(skill_matrix)
                except (json.JSONDecodeError, TypeError):
                    skill_matrix = {}

            skills_covered = ",".join(skill_matrix.keys()) if isinstance(skill_matrix, dict) else ""

            duration_secs = interview.get("duration") or 0
            duration_minutes = round(duration_secs / 60, 1) if duration_secs else 0

            created_at = interview.get("created_at")
            if isinstance(created_at, datetime):
                date_str = created_at.strftime("%Y-%m-%d")
            elif isinstance(created_at, str):
                date_str = created_at[:10]
            else:
                date_str = ""

            row = {
                "session_id": interview.get("id", ""),
                "candidate_email": interview.get("candidate_email", ""),
                "candidate_name": interview.get("candidate_name", ""),
                "job_role": interview.get("job_role", ""),
                "drive_title": interview.get("drive_title", ""),
                "overall_score": interview.get("overall_score") or "",
                "technical_accuracy": ai_feedback.get("technical_accuracy", ""),
                "communication_clarity": ai_feedback.get("communication_clarity", ""),
                "depth_of_knowledge": ai_feedback.get("depth_of_knowledge", ""),
                "hire_recommendation": ai_feedback.get("hire_recommendation", ""),
                "skills_covered": skills_covered,
                "date": date_str,
                "status": interview.get("status", ""),
                "duration_minutes": duration_minutes,
            }
            writer.writerow(row)

        return output.getvalue()

    def team_analytics_to_csv(self, analytics: Dict[str, Any]) -> str:
        """Convert team analytics data to CSV format.
        
        Args:
            analytics: Dict with team analytics data including
                summary, score_distribution, role_breakdown, etc.
        
        Returns:
            CSV string with analytics summary.
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # Summary section
        writer.writerow(["Vedrix AI Interview — Team Analytics Report"])
        writer.writerow([f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}"])
        writer.writerow([])

        summary = analytics.get("summary", {})
        writer.writerow(["Summary Metrics"])
        writer.writerow(["Metric", "Value"])
        for key, value in summary.items():
            label = key.replace("_", " ").title()
            writer.writerow([label, value])
        writer.writerow([])

        # Role breakdown
        role_breakdown = analytics.get("role_breakdown", [])
        if role_breakdown:
            writer.writerow(["Role Breakdown"])
            writer.writerow(["Job Role", "Total Interviews", "Completed", "Avg Score", "Pass Rate"])
            for role in role_breakdown:
                writer.writerow([
                    role.get("job_role", ""),
                    role.get("total", 0),
                    role.get("completed", 0),
                    role.get("avg_score", 0),
                    role.get("pass_rate", 0),
                ])
            writer.writerow([])

        # Funnel
        funnel = analytics.get("funnel", {})
        if funnel:
            writer.writerow(["Hiring Funnel"])
            writer.writerow(["Stage", "Count"])
            for stage, count in funnel.items():
                writer.writerow([stage.replace("_", " ").title(), count])

        return output.getvalue()


export_service = ExportService()
