"""Closed enumerations (docs/SEMANTICS.md §1)."""

from enum import StrEnum


class Role(StrEnum):
    MANAGER = "manager"
    FINANCE = "finance"
    SECURITY = "security"
    LEGAL = "legal"
    PROCUREMENT = "procurement"
    IT = "it"
    EXECUTIVE = "executive"


class Department(StrEnum):
    ENGINEERING = "engineering"
    SALES = "sales"
    MARKETING = "marketing"
    FINANCE = "finance"
    HR = "hr"
    OPERATIONS = "operations"
    LEGAL = "legal"


class Category(StrEnum):
    SOFTWARE = "software"
    HARDWARE = "hardware"
    SERVICES = "services"
    MARKETING = "marketing"
    TRAVEL = "travel"
    OFFICE = "office"
    FACILITIES = "facilities"


class VendorRisk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    PROHIBITED = "prohibited"
    UNKNOWN = "unknown"


class Currency(StrEnum):
    USD = "USD"


class EvidenceType(StrEnum):
    SECURITY_QUESTIONNAIRE = "security_questionnaire"
    SOC2_REPORT = "soc2_report"
    QUOTE = "quote"
    CONTRACT_DRAFT = "contract_draft"
    W9 = "w9"


class Decision(StrEnum):
    AUTO_APPROVED = "AUTO_APPROVED"
    NEEDS_APPROVAL = "NEEDS_APPROVAL"
    BLOCKED = "BLOCKED"


class Severity(StrEnum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
