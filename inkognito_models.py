import hashlib
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional


class Priority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NONE = "NONE"


@dataclass
class SubjectProfile:
    """
    Everything the client provides on the intake form.
    Only full_name + current_city are required.
    All other fields are optional.
    """

    # Required
    full_name: str
    current_city: str

    # Strongly recommended
    age: Optional[int] = None
    native_city: Optional[str] = None

    # Conditional triggers
    employer_name: Optional[str] = None
    business_name: Optional[str] = None
    company_name: Optional[str] = None
    education_college: Optional[str] = None
    education_year: Optional[int] = None

    # Social media inputs
    linkedin_url: Optional[str] = None
    instagram_username: Optional[str] = None
    facebook_profile_id: Optional[str] = None

    # Reverse image / phone / property
    photo_path: Optional[str] = None
    mobile: Optional[str] = None
    known_property_areas: Optional[list[str]] = None

    def has_business(self) -> bool:
        return bool(self.business_name or self.company_name)

    def has_employer(self) -> bool:
        return bool(self.employer_name)

    def has_photo(self) -> bool:
        return bool(self.photo_path and os.path.exists(self.photo_path))

    def has_finance_role(self) -> bool:
        """True when subject likely has a finance role (triggers SEBI check)."""
        if getattr(self, "claims_finance_role", False):
            return True
        finance_keywords = [
            "stock",
            "invest",
            "broker",
            "trading",
            "mutual fund",
            "wealth",
            "portfolio",
            "sebi",
            "nse",
            "bse",
            "fund manager",
            "financial advisor",
            "chartered accountant",
        ]
        combined = " ".join(
            [self.employer_name or "", self.business_name or "", self.company_name or ""]
        ).lower()
        return any(kw in combined for kw in finance_keywords)

    def report_id(self) -> str:
        raw = f"{self.full_name}{self.current_city}{datetime.now().date()}"
        return "IK-" + hashlib.md5(raw.encode()).hexdigest()[:8].upper()


@dataclass
class Finding:
    source: str
    category: str
    title: str
    detail: str
    priority: Priority = Priority.LOW
    url: Optional[str] = None
    raw_data: Optional[dict] = None


LEGAL_FILTER_LOG = logging.getLogger("Inkognito.LegalFilter")

_LEGAL_BLOCKLIST_TERMS = (
    # RBI / CICRA 2005 — regulated credit data (prohibited for unlicensed entities)
    "loan default",
    "loan defaults",
    "cibil",
    "credit score",
    "wilful defaulter",
    "willful defaulter",
    "credit report",
    "credit history",
    "credit bureau",
    "loan account",
    "non-performing asset",
    "npa",
    "bank defaulter",
    "bank default",
    # IT Act Sections 66E / 67 — intimate and obscene content (criminally prohibited)
    "intimate photograph",
    "nude",
    "obscene content",
    "sexually explicit",
    # Defamation risk — editorial, gossip, and unverified aggregator content
    "news article",
    "blog post",
    "gossip",
)


def _legal_filter_block_reason(finding: Finding) -> Optional[str]:
    """Return block reason if a finding contains disallowed content."""
    haystack = f"{finding.source} {finding.detail}".lower()

    for term in _LEGAL_BLOCKLIST_TERMS:
        if term in haystack:
            return f"matched keyword '{term}'"

    social_markers = ("linkedin", "instagram", "facebook", "social media")
    opinion_markers = (
        "opinion",
        "political statement",
        "religious view",
        "political view",
        "religious belief",
    )
    if any(s in haystack for s in social_markers) and any(p in haystack for p in opinion_markers):
        return "scraped social opinion/political/religious content"

    news_markers = ("news", "newspaper", "blogspot", "wordpress", "medium.com")
    if any(n in haystack for n in news_markers):
        return "news/blog/gossip sourced content"

    return None


class LegalFilteredFindings(list):
    """List-like container that blocks legally disallowed findings."""

    def append(self, item):
        if isinstance(item, Finding):
            reason = _legal_filter_block_reason(item)
            if reason:
                LEGAL_FILTER_LOG.info(
                    f"[BLOCKED — legal filter] {item.source} | {item.title} | {reason}"
                )
                return
        super().append(item)

    def extend(self, items):
        for item in items:
            self.append(item)


@dataclass
class ModuleResult:
    module_name: str
    ran: bool = False
    skipped: bool = False
    skip_reason: str = ""
    success: bool = False
    error: str = ""
    findings: list[Finding] = field(default_factory=LegalFilteredFindings)
    raw_results: list[dict] = field(default_factory=list)
    duration_sec: float = 0.0

    @property
    def high_priority_count(self) -> int:
        return sum(1 for f in self.findings if f.priority == Priority.HIGH)

    @property
    def medium_priority_count(self) -> int:
        return sum(1 for f in self.findings if f.priority == Priority.MEDIUM)


