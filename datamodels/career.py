from typing import List, Set, Optional, Dict
from datetime import date
from enum import Enum
import calendar
from .base import SerializableModel


# Move all the Enum classes and career analysis related classes here
class FundingStage(str, Enum):
    """Enum for company funding stages."""

    SEED = "Seed"
    SERIES_A = "Series A"
    SERIES_B = "Series B"
    SERIES_C = "Series C"
    SERIES_D_PLUS = "Series D+"
    IPO = "IPO"
    UNKNOWN = "Unknown"


class CompanyTier(str, Enum):
    """Enum for company classification."""

    STARTUP = "Startup"
    GROWTH = "Growth"
    BIG_TECH = "Big Tech"
    ENTERPRISE = "Enterprise"


class UniversityTier(Enum):
    """Enum for university rankings."""

    TOP_5 = "Top 5"
    TOP_10 = "Top 10"
    TOP_20 = "Top 20"
    TOP_50 = "Top 50"
    OTHER = "Other"


class ExperienceStageMetrics(SerializableModel):
    """Model for experience at a particular company stage."""

    company_name: str
    funding_stage: FundingStage
    joined_at: date
    left_at: Optional[date]
    duration_months: int
    company_tier: CompanyTier


class TechStack(Enum):
    """Enum for different tech stacks."""

    BACKEND = "Backend"
    FRONTEND = "Frontend"
    FULLSTACK = "Full Stack"
    ML_AI = "ML/AI"
    INFRASTRUCTURE = "Infrastructure"
    DATA = "Data Engineering"
    MOBILE = "Mobile"
    SECURITY = "Security"


class TechStackPatterns:
    """Patterns for identifying different tech stacks from job descriptions."""

    BACKEND = {
        "python",
        "django",
        "flask",
        "fastapi",
        "java",
        "spring",
        "nodejs",
        "express",
        "php",
        "laravel",
        "ruby",
        "rails",
        "golang",
        "rust",
        "c#",
        ".net",
        "postgresql",
        "mysql",
        "mongodb",
        "redis",
        "rabbitmq",
        "kafka",
        "api",
        "microservices",
        "backend",
        "back-end",
        "back end",
        "server-side",
        "database",
    }

    FRONTEND = {
        "javascript",
        "typescript",
        "react",
        "vue",
        "angular",
        "svelte",
        "html",
        "css",
        "sass",
        "less",
        "webpack",
        "babel",
        "frontend",
        "front-end",
        "front end",
        "ui/ux",
        "responsive design",
        "web development",
        "spa",
        "pwa",
        "jsx",
        "dom",
    }

    ML_AI = {
        "machine learning",
        "deep learning",
        "artificial intelligence",
        "neural networks",
        "tensorflow",
        "pytorch",
        "keras",
        "scikit-learn",
        "nlp",
        "computer vision",
        "ml ops",
        "data science",
        "ai",
        "ml",
        "transformers",
        "llm",
        "large language models",
        "reinforcement learning",
        "opencv",
        "pandas",
        "numpy",
    }

    INFRASTRUCTURE = {
        "aws",
        "azure",
        "gcp",
        "docker",
        "kubernetes",
        "terraform",
        "ansible",
        "jenkins",
        "ci/cd",
        "devops",
        "sre",
        "cloud",
        "infrastructure",
        "linux",
        "unix",
        "networking",
        "security",
        "monitoring",
        "logging",
        "prometheus",
        "grafana",
    }

    DATA = {
        "etl",
        "data warehouse",
        "data lake",
        "spark",
        "hadoop",
        "airflow",
        "dbt",
        "snowflake",
        "redshift",
        "big data",
        "data pipeline",
        "data engineering",
        "data infrastructure",
        "data modeling",
        "data architecture",
    }

    @classmethod
    def detect_tech_stacks(cls, text: str) -> Set[TechStack]:
        """Detect tech stacks from text description."""
        text = text.lower()
        stacks = set()

        # Check for each tech stack
        if any(keyword in text for keyword in cls.BACKEND):
            stacks.add(TechStack.BACKEND)

        if any(keyword in text for keyword in cls.FRONTEND):
            stacks.add(TechStack.FRONTEND)

        if any(keyword in text for keyword in cls.ML_AI):
            stacks.add(TechStack.ML_AI)

        if any(keyword in text for keyword in cls.INFRASTRUCTURE):
            stacks.add(TechStack.INFRASTRUCTURE)

        if any(keyword in text for keyword in cls.DATA):
            stacks.add(TechStack.DATA)

        # Infer Full Stack
        if TechStack.BACKEND in stacks and TechStack.FRONTEND in stacks:
            stacks.add(TechStack.FULLSTACK)
        elif "full stack" in text or "fullstack" in text:
            stacks.add(TechStack.FULLSTACK)
            stacks.add(TechStack.BACKEND)
            stacks.add(TechStack.FRONTEND)

        return stacks


class CareerMetrics(SerializableModel):
    """Model for career analysis metrics."""

    total_experience_months: int
    total_experience_years: float
    average_tenure_months: int
    average_tenure_years: float
    current_tenure_months: int
    current_tenure_years: float
    tech_stacks: Optional[List[str]] = None
    career_tags: Optional[List[str]] = None
    experience_by_stage: List[ExperienceStageMetrics] = []

    @staticmethod
    def calculate_months_between(start_date: date, end_date: date) -> float:
        """Calculate months between two dates."""
        months = (end_date.year - start_date.year) * 12 + (
            end_date.month - start_date.month
        )
        # Add partial month
        days_in_month = calendar.monthrange(end_date.year, end_date.month)[1]
        months += end_date.day / days_in_month
        return round(months, 1)

    def to_dict(self) -> dict:
        """Convert career metrics to a dictionary format."""
        return {
            "average_tenure_years": self.average_tenure_years,
            "current_tenure_years": self.current_tenure_years,
            "total_experience_years": self.total_experience_years,
            "tech_stacks": self.tech_stacks,
            "career_tags": self.career_tags,
            "experience_by_stage": [
                {
                    "company": exp.company_name,
                    "stage": exp.funding_stage,
                    "duration_years": exp.duration_months / 12,
                    "tier": exp.company_tier,
                }
                for exp in self.experience_by_stage
            ],
        }
