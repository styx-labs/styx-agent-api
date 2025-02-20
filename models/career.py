from datetime import date
from enum import Enum
from .serializable import SerializableModel


class FundingType(str, Enum):
    """Detailed funding type classification."""

    ANGEL = "Angel Round"
    CONVERTIBLE_NOTE = "Convertible Note"
    CORPORATE = "Corporate Round"
    DEBT = "Debt Financing"
    EQUITY_CROWDFUNDING = "Equity Crowdfunding"
    GENERIC = "Funding Round"
    GRANT = "Grant"
    ICO = "Initial Coin Offering"
    NON_EQUITY = "Non Equity Assistance"
    POST_IPO_DEBT = "Post-IPO Debt"
    POST_IPO_EQUITY = "Post-IPO Equity"
    POST_IPO_SECONDARY = "Post-IPO Secondary"
    PRE_SEED = "Pre Seed Round"
    PRIVATE_EQUITY = "Private Equity Round"
    PRODUCT_CROWDFUNDING = "Product Crowdfunding"
    SECONDARY_MARKET = "Secondary Market"
    SEED = "Seed Round"
    SERIES_A = "Series A"
    SERIES_B = "Series B"
    SERIES_C = "Series C"
    SERIES_D = "Series D"
    SERIES_E = "Series E"
    SERIES_F = "Series F"
    SERIES_G = "Series G"
    SERIES_H = "Series H"
    SERIES_I = "Series I"
    SERIES_J = "Series J"
    VENTURE = "Venture Round"
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
    funding_stage: FundingType
    joined_at: date
    left_at: date | None
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
    def detect_tech_stacks(cls, text: str) -> set[TechStack]:
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

    total_experience_months: int | None
    average_tenure_months: int | None
    current_tenure_months: int | None
    tech_stacks: list[str] | None
    career_tags: list[str] | None
    experience_tags: list[str] | None
    latest_experience_level: str | None = None