@dataclass
class UnifiedReport:
    report_id: str
    subject: SubjectProfile
    generated_at: str
    modules: dict[str, ModuleResult] = field(default_factory=dict)

    @property
    def all_findings(self) -> list[Finding]:
        findings = []
        for module in self.modules.values():
            findings.extend(module.findings)
        return findings

    @property
    def high_priority_findings(self) -> list[Finding]:
        return [f for f in self.all_findings if f.priority == Priority.HIGH]

    @property
    def overall_flag(self) -> str:
        hp = len(self.high_priority_findings)
        mp = sum(1 for f in self.all_findings if f.priority == Priority.MEDIUM)
        if hp > 0:
            return f"🔴 HIGH — {hp} significant finding(s) require attention"
        if mp > 0:
            return f"🟡 MEDIUM — {mp} item(s) to review with subject"
        return "🟢 CLEAR — No significant issues found"

    def to_dict(self) -> dict:
        deletion_date = (
            datetime.fromisoformat(self.generated_at) + timedelta(days=30)
        ).isoformat()
        return {
            "report_id": self.report_id,
            "subject_name": self.subject.full_name,
            "generated_at": self.generated_at,
            "deletion_scheduled_at": deletion_date,
            "legal_disclaimer": {
                "as_is_nature": (
                    "This report is an automated snapshot of publicly available statutory and "
                    "government records retrieved at the timestamp shown above. It is provided "
                    "strictly 'as-is' without any representation, warranty, or guarantee of "
                    "accuracy, completeness, or fitness for any particular purpose. "
                    "Inkognito is a Data Aggregation Platform, not a private detective agency "
                    "or licensed credit bureau."
                ),
                "no_professional_verification": (
                    "The platform does not independently verify the factual accuracy of source "
                    "records. Government databases are inherently subject to clerical errors, "
                    "indexing delays, and outdated status entries. This report does not "
                    "constitute a certified investigation, legal opinion, or professional "
                    "due diligence opinion. Do not treat any finding as conclusive."
                ),
                "data_currency_warning": (
                    "A finding reflects the state of public records at the moment of retrieval "
                    "and may not reflect subsequent legal developments such as acquittals, "
                    "case dismissals, struck-off status reversals, or registration corrections. "
                    "The requesting party is strongly advised to independently verify any "
                    "adverse finding before taking any action."
                ),
                "liability_cap": (
                    "The maximum aggregate liability of the platform for any claim, loss, or "
                    "damage arising from or related to this report is strictly limited to the "
                    "fee paid for this specific report. The platform expressly excludes liability "
                    "for indirect, consequential, special, or incidental damages — including "
                    "but not limited to: broken engagements, emotional distress, reputational "
                    "harm, or cancelled wedding expenditures."
                ),
                "customer_indemnity": (
                    "By commissioning this report, the requesting party agrees to indemnify, "
                    "defend, and hold the platform harmless from any claim, suit, or liability "
                    "arising from: (a) reliance on this report; (b) redistribution, publication, "
                    "or unauthorised sharing of this report or its contents; or (c) any use of "
                    "this report for a purpose other than personal pre-matrimonial due diligence."
                ),
                "restricted_use": (
                    "This report is exclusively for the personal use of the commissioning party "
                    "for pre-matrimonial due diligence purposes only. Redistribution, publication, "
                    "sale, or commercial use is strictly prohibited and may constitute a criminal "
                    "offence under applicable law."
                ),
                "data_scope": (
                    "This report is compiled exclusively from publicly available statutory and "
                    "government records (eCourts, MCA21, GST, EPFO, SEBI enforcement orders, "
                    "property registration indices, consumer forum records). It does not include "
                    "credit bureau data, loan repayment history, bank default records, or any "
                    "information obtained from restricted databases or regulated credit repositories."
                ),
                "scheduled_deletion": (
                    f"This report and associated processing data will be permanently deleted from "
                    f"platform systems 30 days from generation. Deletion deadline: {deletion_date[:10]}."
                ),
            },
            "overall_flag": self.overall_flag,
            "total_findings": len(self.all_findings),
            "high_priority": len(self.high_priority_findings),
            "medium_priority": sum(
                1 for f in self.all_findings if f.priority == Priority.MEDIUM
            ),
            "modules_run": {
                name: {
                    "ran": m.ran,
                    "skipped": m.skipped,
                    "skip_reason": m.skip_reason,
                    "success": m.success,
                    "findings_count": len(m.findings),
                    "high_priority": m.high_priority_count,
                    "duration_sec": round(m.duration_sec, 2),
                    "findings": [
                        {
                            "source": f.source,
                            "category": f.category,
                            "title": f.title,
                            "detail": f.detail,
                            "priority": f.priority.value,
                        }
                        for f in m.findings
                    ],
                }
                for name, m in self.modules.items()
            },
        }
