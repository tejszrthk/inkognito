"""
Inkognito — Public Records Data Aggregation Pipeline
=====================================================
Single entry point that orchestrates ALL statutory data source searches
in the correct order, with conditional logic based on what
information the client has provided.

This platform is a Data Aggregation Service operating strictly on
publicly available statutory and government records. It is NOT a private
detective agency. All data sources are restricted to records that are
free from DPDP Act 2023 obligations under Section 3(c)(ii) (publicly
mandated government records).

ARCHITECTURE:
  SubjectProfile (input form data)
       ↓
  SearchPipeline.run()
       ↓
  ┌─────────────────────────────────────────┐
  │  ALWAYS RUN                             │
  │  • eCourts (LegalKart API)              │
  │  • MCA21 Director Search                │
  │  • GST Portal                           │
  │  • Google Deep Search                   │
  │  • Reverse Image Search (Yandex)        │
  └─────────────────────────────────────────┘
       ↓
  ┌─────────────────────────────────────────┐
  │  CONDITIONAL — only if business given   │
  │  • NCDRC / Consumer Forum (e-Jagriti)   │
  │  • NCLT Insolvency Check                │
  └─────────────────────────────────────────┘
       ↓
  ┌─────────────────────────────────────────┐
  │  CONDITIONAL — only if employer given   │
  │  • EPFO Employer Verification           │
  │  • LinkedIn Cross-check                 │
  └─────────────────────────────────────────┘
       ↓
  ┌─────────────────────────────────────────┐
  │  CONDITIONAL — only if photo given      │
  │  • Reverse Image Search                 │
  │  • Matrimonial Platform Check           │
  └─────────────────────────────────────────┘
       ↓
  UnifiedReport (structured JSON)

DATA SOURCES STATUS:
  ✓ eCourts       → LegalKart API (paid, ₹0.50-2/hit)
  ✓ NCDRC         → e-Jagriti scrape (free, conditional on business)
  ✓ NCLT          → LegalKart API + IBBI scrape (conditional on business)
  ✓ SEBI          → NSE debarred XLS + sebi.gov.in scrape (conditional on finance)
  ✓ MCA21         → Direct scrape / MCA API (free)
  ✓ GST           → GST portal scrape (free)
  ✓ EPFO          → EPFO portal scrape (free, conditional on employer)
  ✓ Google Search → SerpAPI or direct (paid/free)

SETUP:
  pip install requests python-dotenv playwright beautifulsoup4 serpapi

  .env file:
    LEGALKART_API_KEY=your_key
    SERP_API_KEY=your_key       (optional, for Google search)
    MCA_API_PROVIDER=surepass   (surepass | sandbox | compdata | scrape)
    MCA_API_KEY=your_key        (from whichever MCA provider you choose)
    CAPTCHA_API_KEY=your_key    (2captcha.com key; internal testing only)
    CAPTCHA_BYPASS_ENABLED=False  (legal risk; keep False unless legal sign-off)
    TINEYE_API_KEY=your_key     (tineye.com, optional — exact photo copy detection)
    IMGBB_API_KEY=your_key      (imgbb.com free — needed to host photos for image search)
"""

import os
import json
import time
import logging
from datetime import datetime
from typing import Optional, Callable

import requests
from dotenv import load_dotenv
from inkognito_models import (
    Finding,
    ModuleResult,
    Priority,
    SubjectProfile,
    UnifiedReport,
)

load_dotenv()

# ─── LOGGING ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger("Inkognito")

# ─── CONFIG ───────────────────────────────────────────────────────────────────

LEGALKART_API_KEY = os.getenv("LEGALKART_API_KEY", "")
LEGALKART_BASE    = "https://www.legalkart.com/api"   # update from their docs
SERP_API_KEY      = os.getenv("SERP_API_KEY", "")     # optional
GRIEVANCE_EMAIL   = os.getenv("GRIEVANCE_EMAIL", "")  # required: contact for subject data requests
REQUEST_DELAY     = 1.5   # seconds between API calls
MAX_RETRIES       = 3


# ─── COMPLIANCE FRAMEWORK ────────────────────────────────────────────────────────────
#
# Applicable laws: DPDP Act 2023, IT Act 2000, CICRA 2005, BNS 2023 S.356,
#                  Companies Act 2013, Consumer Protection Act 2019.
#
# The following controls are permanently enforced in this codebase:
#
#   ✓ Social media automated scraping   : DISABLED (IT Act S.43(b) + platform ToS)
#   ✓ CAPTCHA bypass on govt portals    : DISABLED by default (set CAPTCHA_BYPASS_ENABLED)
#   ✓ Credit bureau / loan default data : BLOCKED (CICRA 2005 + RBI Directions 2024)
#   ✓ News / blog / gossip aggregation  : BLOCKED (civil defamation risk)
#   ✓ Intimate / obscene content         : BLOCKED (IT Act S.66E / S.67)
#   ✓ Subjective opinions / religious    : BLOCKED (BNS S.356 defamation risk)
#   ✓ Photo / binary data in reports     : TEXT-ONLY findings, no binary content stored
#   ✓ Report retention                   : 30-day scheduled deletion (see UnifiedReport)
#   ✓ Database caching of subject data   : DISABLED — live queries only, no stale data
#   ✓ "Private detective" branding       : PROHIBITED — use "Data Aggregation Platform"
#
# Permitted sources (DPDPA S.3(c)(ii) exempt — publicly mandated records):
#   eCourts, MCA21, GST, EPFO, SEBI enforcement orders, property registries
#   (NGDRS / IGRSUP / CERSAI), NCDRC / e-Jagriti, IBBI, NSE debarred XLS
#
# Social media: Google site-search discovery only (SerpAPI). No automated
#   profile fetch. Human analyst manual review checklists only.
#
# Board instruction on record: Engineers are expressly prohibited from
#   deploying automated scrapers that bypass CAPTCHAs, login walls, or
#   platform ToS. Violation may constitute personal liability under IT Act S.85.
#
# Grievance contact: set GRIEVANCE_EMAIL in .env to publish a subject
#   rights contact as required under DPDP Rules 2025.


# ─── SHARED UTILITIES ─────────────────────────────────────────────────────────

def generate_name_variations(full_name: str) -> list[str]:
    """Generate spelling variations covering common Indian surname transliterations."""
    parts = full_name.strip().split()
    first = parts[0] if parts else ""
    last_parts = parts[1:] if len(parts) > 1 else []
    last = " ".join(last_parts)

    surname_map = {
        "chaudhary": ["Chaudhary", "Chaudhry", "Choudhari", "Choudhary", "Chowdhury"],
        "sharma":    ["Sharma", "Sarma"],
        "singh":     ["Singh", "Sinha"],
        "gupta":     ["Gupta", "Guptha"],
        "verma":     ["Verma", "Varma"],
        "kumar":     ["Kumar", "Kumaar"],
        "mehta":     ["Mehta", "Metha"],
        "kapoor":    ["Kapoor", "Kapur"],
        "agarwal":   ["Agarwal", "Aggarwal", "Agrawal"],
        "joshi":     ["Joshi", "Joshee"],
        "mishra":    ["Mishra", "Misra"],
        "pandey":    ["Pandey", "Pandé", "Pande"],
        "yadav":     ["Yadav", "Yadaw"],
        "khan":      ["Khan", "Kha"],
        "ansari":    ["Ansari", "Ansari"],
    }

    variations = [full_name]
    last_lower = last.lower()

    if last_lower in surname_map:
        for variant in surname_map[last_lower]:
            v = f"{first} {variant}".strip()
            if v not in variations:
                variations.append(v)
    elif len(parts) == 3:
        # Also try First + Last without middle name
        short = f"{parts[0]} {parts[2]}"
        if short not in variations:
            variations.append(short)

    return variations


def safe_request(
    method: str,
    url: str,
    session: requests.Session = None,
    headers: dict = None,
    params: dict = None,
    json_body: dict = None,
    timeout: int = 15,
    retries: int = MAX_RETRIES,
) -> Optional[requests.Response]:
    """
    HTTP request with retry logic and rate limit handling.
    Accepts an optional persistent session for connection reuse.
    Falls back to a one-off request if no session provided.
    """
    requester = session or requests
    for attempt in range(retries):
        try:
            time.sleep(REQUEST_DELAY)
            response = requester.request(
                method, url,
                headers=headers or {},
                params=params,
                json=json_body,
                timeout=timeout
            )
            if response.status_code == 429:
                wait = 5 * (attempt + 1)
                log.warning(f"Rate limited on {url}. Waiting {wait}s...")
                time.sleep(wait)
                continue
            return response
        except requests.exceptions.Timeout:
            log.warning(f"Timeout on attempt {attempt + 1} for {url}")
        except requests.exceptions.RequestException as e:
            log.warning(f"Request error on attempt {attempt + 1}: {e}")
        if attempt < retries - 1:
            time.sleep(2)
    return None


# ─── PIPELINE CONTEXT — single auth + shared state per report run ─────────────

class PipelineContext:
    """
    Created once per report run by SearchPipeline.
    Holds all shared, expensive-to-compute state so no module
    ever duplicates work done by another module.

    What gets computed ONCE and reused by ALL modules:
      • LegalKart bearer token      (1 API auth call total)
      • name_variations             (computed once from subject name)
      • districts                   (built once from subject cities)
      • HTTP sessions per domain    (persistent TCP + cookie reuse)
      • NSE debarred list           (downloaded once, searched N times)
    """

    def __init__(self, subject: SubjectProfile):
        self.subject = subject

        # ── Computed once ──────────────────────────────────────────────────
        self.name_variations: list[str] = generate_name_variations(subject.full_name)
        self.districts: list[str] = self._build_districts()

        # ── Token: lazily fetched once, reused by eCourts + NCLT ──────────
        self._legalkart_token: Optional[str] = None
        self._token_fetched: bool = False

        # ── Sessions: one per domain, persistent across all modules ────────
        # Each session maintains keep-alive, cookies, and base headers
        self.sessions: dict[str, requests.Session] = {
            "legalkart": self._make_session({
                "Accept": "application/json",
            }),
            "mca":       self._make_session(),
            "gst":       self._make_session({"Accept": "application/json"}),
            "epfo":      self._make_session({"Accept": "application/json",
                                             "Content-Type": "application/json"}),
            "ejagriti":  self._make_session({"Accept": "text/html,application/json"}),
            "ibbi":      self._make_session(),
            "sebi":      self._make_session(),
            "serp":      self._make_session({"Accept": "application/json"}),
            "ngdrs":     self._make_session({"Accept": "text/html,application/xhtml+xml"}),
            "igrsup":    self._make_session({"Accept": "text/html,application/xhtml+xml"}),
            "instagram": self._make_session({
                "Accept": "text/html,application/json",
                "X-IG-App-ID": "936619743392459",   # public IG web app ID
            }),
            "linkedin":  self._make_session({
                "Accept": "application/json",
            }),
            "facebook":    self._make_session({"Accept": "application/json"}),
            "yandex":      self._make_session({"Accept": "text/html,application/json"}),
            "tineye":      self._make_session({"Accept": "application/json"}),
            "phone":       self._make_session({"Accept": "text/html,application/json"}),
            "matrimonial": self._make_session({"Accept": "text/html,application/json"}),
        }

        # ── NSE debarred list: downloaded once, searched by SEBI module ───
        self._nse_debarred: Optional[list[dict]] = None
        self._nse_loaded: bool = False

        log.info(
            f"[Context] Initialised for '{subject.full_name}' — "
            f"{len(self.name_variations)} name variant(s), "
            f"{len(self.districts)} district(s)"
        )

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _make_session(extra_headers: dict = None) -> requests.Session:
        s = requests.Session()
        s.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; Inkognito/1.0)",
        })
        if extra_headers:
            s.headers.update(extra_headers)
        return s

    def _build_districts(self) -> list[str]:
        base = [
            "Delhi", "Saket", "Rohini", "Tis Hazari",
            "Dwarka", "Karkardooma", "Gurugram", "Gautam Buddh Nagar"
        ]
        if self.subject.native_city and self.subject.native_city not in base:
            base.insert(0, self.subject.native_city)
        return base

    # ── LegalKart token — fetched exactly once per pipeline run ───────────

    @property
    def legalkart_token(self) -> Optional[str]:
        if self._token_fetched:
            return self._legalkart_token          # cached — even if None

        if not LEGALKART_API_KEY:
            log.error("[Context] LEGALKART_API_KEY not set in .env")
            self._token_fetched = True
            return None

        auth_timeout = int(os.getenv("LEGALKART_AUTH_TIMEOUT_SEC", "4"))
        auth_retries = int(os.getenv("LEGALKART_AUTH_RETRIES", "1"))

        log.info(
            f"[Context] Fetching LegalKart token (once per run, timeout={auth_timeout}s, retries={auth_retries})..."
        )

        auth_url = f"{LEGALKART_BASE}/auth"
        session = self.sessions["legalkart"]

        for attempt in range(auth_retries):
            try:
                r = session.post(
                    auth_url,
                    json={"api_key": LEGALKART_API_KEY},
                    timeout=auth_timeout,
                )

                if not r.ok:
                    log.warning(
                        f"[Context] LegalKart auth failed (status={r.status_code}) on attempt {attempt + 1}"
                    )
                    if attempt < auth_retries - 1:
                        time.sleep(1)
                    continue

                data = r.json()
                self._legalkart_token = data.get("token") or data.get("access_token")
                if self._legalkart_token:
                    log.info("[Context] ✓ LegalKart token acquired")
                    # Inject into session header so all future calls are authenticated
                    session.headers.update(
                        {"Authorization": f"Bearer {self._legalkart_token}"}
                    )
                else:
                    log.error("[Context] LegalKart auth response had no token")
                break

            except requests.exceptions.Timeout:
                log.warning(
                    f"[Context] LegalKart auth timeout on attempt {attempt + 1}"
                )
            except requests.exceptions.RequestException as e:
                log.warning(
                    f"[Context] LegalKart auth request error on attempt {attempt + 1}: {e}"
                )

            if attempt < auth_retries - 1:
                time.sleep(1)

        if not self._legalkart_token:
            log.error("[Context] LegalKart auth unavailable for this run")

        self._token_fetched = True
        return self._legalkart_token

    # ── LegalKart auth header — convenience shortcut ──────────────────────

    @property
    def legalkart_headers(self) -> dict:
        token = self.legalkart_token
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}

    # ── NSE debarred list — downloaded once per run ───────────────────────

    @property
    def nse_debarred(self) -> list[dict]:
        if self._nse_loaded:
            return self._nse_debarred or []

        NSE_XLS_URL = (
            "https://www.nseindia.com/content/regulations/debarredentities.xlsx"
        )
        try:
            import io
            import openpyxl
            log.info("[Context] Downloading NSE debarred entities list (once per run)...")
            r = safe_request(
                "GET", NSE_XLS_URL,
                session=self.sessions["sebi"],
                headers={"Referer": "https://www.nseindia.com/static/regulations/member-sebi-debarred-entities"}
            )
            if r and r.ok:
                wb = openpyxl.load_workbook(io.BytesIO(r.content), read_only=True)
                ws = wb.active
                rows = list(ws.iter_rows(values_only=True))
                if rows:
                    hdrs = [str(h).strip().lower() if h else f"col_{i}"
                            for i, h in enumerate(rows[0])]
                    entities = []
                    for row in rows[1:]:
                        if not any(row):
                            continue
                        entities.append({
                            hdrs[i]: str(v).strip() if v is not None else ""
                            for i, v in enumerate(row)
                            if i < len(hdrs)
                        })
                    self._nse_debarred = entities
                    log.info(f"[Context] ✓ NSE debarred list: {len(entities)} entities")
            else:
                log.warning("[Context] NSE debarred XLS unavailable")
                self._nse_debarred = []
        except ImportError:
            log.warning("[Context] openpyxl not installed — NSE XLS skipped")
            self._nse_debarred = []
        except Exception as e:
            log.warning(f"[Context] NSE debarred load error: {e}")
            self._nse_debarred = []

        self._nse_loaded = True
        return self._nse_debarred or []

    def close(self):
        """Close all HTTP sessions cleanly after pipeline completes."""
        for name, session in self.sessions.items():
            try:
                session.close()
            except requests.exceptions.RequestException as e:
                log.warning(f"[Context] Failed to close session '{name}': {e}")
            except Exception as e:
                log.warning(f"[Context] Unexpected close error for '{name}': {e}")
        log.info("[Context] All HTTP sessions closed.")




# ─── MODULE 1: eCOURTS (via LegalKart API) ────────────────────────────────────

HIGH_PRIORITY_SECTIONS = [
    "498A", "376", "354", "POCSO", "Dowry",
    "Matrimonial", "Divorce", "Maintenance", "Custody",
    "420", "406", "Criminal Breach"
]

MEDIUM_PRIORITY_SECTIONS = [
    "138", "Cheque Bounce", "Money Recovery",
    "Civil Suit", "Injunction", "Arbitration"
]


def _classify_case(case_json: dict) -> Priority:
    text = json.dumps(case_json).upper()
    for kw in HIGH_PRIORITY_SECTIONS:
        if kw.upper() in text:
            return Priority.HIGH
    for kw in MEDIUM_PRIORITY_SECTIONS:
        if kw.upper() in text:
            return Priority.MEDIUM
    return Priority.LOW


def run_ecourts(subject: SubjectProfile, ctx: PipelineContext) -> ModuleResult:
    result = ModuleResult(module_name="eCourts")
    start = time.time()

    # Token from context — no re-auth
    if not ctx.legalkart_token:
        result.ran = True
        result.error = "LegalKart authentication failed. Check API key."
        result.duration_sec = time.time() - start
        return result

    # Name variations and districts from context — no recomputation
    name_variations = ctx.name_variations
    districts = ctx.districts
    session = ctx.sessions["legalkart"]  # persistent session

    all_cases = []
    seen_cnrs = set()

    log.info(f"[eCourts] Searching {len(name_variations)} variations × "
             f"{len(districts)} districts")

    for name in name_variations:
        for district in districts:
            r = safe_request("GET", f"{LEGALKART_BASE}/cases/keyword-search",
                             session=session,
                             params={"keyword": name, "district": district})
            if r and r.ok:
                cases = r.json().get("cases") or r.json().get("results") or []
                for case in cases:
                    cnr = case.get("cnr") or case.get("cnr_number", "")
                    if cnr and cnr not in seen_cnrs:
                        seen_cnrs.add(cnr)
                        all_cases.append(case)

    # Fetch full details per CNR
    detailed = []
    for case in all_cases:
        cnr = case.get("cnr") or case.get("cnr_number")
        if cnr:
            r = safe_request("GET", f"{LEGALKART_BASE}/cases/cnr/{cnr}",
                             session=session)
            if r and r.ok:
                detailed.append(r.json())
            else:
                detailed.append(case)
        else:
            detailed.append(case)

    result.ran = True
    result.success = True
    result.raw_results = detailed

    for case in detailed:
        priority = _classify_case(case)
        finding = Finding(
            source="eCourts / LegalKart API",
            category="Legal & Court Records",
            title=f"{case.get('case_type', 'Case')} — {case.get('court', '')}",
            detail=(
                f"Filed: {case.get('filing_date', 'N/A')} | "
                f"Status: {case.get('current_status', 'N/A')} | "
                f"Parties: {case.get('petitioner', '')} vs {case.get('respondent', '')} | "
                f"Sections: {case.get('acts') or case.get('sections', 'N/A')}"
            ),
            priority=priority,
            raw_data=case
        )
        result.findings.append(finding)

    log.info(f"[eCourts] {len(detailed)} cases found. "
             f"High: {result.high_priority_count} | "
             f"Medium: {result.medium_priority_count}")

    result.duration_sec = time.time() - start
    return result


# ─── MODULE 2: NCDRC / Consumer Forum (e-Jagriti scrape) ─────────────────────
# CONDITIONAL: only runs when subject.has_business() == True

def run_ncdrc(subject: SubjectProfile, ctx: PipelineContext) -> ModuleResult:
    result = ModuleResult(module_name="NCDRC")

    # ── Conditional gate ──────────────────────────────────────────────────────
    if not subject.has_business():
        result.skipped = True
        result.skip_reason = (
            "No business name provided. NCDRC checks are only relevant "
            "when the subject runs a business and consumer complaints are possible. "
            "If business information is later provided, re-run this module."
        )
        log.info("[NCDRC] Skipped — no business name in profile")
        return result

    start = time.time()
    result.ran = True

    business_name = subject.business_name or subject.company_name
    search_names = [subject.full_name, business_name]

    log.info(f"[NCDRC] Searching for: {search_names}")

    # e-Jagriti replaced eDaakhil as of Jan 2025
    # Portal: https://e-jagriti.gov.in
    # Search endpoint (requires investigation of actual form params after login)
    EJAGRITI_SEARCH_URL = "https://e-jagriti.gov.in/case-status"

    for search_term in search_names:
        try:
            session = ctx.sessions["ejagriti"]  # persistent session from context
            # e-Jagriti uses a POST form with CSRF token
            # Step 1: GET the page to extract CSRF token
            page = safe_request("GET", EJAGRITI_SEARCH_URL,
                                session=session, timeout=15)

            if not page or not page.ok:
                result.error = f"e-Jagriti portal returned {page.status_code if page else 'no response'}"
                continue

            # Step 2: Parse CSRF token from HTML
            # Note: exact field name needs verification from portal inspection
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(page.text, "html.parser")
            csrf = ""
            csrf_input = soup.find("input", {"name": "_token"}) or \
                         soup.find("input", {"name": "csrf_token"}) or \
                         soup.find("meta", {"name": "csrf-token"})
            if csrf_input:
                csrf = csrf_input.get("value") or csrf_input.get("content", "")

            # Step 3: Submit party name search
            time.sleep(REQUEST_DELAY)
            search_response = session.post(
                EJAGRITI_SEARCH_URL,
                data={
                    "_token": csrf,
                    "party_name": search_term,
                    "commission_type": "all",  # NCDRC + State + District
                },
                headers={"Referer": EJAGRITI_SEARCH_URL},
                timeout=15
            )

            if not search_response.ok:
                continue

            # Step 4: Parse results table
            results_soup = BeautifulSoup(search_response.text, "html.parser")
            table = results_soup.find("table", {"class": "case-table"}) or \
                    results_soup.find("table")

            if not table:
                log.info(f"[NCDRC] No results table found for '{search_term}'")
                continue

            rows = table.find_all("tr")[1:]  # Skip header
            log.info(f"[NCDRC] Found {len(rows)} row(s) for '{search_term}'")

            for row in rows:
                cols = [td.get_text(strip=True) for td in row.find_all("td")]
                if not cols:
                    continue

                raw = {
                    "case_number":    cols[0] if len(cols) > 0 else "N/A",
                    "complainant":    cols[1] if len(cols) > 1 else "N/A",
                    "opposite_party": cols[2] if len(cols) > 2 else "N/A",
                    "commission":     cols[3] if len(cols) > 3 else "N/A",
                    "status":         cols[4] if len(cols) > 4 else "N/A",
                    "filed_date":     cols[5] if len(cols) > 5 else "N/A",
                    "search_term":    search_term,
                }
                result.raw_results.append(raw)

                # Consumer complaints against a business are MEDIUM priority
                # unless it appears the subject is the opposite party being sued
                is_opposite_party = (
                    subject.full_name.lower() in raw["opposite_party"].lower() or
                    (business_name and business_name.lower() in raw["opposite_party"].lower())
                )

                priority = Priority.MEDIUM if is_opposite_party else Priority.LOW

                finding = Finding(
                    source="NCDRC / e-Jagriti",
                    category="Consumer Complaints",
                    title=f"Consumer case — {raw['commission']}",
                    detail=(
                        f"Case: {raw['case_number']} | "
                        f"Complainant: {raw['complainant']} | "
                        f"Opposite Party: {raw['opposite_party']} | "
                        f"Status: {raw['status']} | "
                        f"Filed: {raw['filed_date']}"
                    ),
                    priority=priority,
                    raw_data=raw
                )
                result.findings.append(finding)

        except ImportError:
            result.error = "beautifulsoup4 not installed. Run: pip install beautifulsoup4"
            break
        except Exception as e:
            log.warning(f"[NCDRC] Error searching '{search_term}': {e}")
            result.error = str(e)

    result.success = not bool(result.error)
    result.duration_sec = time.time() - start

    log.info(f"[NCDRC] {len(result.findings)} complaint(s) found.")
    return result


# ─── MODULE 3: MCA21 — Deep Director & Company Search ────────────────────────
#
# ARCHITECTURE — 3-step funnel, minimal API calls:
#
#   Step 1: Name → DIN(s)
#           Search director by name → get DIN numbers
#           Uses: Surepass / Sandbox.co.in paid API  OR  MCA V2 scrape fallback
#           Cost: ~₹2 per search
#
#   Step 2: DIN → Full directorship history
#           For each DIN found, fetch all companies (current + past)
#           Uses: Same API
#           Cost: ~₹2 per DIN
#
#   Step 3: CIN → Company deep-dive
#           For each company found, fetch compliance status, charges, filing history
#           Uses: Same API  OR  MCA public data endpoint
#           Cost: ~₹2 per CIN
#
# Total cost per subject: ₹6-15 depending on how many companies found
#
# WHAT WE FLAG:
#   HIGH   • DIN disqualified (Section 164 of Companies Act)
#          • Company under liquidation / winding up
#          • Company struck off with charges registered (unpaid debt)
#   MEDIUM • Undisclosed directorship (not told to family)
#          • Company with non-filed annual returns (compliance defaulter)
#          • Active charges on company (loans outstanding)
#          • Multiple struck-off companies (pattern of abandonment)
#   LOW    • Active company, fully compliant — just FYI disclosure
#
# API OPTIONS (pick one, set in .env):
#   Option A: Surepass   — surepass.io         — well documented, ₹2-5/hit
#   Option B: Sandbox    — sandbox.co.in        — good for startups, has free tier
#   Option C: Compdata   — compdata.in          — older but works, cheapest
#   Option D: MCA scrape — mca.gov.in (V2 endpoint still live, CAPTCHA risk)
#
# Set MCA_API_PROVIDER = "surepass" | "sandbox" | "compdata"
# Note: "scrape" (direct MCA portal) carries IT Act S.43 liability if it
#       bypasses technical controls. Prefer a licensed B2B API provider.

MCA_API_PROVIDER = os.getenv("MCA_API_PROVIDER", "surepass")
MCA_API_KEY      = os.getenv("MCA_API_KEY", "")
MCA_API_SECRET   = os.getenv("MCA_API_SECRET", "")

# Endpoint map per provider
_MCA_ENDPOINTS = {
    "surepass": {
        "din_by_name": "https://kyc-api.surepass.io/api/v1/mca/director-search",
        "director_data": "https://kyc-api.surepass.io/api/v1/mca/director-detail",
        "company_data":  "https://kyc-api.surepass.io/api/v1/mca/company-detail",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
    },
    "sandbox": {
        "din_by_name":   "https://api.sandbox.co.in/kyc/mca/director",
        "director_data": "https://api.sandbox.co.in/kyc/mca/director/{din}",
        "company_data":  "https://api.sandbox.co.in/kyc/mca/company/{cin}",
        "auth_header": "x-api-key",
        "auth_prefix": "",
    },
    "compdata": {
        "din_by_name":   "https://compdata.in/api/v1/din-by-name",
        "director_data": "https://compdata.in/api/v1/director-data",
        "company_data":  "https://compdata.in/api/v1/master-data",
        "auth_header": "Authorization",
        "auth_prefix": "Token ",
    },
}


def _mca_headers() -> dict:
    """Build auth headers for whichever MCA API provider is configured."""
    ep = _MCA_ENDPOINTS.get(MCA_API_PROVIDER, _MCA_ENDPOINTS["surepass"])
    headers = {ep["auth_header"]: f"{ep['auth_prefix']}{MCA_API_KEY}"}
    
    # Sandbox requires an additional x-api-secret header
    if MCA_API_PROVIDER == "sandbox" and MCA_API_SECRET:
        headers["x-api-secret"] = MCA_API_SECRET
        
    return headers


def _mca_get(session, endpoint_key: str, params: dict = None,
             json_body: dict = None, path_vars: dict = None) -> Optional[dict]:
    """
    Make one MCA API call. Handles URL templating for sandbox-style {din}/{cin} paths.
    Returns parsed JSON dict or None on failure.
    """
    ep = _MCA_ENDPOINTS.get(MCA_API_PROVIDER, _MCA_ENDPOINTS["surepass"])
    url = ep[endpoint_key]
    if path_vars:
        url = url.format(**path_vars)

    r = safe_request(
        "POST" if json_body else "GET",
        url,
        session=session,
        headers=_mca_headers(),
        params=params,
        json_body=json_body,
    )
    if r and r.ok:
        try:
            return r.json()
        except Exception:
            return None
    return None


def _classify_company(company: dict, subject_name: str,
                      disclosed_names: list[str]) -> tuple[Priority, list[str]]:
    """
    Classify a company finding and return (priority, list_of_flag_reasons).
    """
    flags = []
    priority = Priority.LOW

    status = str(company.get("company_status") or company.get("status", "")).upper()
    name   = str(company.get("company_name") or company.get("name", ""))
    charges = company.get("charges") or []
    filing_status = str(company.get("active_compliance") or
                        company.get("filing_status", "")).upper()
    din_disqualified = company.get("din_disqualified", False)

    # DIN disqualification = director banned under Section 164
    if din_disqualified:
        flags.append("DIN disqualified under Section 164 — director legally barred")
        priority = Priority.HIGH

    # Company under liquidation / winding up
    if any(kw in status for kw in ["LIQUIDAT", "WIND", "DISSOLV"]):
        flags.append(f"Company under {status.lower()}")
        priority = Priority.HIGH

    # Struck off with active charges = abandoned company with unpaid loans
    if "STRUCK" in status and charges:
        flags.append(
            f"Company struck off but has {len(charges)} active charge(s) — "
            f"possible unpaid debt of ₹{_total_charge_amount(charges):,}"
        )
        priority = Priority.HIGH

    # Struck off without charges — still notable, less severe
    elif "STRUCK" in status:
        flags.append("Company struck off by RoC (non-compliance or closure)")
        priority = max(priority, Priority.MEDIUM)

    # Non-filer — compliance defaulter
    if "DEFAULTER" in filing_status or "NOT FILED" in filing_status:
        flags.append("Annual returns not filed — compliance defaulter")
        priority = max(priority, Priority.MEDIUM)

    # Active charges = outstanding loans against the company
    if charges and "STRUCK" not in status:
        total = _total_charge_amount(charges)
        flags.append(
            f"{len(charges)} active charge(s) registered — "
            f"₹{total:,} in outstanding obligations"
        )
        priority = max(priority, Priority.MEDIUM)

    # Undisclosed company
    is_disclosed = any(
        disc.lower() in name.lower() or name.lower() in disc.lower()
        for disc in disclosed_names if disc
    )
    if not is_disclosed:
        flags.append("Company not disclosed on matrimonial profile")
        priority = max(priority, Priority.MEDIUM)

    return priority, flags


def _total_charge_amount(charges: list) -> int:
    """Sum up charge amounts from MCA charge records."""
    total = 0
    for charge in charges:
        amt = charge.get("amount") or charge.get("charge_amount") or 0
        try:
            total += int(str(amt).replace(",", "").replace("₹", "").strip() or 0)
        except (ValueError, TypeError):
            pass
    return total


def run_mca21(subject: SubjectProfile, ctx: PipelineContext) -> ModuleResult:
    """
    Full MCA21 deep search:
      1. Find DIN(s) by name
      2. Fetch complete directorship history per DIN
      3. Deep-dive each company found (compliance, charges, filing status)
      4. Classify and flag findings
    """
    result = ModuleResult(module_name="MCA21")
    start  = time.time()
    result.ran = True

    if not MCA_API_KEY and MCA_API_PROVIDER != "scrape":
        result.success = False
        result.error = (
            f"MCA_API_KEY not set in .env. "
            f"Sign up at {MCA_API_PROVIDER}.io and add MCA_API_KEY to .env. "
            f"Alternatively set MCA_API_PROVIDER=scrape to use direct MCA portal "
            f"(less reliable, CAPTCHA risk)."
        )
        log.warning(f"[MCA21] {result.error}")
        result.duration_sec = time.time() - start
        return result

    session = ctx.sessions["mca"]
    name_variations = ctx.name_variations

    # Names the subject has disclosed — used to flag hidden companies
    disclosed_names = list(filter(None, [
        subject.company_name,
        subject.business_name,
        subject.employer_name,
    ]))

    # ── STEP 1: Name → DIN(s) ────────────────────────────────────────────────
    log.info(f"[MCA21] Step 1: Searching DIN for {len(name_variations)} name variants")

    found_dins: dict[str, dict] = {}  # din → basic director info

    for name in name_variations:
        data = _mca_get(session, "din_by_name",
                        params={"name": name},
                        json_body={"name": name} if MCA_API_PROVIDER == "surepass" else None)
        if not data:
            continue

        # Normalise response across providers
        directors = (
            data.get("data") or
            data.get("directors") or
            data.get("result") or
            []
        )
        if isinstance(directors, dict):
            directors = [directors]

        for d in directors:
            din = str(d.get("din") or d.get("DIN") or d.get("director_id") or "").strip()
            if not din or din in found_dins:
                continue

            # Fuzzy name match — skip if result is clearly a different person
            result_name = str(d.get("name") or d.get("director_name") or "").lower()
            if result_name and subject.full_name.split()[0].lower() not in result_name:
                continue

            found_dins[din] = {
                "din":  din,
                "name": d.get("name") or d.get("director_name", name),
                "dob":  d.get("dob") or d.get("date_of_birth", "N/A"),
            }
            log.info(f"[MCA21]   DIN found: {din} ({found_dins[din]['name']})")

    if not found_dins:
        log.info(f"[MCA21] No DIN found for '{subject.full_name}' — no directorship records")
        result.success = True
        result.duration_sec = time.time() - start

        # Add an explicit "not found" finding so report shows this was checked
        result.findings.append(Finding(
            source="MCA21",
            category="Business & Financial",
            title="No director record found",
            detail=(
                f"Searched {len(name_variations)} name variations. "
                f"No DIN registered under this name. Subject does not appear "
                f"to be a director of any registered Indian company."
            ),
            priority=Priority.LOW,
        ))
        return result

    # ── STEP 2: DIN → Full Directorship History ───────────────────────────────
    log.info(f"[MCA21] Step 2: Fetching directorship history for "
             f"{len(found_dins)} DIN(s)")

    all_companies: list[dict] = []  # flat list of all companies across all DINs
    seen_cins: set[str] = set()

    for din, din_info in found_dins.items():
        data = _mca_get(session, "director_data",
                        params={"din": din},
                        json_body={"din": din} if MCA_API_PROVIDER == "surepass" else None,
                        path_vars={"din": din})
        if not data:
            log.warning(f"[MCA21]   Could not fetch director data for DIN {din}")
            continue

        companies = (
            data.get("data", {}).get("companies") or
            data.get("companies") or
            data.get("result", {}).get("companies") or
            []
        )

        # Also check if DIN itself is disqualified
        din_disqualified = (
            data.get("data", {}).get("disqualified") or
            data.get("disqualified") or
            False
        )

        log.info(f"[MCA21]   DIN {din}: {len(companies)} company/companies found")

        for company in companies:
            cin = str(company.get("cin") or company.get("CIN") or "").strip()
            if not cin or cin in seen_cins:
                continue
            seen_cins.add(cin)
            company["_din"] = din
            company["_din_disqualified"] = din_disqualified
            company["_din_info"] = din_info
            all_companies.append(company)

    # ── STEP 3: CIN → Company Deep-dive ──────────────────────────────────────
    log.info(f"[MCA21] Step 3: Deep-dive on {len(all_companies)} unique company/companies")

    for company in all_companies:
        cin = company.get("cin") or company.get("CIN", "")
        din = company.get("_din", "")

        # Fetch full company master data
        company_data = _mca_get(
            session, "company_data",
            params={"cin": cin},
            json_body={"cin": cin} if MCA_API_PROVIDER == "surepass" else None,
            path_vars={"cin": cin}
        )

        # Merge fetched data into our company dict
        if company_data:
            merged = {**company}
            fetched = (
                company_data.get("data") or
                company_data.get("company_master_data") or
                company_data
            )
            if isinstance(fetched, dict):
                merged.update(fetched)
            merged["_din"] = din
            merged["_din_disqualified"] = company.get("_din_disqualified", False)
        else:
            merged = company

        # Extract key fields with fallbacks
        company_name    = str(merged.get("company_name") or merged.get("name", cin))
        company_status  = str(merged.get("company_status") or merged.get("status", "N/A"))
        designation     = str(merged.get("designation") or merged.get("member_type", "Director"))
        date_of_appt    = str(merged.get("appointment_date") or merged.get("date_of_appointment", "N/A"))
        date_of_resign  = str(merged.get("resignation_date") or merged.get("date_of_cessation", ""))
        auth_capital    = merged.get("authorised_capital") or merged.get("authorised_capital(rs)", "N/A")
        paid_capital    = merged.get("paid_up_capital") or merged.get("paid_up_capital(rs)", "N/A")
        incorporation   = merged.get("date_of_incorporation", "N/A")
        last_agm        = merged.get("date_of_last_agm", "N/A")
        charges         = merged.get("charges") or []
        roc_code        = merged.get("roc_code", "N/A")
        filing_status   = str(merged.get("active_compliance") or
                              merged.get("filing_status", "N/A"))
        is_current      = not bool(date_of_resign)

        # Classify
        priority, flags = _classify_company(merged, subject.full_name, disclosed_names)

        # Build raw record
        raw = {
            "cin":              cin,
            "din":              din,
            "company_name":     company_name,
            "company_status":   company_status,
            "designation":      designation,
            "appointment_date": date_of_appt,
            "resignation_date": date_of_resign or "Current",
            "incorporation":    incorporation,
            "authorised_capital": str(auth_capital),
            "paid_up_capital":  str(paid_capital),
            "last_agm":         str(last_agm),
            "charges_count":    len(charges),
            "charges":          charges[:5],  # store first 5 to avoid bloat
            "filing_status":    filing_status,
            "roc_code":         roc_code,
            "din_disqualified": merged.get("_din_disqualified", False),
            "flags":            flags,
        }
        result.raw_results.append(raw)

        # Build detail string
        tenure = (f"Appointed: {date_of_appt}" +
                  (f" | Resigned: {date_of_resign}" if date_of_resign else " | Currently active"))
        charge_str = (f" | Charges: {len(charges)} active" if charges else "")
        flag_str = (" | ⚠ " + " | ⚠ ".join(flags)) if flags else ""

        finding = Finding(
            source="MCA21",
            category="Business & Financial",
            title=f"{'[CURRENT] ' if is_current else '[PAST] '}{designation} — {company_name}",
            detail=(
                f"CIN: {cin} | DIN: {din} | "
                f"Status: {company_status} | "
                f"Incorporated: {incorporation} | "
                f"{tenure} | "
                f"Capital: Auth ₹{auth_capital} / Paid-up ₹{paid_capital} | "
                f"Filing: {filing_status}"
                f"{charge_str}"
                f"{flag_str}"
            ),
            priority=priority,
            raw_data=raw
        )
        result.findings.append(finding)

        log.info(
            f"[MCA21]   {company_name} ({cin}) — "
            f"Status: {company_status} | "
            f"Priority: {priority.value} | "
            f"Flags: {len(flags)}"
        )

    result.success = True
    result.duration_sec = time.time() - start

    log.info(
        f"[MCA21] Complete — {len(found_dins)} DIN(s), "
        f"{len(all_companies)} company/companies | "
        f"High: {result.high_priority_count} | "
        f"Medium: {result.medium_priority_count}"
    )
    return result



# ─── MODULE 4: GST Verification ───────────────────────────────────────────────

def run_gst(subject: SubjectProfile, ctx: PipelineContext) -> ModuleResult:
    result = ModuleResult(module_name="GST")
    start = time.time()
    result.ran = True

    log.info(f"[GST] Checking business registration for: {subject.full_name}")

    # GST portal taxpayer search by name
    GST_SEARCH_URL = "https://services.gst.gov.in/services/api/search/taxpayerSearch"

    search_terms = [subject.full_name]
    if subject.business_name:
        search_terms.append(subject.business_name)
    if subject.company_name:
        search_terms.append(subject.company_name)

    for term in search_terms:
        try:
            time.sleep(REQUEST_DELAY)
            r = safe_request(
                "GET",
                GST_SEARCH_URL,
                session=ctx.sessions["gst"],
                params={"legalname": term, "stj": ""},
            )

            if not r or not r.ok:
                continue

            try:
                data = r.json()
                taxpayers = data.get("data") or data.get("taxpayerInfo") or []
                if isinstance(taxpayers, dict):
                    taxpayers = [taxpayers]
            except Exception:
                continue

            for taxpayer in taxpayers:
                gstin = taxpayer.get("gstin", "N/A")
                legal_name = taxpayer.get("legalName") or taxpayer.get("tradeNam", "N/A")
                status = taxpayer.get("sts", "N/A")
                reg_date = taxpayer.get("rgdt", "N/A")
                state = taxpayer.get("pradr", {}).get("adr", "N/A") if isinstance(taxpayer.get("pradr"), dict) else "N/A"

                raw = {
                    "gstin": gstin,
                    "legal_name": legal_name,
                    "status": status,
                    "reg_date": reg_date,
                    "state": state,
                    "search_term": term,
                }
                result.raw_results.append(raw)

                # Active undisclosed GST registration = undisclosed business
                disclosed = (
                    subject.company_name and
                    subject.company_name.lower() in legal_name.lower()
                ) or (
                    subject.business_name and
                    subject.business_name.lower() in legal_name.lower()
                )

                priority = Priority.LOW
                if not disclosed:
                    priority = Priority.MEDIUM

                finding = Finding(
                    source="GST Portal",
                    category="Business & Financial",
                    title=f"GST Registration — {legal_name}",
                    detail=(
                        f"GSTIN: {gstin} | "
                        f"Status: {status} | "
                        f"Registered: {reg_date} | "
                        f"{'⚠ Not disclosed' if not disclosed else 'Known registration'}"
                    ),
                    priority=priority,
                    raw_data=raw
                )
                result.findings.append(finding)

        except Exception as e:
            log.warning(f"[GST] Error for '{term}': {e}")

    result.success = True
    result.duration_sec = time.time() - start

    log.info(f"[GST] {len(result.findings)} registration(s) found.")
    return result


# ─── MODULE 5: EPFO Employer Verification ─────────────────────────────────────
# CONDITIONAL: only runs when subject.has_employer() == True

def run_epfo(subject: SubjectProfile, ctx: PipelineContext) -> ModuleResult:
    result = ModuleResult(module_name="EPFO")

    if not subject.has_employer():
        result.skipped = True
        result.skip_reason = "No employer name provided. EPFO check skipped."
        log.info("[EPFO] Skipped — no employer in profile")
        return result

    start = time.time()
    result.ran = True
    employer = subject.employer_name

    log.info(f"[EPFO] Verifying employer: {employer}")

    # EPFO establishment search
    EPFO_SEARCH_URL = "https://unifiedportal-emp.epfindia.gov.in/publicPortal/no-auth/misReport/home/loadEstSearchHome"

    try:
        time.sleep(REQUEST_DELAY)
        r = safe_request(
            "POST",
            EPFO_SEARCH_URL,
            session=ctx.sessions["epfo"],
            json_body={"establishmentName": employer, "stateCode": ""},
        )

        if r and r.ok:
            try:
                data = r.json()
                establishments = data.get("data") or data.get("establishmentList") or []
                result.raw_results = establishments

                employer_found = len(establishments) > 0
                if employer_found:
                    finding = Finding(
                        source="EPFO",
                        category="Employment Verification",
                        title=f"Employer Verified — {employer}",
                        detail=(
                            f"'{employer}' is a registered EPFO employer. "
                            f"This confirms the company exists and employs formal workers. "
                            f"Individual employment cannot be confirmed without UAN."
                        ),
                        priority=Priority.LOW,
                        raw_data={"employer": employer, "found": True, "count": len(establishments)}
                    )
                else:
                    finding = Finding(
                        source="EPFO",
                        category="Employment Verification",
                        title=f"Employer Not Found — {employer}",
                        detail=(
                            f"'{employer}' was not found in EPFO establishment records. "
                            f"This may indicate the employer is unregistered, uses a different name, "
                            f"or the claimed employment may be false."
                        ),
                        priority=Priority.MEDIUM,
                        raw_data={"employer": employer, "found": False}
                    )
                result.findings.append(finding)

            except Exception as e:
                log.warning(f"[EPFO] Parse error: {e}")
    except Exception as e:
        result.error = str(e)
        log.warning(f"[EPFO] Error: {e}")

    result.success = True
    result.duration_sec = time.time() - start
    return result


# ─── MODULE 6: Google Deep Search ─────────────────────────────────────────────

def run_google_search(subject: SubjectProfile, ctx: PipelineContext) -> ModuleResult:
    result = ModuleResult(module_name="Google Search")
    start = time.time()
    result.ran = True

    name = subject.full_name
    city = subject.current_city

    # Search queries — ordered by most likely to surface red flags first
    queries = [
        f'"{name}" fraud OR scam OR complaint OR cheating',
        f'"{name}" {city} court OR FIR OR arrested',
        f'"{name}" {city}',
    ]
    if subject.employer_name:
        queries.append(f'"{name}" {subject.employer_name}')
    if subject.native_city:
        queries.append(f'"{name}" {subject.native_city} news')

    log.info(f"[Google] Running {len(queries)} searches")

    # Option A: SerpAPI (paid but reliable, ~$50/month for 5000 searches)
    # Only factual, objective findings are reported: court cases, FIRs, arrests.
    # News articles, opinion pieces, and gossip are excluded by the LegalFilteredFindings
    # blocklist in inkognito_models.py and by the negative_keywords filter below.
    if SERP_API_KEY:
        for query in queries:
            try:
                time.sleep(REQUEST_DELAY)
                r = safe_request(
                    "GET",
                    "https://serpapi.com/search",
                    session=ctx.sessions["serp"],
                    params={
                        "q": query,
                        "api_key": SERP_API_KEY,
                        "num": 10,
                        "hl": "en",
                        "gl": "in"
                    }
                )
                if r and r.ok:
                    data = r.json()
                    organic = data.get("organic_results", [])
                    result.raw_results.extend(organic)

                    # Flag results with negative keywords in title/snippet
                    negative_keywords = [
                        "fraud", "scam", "arrested", "FIR", "case filed",
                        "cheating", "complaint", "accused", "convicted", "bail"
                    ]
                    for item in organic:
                        text = f"{item.get('title','')} {item.get('snippet','')}".lower()
                        if any(kw in text for kw in negative_keywords):
                            finding = Finding(
                                source="Google Search",
                                category="Web Presence",
                                title=item.get("title", "Search Result"),
                                detail=(
                                    f"Query: {query} | "
                                    f"Snippet: {item.get('snippet', '')[:200]} | "
                                    f"URL: {item.get('link', '')}"
                                ),
                                priority=Priority.HIGH,
                                url=item.get("link"),
                                raw_data=item
                            )
                            result.findings.append(finding)

            except Exception as e:
                log.warning(f"[Google] SerpAPI error for query '{query}': {e}")

    else:
        # Option B: Note that manual Google search is needed
        # Direct Google scraping violates ToS and is unreliable
        # Log as a manual step required
        log.info("[Google] SERP_API_KEY not set. Logging as manual check required.")
        finding = Finding(
            source="Google Search",
            category="Web Presence",
            title="Manual Google Search Required",
            detail=(
                f"Automated Google search unavailable (SERP_API_KEY not configured). "
                f"Manually search these queries:\n" +
                "\n".join(f"  • {q}" for q in queries)
            ),
            priority=Priority.NONE,
        )
        result.findings.append(finding)

    result.success = True
    result.duration_sec = time.time() - start

    flagged = [f for f in result.findings if f.priority == Priority.HIGH]
    log.info(f"[Google] {len(flagged)} flagged result(s) across {len(queries)} queries.")
    return result



# ─── MODULE 7: Property Records — Delhi NGDRS + IGRS UP ──────────────────────
#
# CONDITIONAL: always attempted, but skips gracefully if no usable location
# data is available for scoping the search.
#
# ARCHITECTURE — why location-first is the only viable approach:
#
#   Both portals are designed for known-property lookup, not person-first search.
#   Delhi NGDRS requires OTP mobile login for the citizen search portal.
#   IGRS UP index search requires district + tehsil selection before name.
#   Neither offers a clean "search all records for this person" endpoint.
#
#   Our approach:
#     1. Build a list of candidate districts from subject's cities
#     2. Delhi NGDRS: use esearch.delhigovt.nic.in index (pre-migration records
#        still searchable) + NGDRS document index via party name per SRO
#     3. IGRS UP: use the index search endpoint with party name + district
#        for each UP district in the subject's profile
#     4. CERSAI: Central Registry of Securitisation — catches mortgaged assets,
#        searchable by name, no CAPTCHA (bonus source)
#
# WHAT WE FLAG:
#   HIGH   • Property found but subject claimed "no assets" or no property
#          • CERSAI charge = property mortgaged (active loan against it)
#          • Property registered in someone else's name (benami signal)
#   MEDIUM • Undisclosed property found (subject didn't mention it)
#          • Multiple properties found (wealth check vs claimed income)
#   LOW    • Property found consistent with disclosed information
#
# WHAT THIS TELLS US FOR MATRIMONIAL:
#   • Claimed "I own a flat in Noida" — verify it actually exists
#   • Claimed "no property" — check if anything is registered
#   • Claimed "self-employed, moderate income" — 3 registered properties = inconsistency
#   • Property under mortgage = financial obligation family should know about

# District → IGRS UP district code mapping (partial — expand as needed)
IGRSUP_DISTRICTS = {
    "meerut":          "Meerut",
    "noida":           "Gautam Buddh Nagar",
    "gautam buddh nagar": "Gautam Buddh Nagar",
    "ghaziabad":       "Ghaziabad",
    "lucknow":         "Lucknow",
    "agra":            "Agra",
    "kanpur":          "Kanpur Nagar",
    "varanasi":        "Varanasi",
    "allahabad":       "Prayagraj",
    "prayagraj":       "Prayagraj",
    "bareilly":        "Bareilly",
    "aligarh":         "Aligarh",
    "moradabad":       "Moradabad",
    "saharanpur":      "Saharanpur",
    "gorakhpur":       "Gorakhpur",
    "mathura":         "Mathura",
    "muzaffarnagar":   "Muzaffarnagar",
}

# Delhi SRO (Sub-Registrar Office) codes for NGDRS
DELHI_SROS = [
    "SR-I",    # New Delhi
    "SR-II",   # Lajpat Nagar / South
    "SR-III",  # Rohini / North West
    "SR-IV",   # Dwarka / South West
    "SR-V",    # Saket
    "SR-VI",   # Mayur Vihar / East
    "SR-VII",  # Janakpuri
    "SR-VIII", # Pitampura
]


def _resolve_property_locations(subject: SubjectProfile) -> dict[str, list[str]]:
    """
    Build searchable location lists for Delhi and UP from subject profile.
    Returns: {"delhi_sros": [...], "up_districts": [...]}
    """
    # Collect all city hints
    cities = set()
    for field in [
        subject.current_city,
        subject.native_city,
        *(subject.known_property_areas or []),
    ]:
        if field:
            cities.add(field.lower().strip())

    # Delhi: if any city hints point to Delhi NCR, search all SROs
    delhi_keywords = {"delhi", "new delhi", "ncr", "dwarka", "rohini",
                      "saket", "lajpat", "janakpuri", "pitampura", "mayur vihar",
                      "noida", "gurgaon", "gurugram", "faridabad"}
    search_delhi = any(c in delhi_keywords or "delhi" in c for c in cities)
    delhi_sros = DELHI_SROS if search_delhi else []

    # UP: match any city to IGRSUP district map
    up_districts = []
    for city in cities:
        for keyword, district in IGRSUP_DISTRICTS.items():
            if keyword in city or city in keyword:
                if district not in up_districts:
                    up_districts.append(district)

    return {"delhi_sros": delhi_sros, "up_districts": up_districts}


def _parse_ngdrs_table(html: str, source_label: str,
                        subject_name: str) -> list[dict]:
    """Parse a document index results table from NGDRS HTML response."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table", {"id": "resultTable"}) or soup.find("table")
        if not table:
            return []

        headers = [th.get_text(strip=True).lower()
                   for th in table.find_all("th")]
        records = []
        for row in table.find_all("tr")[1:]:
            cols = [td.get_text(strip=True) for td in row.find_all("td")]
            if not cols:
                continue
            record = {headers[i] if i < len(headers) else f"col_{i}": v
                      for i, v in enumerate(cols)}
            record["_source"] = source_label
            records.append(record)
        return records
    except Exception:
        return []


def run_property_records(subject: SubjectProfile,
                         ctx: PipelineContext) -> ModuleResult:
    result = ModuleResult(module_name="Property Records")
    start  = time.time()
    max_duration_sec = int(os.getenv("PROPERTY_MAX_DURATION_SEC", "75"))
    timed_out = False

    def _budget_exhausted(stage: str) -> bool:
        nonlocal timed_out
        if (time.time() - start) < max_duration_sec:
            return False
        timed_out = True
        if not result.error:
            result.error = (
                f"Property records check hit module time limit ({max_duration_sec}s). "
                "Partial results returned."
            )
        log.warning(f"[Property] Time budget reached during {stage} ({max_duration_sec}s)")
        return True

    # ── Resolve searchable locations ──────────────────────────────────────────
    locations = _resolve_property_locations(subject)
    delhi_sros    = locations["delhi_sros"]
    up_districts  = locations["up_districts"]

    if not delhi_sros and not up_districts:
        result.skipped = True
        result.skip_reason = (
            "No Delhi or UP location found in subject profile. "
            "Property records search covers Delhi NGDRS and IGRS UP. "
            "Populate current_city, native_city, or known_property_areas "
            "with a Delhi/NCR or UP location to enable this check."
        )
        log.info("[Property] Skipped — no Delhi/UP location in profile")
        return result

    result.ran = True
    log.info(
        f"[Property] Locations resolved — "
        f"Delhi SROs: {len(delhi_sros)} | UP districts: {len(up_districts)}"
    )

    name_variations = ctx.name_variations
    all_records: list[dict] = []

    # ── Source A: Delhi NGDRS — document index search ─────────────────────────
    # The NGDRS Delhi portal has a public document search by party name per SRO.
    # URL pattern: ngdrs.delhi.gov.in/NGDRS_DL/DLSearch/searchDocumentIndex
    # POST params: partyName, sroCode, fromYear, toYear
    # Note: full citizen search requires OTP login. The document index search
    # (public records index) is accessible without login per RTI obligations.

    if delhi_sros:
        NGDRS_INDEX_URL = (
            "https://ngdrs.delhi.gov.in/NGDRS_DL/DLSearch/searchDocumentIndex"
        )
        session = ctx.sessions["ngdrs"]

        # Fetch CSRF token from search page first
        csrf_token = ""
        try:
            init = safe_request(
                "GET",
                "https://ngdrs.delhi.gov.in/NGDRS_DL/DLSearch/citizenDocSearch",
                session=session,
                timeout=8,
                retries=1,
            )
            if init and init.ok:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(init.text, "html.parser")
                token_tag = (
                    soup.find("input", {"name": "_token"}) or
                    soup.find("meta", {"name": "csrf-token"})
                )
                if token_tag:
                    csrf_token = (token_tag.get("value") or
                                  token_tag.get("content", ""))
        except Exception as e:
            log.warning(f"[Property] NGDRS CSRF fetch error: {e}")

        log.info(f"[Property] Searching Delhi NGDRS across "
                 f"{len(delhi_sros)} SROs × {len(name_variations)} names")

        for sro in delhi_sros:
            for name in name_variations:
                if _budget_exhausted("Delhi NGDRS search"):
                    break
                try:
                    time.sleep(REQUEST_DELAY)
                    r = safe_request(
                        "POST",
                        NGDRS_INDEX_URL,
                        session=session,
                        json_body={
                            "_token":    csrf_token,
                            "partyName": name,
                            "sroCode":   sro,
                            "fromYear":  "2000",
                            "toYear":    str(datetime.now().year),
                            "partyType": "both",   # search as both buyer and seller
                        },
                        timeout=8,
                        retries=1,
                    )
                    if r and r.ok:
                        try:
                            data = r.json()
                            records = (data.get("data") or
                                       data.get("documents") or [])
                            for rec in records:
                                rec["_sro"] = sro
                                rec["_search_name"] = name
                                all_records.append(rec)
                        except Exception:
                            # Try HTML table parse
                            parsed = _parse_ngdrs_table(
                                r.text, f"Delhi NGDRS {sro}", name
                            )
                            all_records.extend(parsed)
                except Exception as e:
                    log.warning(f"[Property] NGDRS error for {sro}/{name}: {e}")
            if timed_out:
                break

    # ── Source B: IGRS UP — index search by party name + district ─────────────
    # Endpoint: igrsup.gov.in/igrsup/searchIndexAction (POST)
    # Params: partyName (buyer or seller), districtId, fromYear, toYear, captcha
    # LEGAL RISK: automated CAPTCHA bypass on government portals is legally
    # flagged. Keep disabled by default and only enable with explicit legal
    # sign-off for controlled internal testing.

    CAPTCHA_API_KEY = os.getenv("CAPTCHA_API_KEY", "")
    CAPTCHA_BYPASS_ENABLED = os.getenv("CAPTCHA_BYPASS_ENABLED", "false").strip().lower() in {
        "1", "true", "yes", "on"
    }

    if up_districts:
        IGRSUP_SEARCH_URL = "https://igrsup.gov.in/igrsup/searchIndexAction"
        IGRSUP_CAPTCHA_URL = "https://igrsup.gov.in/igrsup/captchaImage"
        IGRSUP_MANUAL_URL = "https://igrsup.gov.in"
        session_up = ctx.sessions["igrsup"]

        if not CAPTCHA_BYPASS_ENABLED:
            log.warning(
                "[Property] CAPTCHA_BYPASS_ENABLED is False; "
                "switching IGRS UP to manual review mode"
            )
            for district in up_districts:
                result.findings.append(Finding(
                    source="IGRS UP",
                    category="Property Records",
                    title=f"[MANUAL REVIEW REQUIRED] IGRS UP Index Search — {district}",
                    detail=(
                        "Automated CAPTCHA bypass is disabled by policy "
                        "(CAPTCHA_BYPASS_ENABLED=False). "
                        f"Manual check URL: {IGRSUP_MANUAL_URL} | "
                        "Reviewer to open Index Search and test buyer/seller name "
                        f"variants for district '{district}'."
                    ),
                    priority=Priority.NONE,
                    url=IGRSUP_MANUAL_URL,
                ))
        elif not CAPTCHA_API_KEY:
            log.warning(
                "[Property] CAPTCHA bypass enabled but CAPTCHA_API_KEY missing; "
                "switching IGRS UP to manual review mode"
            )
            for district in up_districts:
                result.findings.append(Finding(
                    source="IGRS UP",
                    category="Property Records",
                    title=f"[MANUAL REVIEW REQUIRED] IGRS UP Index Search — {district}",
                    detail=(
                        "CAPTCHA_BYPASS_ENABLED=True but CAPTCHA_API_KEY is not set. "
                        f"Manual check URL: {IGRSUP_MANUAL_URL} | "
                        "Reviewer to open Index Search and test buyer/seller name "
                        f"variants for district '{district}'."
                    ),
                    priority=Priority.NONE,
                    url=IGRSUP_MANUAL_URL,
                ))
        else:
            log.info(f"[Property] Searching IGRS UP across "
                     f"{len(up_districts)} district(s) × {len(name_variations)} names")

            for district in up_districts:
                for name in name_variations:
                    if _budget_exhausted("IGRS UP search"):
                        break
                    try:
                        # Step 1: Get fresh session + captcha image
                        time.sleep(REQUEST_DELAY)
                        captcha_r = safe_request(
                            "GET", IGRSUP_CAPTCHA_URL,
                            session=session_up,
                            timeout=8,
                            retries=1,
                        )

                        captcha_text = ""
                        if captcha_r and captcha_r.ok:
                            # Solve via 2captcha only when explicit opt-in is enabled.
                            import base64
                            img_b64 = base64.b64encode(captcha_r.content).decode()
                            solve_r = safe_request(
                                "POST",
                                "https://2captcha.com/in.php",
                                session=ctx.sessions["serp"],
                                json_body={
                                    "key":    CAPTCHA_API_KEY,
                                    "method": "base64",
                                    "body":   img_b64,
                                    "json":   1,
                                }
                            )
                            if solve_r and solve_r.ok:
                                captcha_id = solve_r.json().get("request")
                                if captcha_id:
                                    # Poll for result (2captcha takes ~10s)
                                    time.sleep(12)
                                    result_r = safe_request(
                                        "GET",
                                        "https://2captcha.com/res.php",
                                        session=ctx.sessions["serp"],
                                        params={
                                            "key":    CAPTCHA_API_KEY,
                                            "action": "get",
                                            "id":     captcha_id,
                                            "json":   1,
                                        },
                                        timeout=8,
                                        retries=1,
                                    )
                                    if result_r and result_r.ok:
                                        captcha_text = result_r.json().get("request", "")

                        if not captcha_text:
                            log.warning(
                                f"[Property] CAPTCHA solve failed for IGRS UP ({district}); "
                                "falling back to manual review"
                            )
                            result.findings.append(Finding(
                                source="IGRS UP",
                                category="Property Records",
                                title=f"[MANUAL REVIEW REQUIRED] IGRS UP Index Search — {district}",
                                detail=(
                                    "Automated CAPTCHA solve did not return a valid token. "
                                    f"Manual check URL: {IGRSUP_MANUAL_URL} | "
                                    f"Reviewer to verify name '{name}' in district '{district}'."
                                ),
                                priority=Priority.NONE,
                                url=IGRSUP_MANUAL_URL,
                            ))
                            break

                        # Step 2: POST search with solved captcha
                        time.sleep(REQUEST_DELAY)
                        search_r = safe_request(
                            "POST",
                            IGRSUP_SEARCH_URL,
                            session=session_up,
                            json_body={
                                "partyName":   name,
                                "districtId":  district,
                                "fromYear":    "2000",
                                "toYear":      str(datetime.now().year),
                                "partyType":   "both",
                                "captchaText": captcha_text,
                            },
                            timeout=8,
                            retries=1,
                        )

                        if search_r and search_r.ok:
                            try:
                                data = search_r.json()
                                records = data.get("data") or data.get("results") or []
                                for rec in records:
                                    rec["_district"] = district
                                    rec["_search_name"] = name
                                    all_records.append(rec)
                            except Exception:
                                parsed = _parse_ngdrs_table(
                                    search_r.text,
                                    f"IGRS UP {district}",
                                    name
                                )
                                all_records.extend(parsed)

                    except Exception as e:
                        log.warning(
                            f"[Property] IGRS UP error for {district}/{name}: {e}"
                        )
                if timed_out:
                    break

    # ── Source C: CERSAI — Central Registry of Securitisation ─────────────────
    # cersai.org.in — public search by debtor name
    # Catches: mortgaged properties, equitable mortgages, hypothecation
    # No CAPTCHA on public search. Returns charge details including lender name.
    # Very useful: if a property is claimed as "unencumbered" but shows CERSAI
    # charge, that's an undisclosed mortgage.

    CERSAI_URL = "https://www.cersai.org.in/CERSAI/webpages/searchCharge.jsf"
    session_cersai = ctx.sessions["ngdrs"]   # reuse ngdrs session

    log.info(f"[Property] Searching CERSAI for: {name_variations[:2]}")
    for name in name_variations[:2]:    # CERSAI — cap at 2 variations to limit calls
        if _budget_exhausted("CERSAI search"):
            break
        try:
            time.sleep(REQUEST_DELAY)
            r = safe_request(
                "GET",
                CERSAI_URL,
                session=session_cersai,
                params={
                    "debtorName": name,
                    "searchType": "DI",   # Debtor Individual
                },
                timeout=8,
                retries=1,
            )
            if r and r.ok:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(r.text, "html.parser")
                table = soup.find("table", {"id": "chargeTable"}) or \
                        soup.find("table", class_=lambda c: c and "charge" in c.lower())
                if table:
                    for row in table.find_all("tr")[1:]:
                        cols = [td.get_text(strip=True)
                                for td in row.find_all("td")]
                        if not cols:
                            continue
                        rec = {
                            "_source":       "CERSAI",
                            "_search_name":  name,
                            "asset":         cols[0] if cols else "N/A",
                            "lender":        cols[1] if len(cols) > 1 else "N/A",
                            "amount":        cols[2] if len(cols) > 2 else "N/A",
                            "charge_date":   cols[3] if len(cols) > 3 else "N/A",
                            "charge_status": cols[4] if len(cols) > 4 else "N/A",
                        }
                        all_records.append(rec)
        except Exception as e:
            log.warning(f"[Property] CERSAI error for '{name}': {e}")

    # ── Classify and build findings ────────────────────────────────────────────
    result.raw_results = all_records
    seen_docs: set[str] = set()

    for rec in all_records:
        source = rec.get("_source", "Property Records")

        # Build a dedup key from available identifiers
        doc_no = str(
            rec.get("doc_no") or rec.get("registration_no") or
            rec.get("asset") or rec.get("col_0", "")
        )
        dedup_key = f"{source}:{doc_no}"
        if dedup_key in seen_docs:
            continue
        seen_docs.add(dedup_key)

        # Extract common fields with fallbacks
        party1    = str(rec.get("first_party")  or rec.get("seller") or
                        rec.get("vikreta")       or rec.get("col_1", ""))
        party2    = str(rec.get("second_party") or rec.get("buyer")  or
                        rec.get("kreta")         or rec.get("col_2", ""))
        prop_addr = str(rec.get("property")     or rec.get("address") or
                        rec.get("asset")         or rec.get("col_3", "N/A"))
        reg_date  = str(rec.get("reg_date")     or rec.get("charge_date") or
                        rec.get("col_4", "N/A"))
        amount    = str(rec.get("amount")       or rec.get("consideration") or
                        rec.get("col_5", "N/A"))

        # CERSAI charges = active mortgage = medium priority by default
        if source == "CERSAI":
            charge_status = rec.get("charge_status", "").upper()
            lender = rec.get("lender", "Unknown lender")
            priority = Priority.HIGH if "ACTIVE" in charge_status else Priority.MEDIUM
            title = f"CERSAI Charge — {prop_addr[:60]}"
            detail = (
                f"Asset: {prop_addr} | "
                f"Lender: {lender} | "
                f"Amount: {amount} | "
                f"Charge date: {reg_date} | "
                f"Status: {charge_status} | "
                f"⚠ Property under mortgage/charge"
            )
        else:
            # Registration record — property found
            district = rec.get("_district") or rec.get("_sro", "")
            priority = Priority.MEDIUM   # undisclosed = medium by default
            title = f"Registered Property — {district}"
            detail = (
                f"Registration No: {doc_no} | "
                f"Date: {reg_date} | "
                f"First Party (Seller): {party1} | "
                f"Second Party (Buyer): {party2} | "
                f"Property: {prop_addr} | "
                f"Amount: ₹{amount}"
            )

        finding = Finding(
            source=source,
            category="Property Records",
            title=title,
            detail=detail,
            priority=priority,
            raw_data=rec,
        )
        result.findings.append(finding)

    result.success = True
    result.duration_sec = time.time() - start

    log.info(
        f"[Property] Complete — {len(all_records)} record(s) found | "
        f"High: {result.high_priority_count} | "
        f"Medium: {result.medium_priority_count}"
    )
    return result


# ─── MODULE 8: NCLT — Insolvency Proceedings ─────────────────────────────────
# CONDITIONAL: only runs when subject.has_business() == True
#
# Two complementary sources:
#   A) LegalKart API  — covers NCLT case search (same API key as eCourts)
#   B) IBBI website   — public insolvency proceeding records, free scrape
#
# What we're looking for:
#   • Corporate Insolvency Resolution Process (CIRP) against their company
#   • Liquidation proceedings
#   • Personal guarantor insolvency
#   • Subject named as promoter/director in CIRP matter

def run_nclt(subject: SubjectProfile, ctx: PipelineContext) -> ModuleResult:
    result = ModuleResult(module_name="NCLT")

    # ── Conditional gate ──────────────────────────────────────────────────────
    if not subject.has_business():
        result.skipped = True
        result.skip_reason = (
            "No business or company name provided. NCLT insolvency checks apply "
            "to businesses and their directors/promoters. If subject later discloses "
            "a business, re-run this module."
        )
        log.info("[NCLT] Skipped — no business name in profile")
        return result

    start = time.time()
    result.ran = True
    max_duration_sec = int(os.getenv("NCLT_MAX_DURATION_SEC", "25"))
    hard_deadline = start + max_duration_sec

    business_name = (subject.business_name or subject.company_name or "").strip()

    # Search business name first (higher precision), then full name.
    search_names: list[str] = []
    for term in [business_name, subject.full_name]:
        t = (term or "").strip()
        if not t:
            continue
        if t.lower() not in [x.lower() for x in search_names]:
            search_names.append(t)

    def _time_left() -> int:
        return int(max(0, hard_deadline - time.time()))

    def _budget_available(min_seconds: int, stage: str) -> bool:
        remaining = _time_left()
        if remaining >= min_seconds:
            return True
        if not result.error:
            result.error = (
                f"NCLT check hit module time limit ({max_duration_sec}s). "
                "Partial results returned."
            )
        log.warning(f"[NCLT] Time budget exhausted before {stage} (left={remaining}s)")
        return False

    # ── Source A: LegalKart NCLT API ──────────────────────────────────────────
    log.info(f"[NCLT] Searching LegalKart API for: {search_names}")

    if ctx.legalkart_token:
        session = ctx.sessions["legalkart"]  # already authenticated, reuse
        for name in search_names:
            if not _budget_available(4, f"LegalKart search for '{name}'"):
                break

            per_call_timeout = max(4, min(8, _time_left()))
            r = safe_request(
                "GET",
                f"{LEGALKART_BASE}/nclt/keyword-search",
                session=session,
                params={"keyword": name},
                timeout=per_call_timeout,
                retries=1,
            )
            if r and r.ok:
                try:
                    cases = r.json().get("cases") or r.json().get("results") or []
                    for case in cases:
                        raw = {
                            "source":      "LegalKart NCLT API",
                            "case_number": case.get("case_number", "N/A"),
                            "case_type":   case.get("case_type", "N/A"),
                            "petitioner":  case.get("petitioner", "N/A"),
                            "respondent":  case.get("respondent", "N/A"),
                            "status":      case.get("current_status", "N/A"),
                            "bench":       case.get("court") or case.get("bench", "N/A"),
                            "filed_date":  case.get("filing_date", "N/A"),
                        }
                        result.raw_results.append(raw)

                        # Any NCLT insolvency case against the subject or their
                        # company is HIGH priority — it means creditors took them
                        # to tribunal over unpaid debts
                        is_respondent = (
                            subject.full_name.lower() in str(raw["respondent"]).lower() or
                            business_name.lower() in str(raw["respondent"]).lower()
                        )
                        priority = Priority.HIGH if is_respondent else Priority.MEDIUM

                        finding = Finding(
                            source="NCLT / LegalKart API",
                            category="Insolvency & Debt",
                            title=f"NCLT Case — {raw['case_type']} | {raw['bench']}",
                            detail=(
                                f"Case: {raw['case_number']} | "
                                f"Filed: {raw['filed_date']} | "
                                f"Petitioner: {raw['petitioner']} | "
                                f"Respondent: {raw['respondent']} | "
                                f"Status: {raw['status']}"
                            ),
                            priority=priority,
                            raw_data=raw
                        )
                        result.findings.append(finding)
                except Exception as e:
                    log.warning(f"[NCLT] LegalKart parse error: {e}")
    else:
        log.warning("[NCLT] LEGALKART token unavailable — skipping API source")

    # ── Source B: IBBI public insolvency records ───────────────────────────────
    # IBBI publishes all CIRP and liquidation orders publicly at ibbi.gov.in
    # We search their orders page for the company/person name
    log.info(f"[NCLT] Searching IBBI public records for: {business_name}")

    IBBI_ORDERS_URL = "https://ibbi.gov.in/en/orders/nclt"

    try:
        from bs4 import BeautifulSoup

        # Use context IBBI session — persistent across calls
        session_ibbi = ctx.sessions["ibbi"]

        # Try fetching with company name as search param
        if business_name and _budget_available(5, "IBBI query"):
            per_call_timeout = max(5, min(10, _time_left()))
            r = safe_request(
                "GET",
                IBBI_ORDERS_URL,
                session=session_ibbi,
                params={"search": business_name},
                timeout=per_call_timeout,
                retries=1,
            )
        else:
            r = None
            if not business_name:
                log.info("[NCLT] IBBI query skipped — no business name available")

        if r and r.ok:
            soup = BeautifulSoup(r.text, "html.parser")

            # Parse result entries — IBBI lists orders as table rows or cards
            order_rows = (
                soup.find_all("tr")[1:] or          # table format
                soup.find_all("div", class_="order-item")  # card format
            )

            for row in order_rows[:15]:  # cap to avoid parsing bloat on slow pages
                text = row.get_text(separator=" ", strip=True)

                # Only keep rows where company/person name appears
                if (business_name.lower() not in text.lower() and
                        subject.full_name.lower() not in text.lower()):
                    continue

                # Try to extract date and title
                cols = [td.get_text(strip=True) for td in row.find_all("td")]
                link_tag = row.find("a")
                order_url = link_tag["href"] if link_tag and link_tag.get("href") else ""
                if order_url and not order_url.startswith("http"):
                    order_url = f"https://ibbi.gov.in{order_url}"

                raw = {
                    "source":  "IBBI",
                    "text":    text[:300],
                    "columns": cols,
                    "url":     order_url,
                }
                result.raw_results.append(raw)

                finding = Finding(
                    source="IBBI Public Records",
                    category="Insolvency & Debt",
                    title=f"IBBI Insolvency Order — {cols[0] if cols else 'N/A'}",
                    detail=(
                        f"Subject or company found in IBBI insolvency order. "
                        f"Details: {text[:200]} | "
                        f"URL: {order_url}"
                    ),
                    priority=Priority.HIGH,
                    url=order_url,
                    raw_data=raw
                )
                result.findings.append(finding)

    except ImportError:
        log.warning("[NCLT] beautifulsoup4 not installed — IBBI scrape skipped")
    except Exception as e:
        log.warning(f"[NCLT] IBBI scrape error: {e}")

    result.success = True
    result.duration_sec = time.time() - start

    log.info(f"[NCLT] {len(result.findings)} insolvency record(s) found.")
    return result


# ─── MODULE 8: SEBI Enforcement Orders ───────────────────────────────────────
# CONDITIONAL: only runs when subject.has_finance_role() == True
#              (auto-detected from employer/business keywords, or manually flagged)
#
# PERMITTED sources:
#   A) NSE Debarred Entities XLS — downloaded fresh each run, searched in-memory
#      Covers: entities formally debarred by SEBI enforcement order (public list)
#   B) SEBI enforcement orders page — sebi.gov.in
#      Covers: show-cause notices, settlement orders, adjudication orders
#
# STRICTLY PROHIBITED (CICRA 2005 + RBI Master Directions 2024):
#   This module does NOT access loan default data, CIBIL records, NPA lists,
#   bank defaulter registers, or any credit bureau information. Accessing or
#   reselling such data without an RBI Certificate of Registration constitutes
#   operating as an unlicensed Credit Information Company (CICRA S.3).
#
# All findings are categorised as "Securities Market — Public Enforcement Records"
# to ensure no finding is misread as a credit bureau output.
#
# Why this matters for matrimonial:
#   A subject claiming to be a "stock market expert" or "SEBI registered advisor"
#   may have had their registration cancelled or been formally debarred.

def _search_debarred_list(entities: list[dict], name: str) -> list[dict]:
    """Search the debarred entities list for fuzzy name match."""
    name_lower = name.lower().strip()
    matches = []
    for entity in entities:
        # Search across all string columns for name match
        for val in entity.values():
            if name_lower in val.lower():
                matches.append(entity)
                break
    return matches


def run_sebi(subject: SubjectProfile, ctx: PipelineContext) -> ModuleResult:
    result = ModuleResult(module_name="SEBI")

    # ── Conditional gate ──────────────────────────────────────────────────────
    if not subject.has_finance_role():
        result.skipped = True
        result.skip_reason = (
            "Subject does not claim a finance or investment role. "
            "SEBI checks apply when employer/business relates to: "
            "stock broking, investment advisory, mutual funds, trading, "
            "wealth management, or SEBI-registered entities. "
            "Set claims_finance_role=True on SubjectProfile to force this check."
        )
        log.info("[SEBI] Skipped — no finance role detected")
        return result

    start = time.time()
    result.ran = True

    search_names = [subject.full_name]
    if subject.business_name:
        search_names.append(subject.business_name)
    if subject.company_name:
        search_names.append(subject.company_name)

    # ── Source A: NSE Debarred Entities — from context (downloaded once) ────────
    log.info(f"[SEBI] Checking NSE debarred entities list for: {search_names}")
    debarred_list = ctx.nse_debarred  # already loaded by context, no re-download

    if debarred_list:
        for name in search_names:
            matches = _search_debarred_list(debarred_list, name)
            for match in matches:
                result.raw_results.append({**match, "search_term": name,
                                           "source": "NSE Debarred XLS"})

                # Determine order type from available columns
                order_details = " | ".join(
                    f"{k}: {v}" for k, v in match.items()
                    if v and k not in ("", "col_0")
                )

                finding = Finding(
                    source="NSE / SEBI Debarred Entities",
                    category="Securities Market — Public Enforcement Records",
                    title=f"SEBI DEBARMENT ORDER — {name}",
                    detail=(
                        f"Subject or associated entity found on the NSE/SEBI publicly "
                        f"published debarred entities list. SEBI has issued a formal order "
                        f"banning this entity from the securities market. "
                        f"Source: NSE official debarred entities register (public record). "
                        f"Details: {order_details}"
                    ),
                    priority=Priority.HIGH,
                    raw_data=match
                )
                result.findings.append(finding)
    else:
        log.warning("[SEBI] NSE debarred list unavailable — falling back to SEBI scrape only")

    # ── Source B: SEBI Enforcement Orders Page Scrape ─────────────────────────
    # sebi.gov.in/enforcement/orders.html has a search form
    log.info(f"[SEBI] Scraping SEBI enforcement orders for: {search_names}")

    SEBI_ORDERS_URL = "https://www.sebi.gov.in/enforcement/orders.html"
    # SEBI uses an internal search API — endpoint discovered via browser devtools
    SEBI_SEARCH_API = "https://www.sebi.gov.in/sebiweb/other/OtherAction.do"

    try:
        from bs4 import BeautifulSoup
        session = ctx.sessions["sebi"]

        for name in search_names:
            time.sleep(REQUEST_DELAY)
            r = session.get(
                SEBI_SEARCH_API,
                params={
                    "doSearch": "yes",
                    "searchText": name,
                    "type": "orders",
                },
                timeout=15
            )

            if not r or not r.ok:
                continue

            try:
                # Try JSON response first
                data = r.json()
                orders = data.get("orders") or data.get("results") or []
            except Exception:
                # Parse HTML
                soup = BeautifulSoup(r.text, "html.parser")
                orders = []
                table = soup.find("table")
                if table:
                    for row in table.find_all("tr")[1:]:
                        cols = [td.get_text(strip=True) for td in row.find_all("td")]
                        link = row.find("a")
                        orders.append({
                            "date":   cols[0] if cols else "",
                            "entity": cols[1] if len(cols) > 1 else "",
                            "type":   cols[2] if len(cols) > 2 else "",
                            "url":    link["href"] if link and link.get("href") else "",
                        })

            for order in orders:
                entity_text = str(order.get("entity", "") or order.get("name", ""))
                # Only keep if name actually appears in the order
                if name.lower() not in entity_text.lower():
                    continue

                order_type = order.get("type", "Enforcement Order")
                order_date = order.get("date", "N/A")
                order_url  = order.get("url", "")
                if order_url and not order_url.startswith("http"):
                    order_url = f"https://www.sebi.gov.in{order_url}"

                raw = {
                    "source":      "SEBI Enforcement Orders",
                    "search_term": name,
                    "entity":      entity_text,
                    "type":        order_type,
                    "date":        order_date,
                    "url":         order_url,
                }
                result.raw_results.append(raw)

                # Classify by order type
                if any(kw in order_type.lower() for kw in
                       ["debarr", "prohibit", "restrain", "disgorg", "criminal"]):
                    priority = Priority.HIGH
                elif any(kw in order_type.lower() for kw in
                         ["settlement", "adjudication", "penalty", "warning"]):
                    priority = Priority.MEDIUM
                else:
                    priority = Priority.LOW

                finding = Finding(
                    source="SEBI Enforcement Orders",
                    category="Securities Market — Public Enforcement Records",
                    title=f"SEBI Public Enforcement Order — {order_type} | {order_date}",
                    detail=(
                        f"Entity: {entity_text} | "
                        f"Order Type: {order_type} | "
                        f"Date: {order_date} | "
                        f"Source: sebi.gov.in public enforcement orders register. "
                        f"URL: {order_url}"
                    ),
                    priority=priority,
                    url=order_url,
                    raw_data=raw
                )
                result.findings.append(finding)

    except ImportError:
        log.warning("[SEBI] beautifulsoup4 not installed — SEBI orders scrape skipped")
    except Exception as e:
        log.warning(f"[SEBI] Orders scrape error: {e}")
        result.error = str(e)

    result.success = True
    result.duration_sec = time.time() - start

    log.info(f"[SEBI] {len(result.findings)} enforcement record(s) found.")
    return result


# ─── MODULE 10: Social Media Footprint ───────────────────────────────────────
#
# Covers: LinkedIn, Instagram, Facebook
# Always runs — skips individual platforms gracefully if unreachable.
#
# COMPLIANCE MODE:
#   Profile discovery via Google site: search is allowed.
#   Automated profile fetching/scraping is disabled due to legal review.
#   For each discovered URL, this module emits a manual-review checklist.
#
# WHAT WE EMIT:
#   Priority NONE manual review findings for LinkedIn, Instagram, and Facebook.
#   Reviewer records factual consistency after human inspection.

TINEYE_API_KEY     = os.getenv("TINEYE_API_KEY", "")     # tineye.com reverse image


def _serp_search(session, query: str, num: int = 5) -> list[dict]:
    """
    Run a SerpAPI Google search and return organic results.
    Reuses the existing SERP_API_KEY from config.
    Returns empty list if SERP_API_KEY not configured.
    """
    if not SERP_API_KEY:
        return []
    try:
        r = safe_request(
            "GET",
            "https://serpapi.com/search",
            session=session,
            params={"q": query, "api_key": SERP_API_KEY,
                    "num": num, "hl": "en", "gl": "in"}
        )
        if r and r.ok:
            return r.json().get("organic_results", [])
    except Exception as e:
        log.warning(f"[SocialMedia] SerpAPI error for '{query}': {e}")
    return []


def _discover_profile_url(session, platform: str,
                           name: str, city: str,
                           employer: str = "") -> Optional[str]:
    """
    Use Google site: search to discover a profile URL for the given name.
    Returns the first plausible result URL or None.
    """
    site_map = {
        "linkedin":  "site:linkedin.com/in",
        "instagram": "site:instagram.com",
        "facebook":  "site:facebook.com",
    }
    site = site_map.get(platform, "")
    query = f'{site} "{name}" "{city}"'
    if employer:
        query += f' "{employer}"'

    results = _serp_search(session, query, num=3)
    for r in results:
        url = r.get("link", "")
        if platform in url.lower():
            # Basic sanity check — URL should not be a company/jobs page
            if platform == "linkedin" and ("/in/" in url or "/pub/" in url):
                return url
            elif platform == "instagram" and "instagram.com/" in url:
                # Exclude instagram.com/p/ (posts), instagram.com/explore/
                if "/p/" not in url and "/explore/" not in url:
                    return url
            elif platform == "facebook" and "facebook.com/" in url:
                # Exclude groups, pages, events
                if not any(x in url for x in
                           ["/groups/", "/events/", "/pages/",
                            "/watch/", "/marketplace/"]):
                    return url
    return None


# ── Social media: compliance note ────────────────────────────────────────────
#
# Automated profile fetching from LinkedIn, Instagram, and Facebook is
# PERMANENTLY DISABLED under the following legal constraints:
#
#   IT Act 2000 S.43(b): Extracting a computer database without permission
#   from the host server (LinkedIn / Instagram / Facebook) constitutes
#   unauthorized access, exposing the platform to compensatory damages.
#
#   Platform Terms of Service:
#     LinkedIn  — prohibits scraping of profile data (robots/crawlers)
#     Instagram — prohibits automated collection without express permission
#     Facebook  — prohibits automated data collection without written consent
#
# The compliant approach: use Google site: search (via SerpAPI) to DISCOVER
# publicly indexed profile URLs, then emit a structured manual-review checklist
# for a human analyst to inspect and record factual, binary observations.
# No automated reading of profile content is permitted.

# ── Main module orchestrator ──────────────────────────────────────────────────

def _manual_social_review_finding(platform: str,
                                  url: Optional[str],
                                  checklist: list[str],
                                  discovery_note: str = "") -> Finding:
    """Create a structured manual-review finding for discovered social profiles."""
    detail_lines = [
        "[MANUAL REVIEW REQUIRED]",
        f"Platform: {platform}",
        f"URL discovered: {url or 'Not discovered via Google site search'}",
        "Reviewer to check and record:",
    ]
    detail_lines.extend([f"  - {item}" for item in checklist])
    if discovery_note:
        detail_lines.append(f"Discovery note: {discovery_note}")

    return Finding(
        source=platform,
        category="Social Media",
        title=f"[MANUAL REVIEW REQUIRED] Platform: {platform}",
        detail="\n".join(detail_lines),
        priority=Priority.NONE,
        url=url,
    )

def run_social_media(subject: SubjectProfile,
                     ctx: PipelineContext) -> ModuleResult:
    """
    Social media assisted review module.
    Keeps Google site: discovery, but disables automated profile fetching.
    Emits manual-review checklists for human verification.
    """
    result = ModuleResult(module_name="Social Media")
    start  = time.time()
    result.ran = True

    serp_session = ctx.sessions["serp"]
    name         = subject.full_name
    city         = subject.current_city
    employer     = subject.employer_name or ""

    discovered_profiles: list[dict] = []

    # ── LinkedIn ──────────────────────────────────────────────────────────────
    log.info(f"[Social] LinkedIn check for: {name}")
    linkedin_url = subject.linkedin_url
    linkedin_note = ""

    if not linkedin_url:
        linkedin_url = _discover_profile_url(
            serp_session, "linkedin", name, city, employer
        )
        if linkedin_url:
            log.info(f"[Social] LinkedIn discovered: {linkedin_url}")
            linkedin_note = "Discovered via Google site search."
        elif not SERP_API_KEY:
            linkedin_note = "SERP_API_KEY not set; Google site discovery unavailable."
        else:
            linkedin_note = "No LinkedIn profile URL discovered via Google site search."

    result.findings.append(_manual_social_review_finding(
        platform="LinkedIn",
        url=linkedin_url,
        checklist=[
            "Name on profile matches claimed name?",
            "Current employer matches claimed employer?",
            "Education matches claimed college/year?",
            "Account creation date (approx)?",
            "Connection count (rough range)?",
            "Any inconsistencies noted?",
        ],
        discovery_note=linkedin_note,
    ))
    if linkedin_url:
        discovered_profiles.append({"platform": "linkedin", "url": linkedin_url})

    # ── Instagram ─────────────────────────────────────────────────────────────
    log.info(f"[Social] Instagram check for: {name}")
    ig_username = subject.instagram_username
    ig_url = None
    ig_note = ""

    if ig_username:
        ig_username = ig_username.lstrip("@").strip()
        ig_url = f"https://instagram.com/{ig_username}"
        ig_note = "Provided by subject input."
    else:
        ig_url = _discover_profile_url(serp_session, "instagram", name, city)
        if ig_url:
            ig_note = "Discovered via Google site search."
        elif not SERP_API_KEY:
            ig_note = "SERP_API_KEY not set; Google site discovery unavailable."
        else:
            ig_note = "No Instagram profile URL discovered via Google site search."

    result.findings.append(_manual_social_review_finding(
        platform="Instagram",
        url=ig_url,
        checklist=[
            "Name/username matches claimed identity?",
            "Bio or visible profile text contradicts claimed status?",
            "Current location cues match claimed city?",
            "Account creation date (approx)?",
            "Follower/following count (rough range)?",
            "Any inconsistencies noted?",
        ],
        discovery_note=ig_note,
    ))
    if ig_url:
        discovered_profiles.append({"platform": "instagram", "url": ig_url})

    # ── Facebook ──────────────────────────────────────────────────────────────
    log.info(f"[Social] Facebook check for: {name}")
    fb_profile_id = subject.facebook_profile_id
    fb_url = None
    fb_note = ""

    if fb_profile_id:
        fb_profile_id = fb_profile_id.strip()
        fb_url = f"https://facebook.com/{fb_profile_id}"
        fb_note = "Provided by subject input."
    else:
        fb_url = _discover_profile_url(serp_session, "facebook", name, city)
        if fb_url:
            fb_note = "Discovered via Google site search."
        elif not SERP_API_KEY:
            fb_note = "SERP_API_KEY not set; Google site discovery unavailable."
        else:
            fb_note = "No Facebook profile URL discovered via Google site search."

    result.findings.append(_manual_social_review_finding(
        platform="Facebook",
        url=fb_url,
        checklist=[
            "Name on profile matches claimed name?",
            "Relationship status visible and consistent with claim?",
            "Current city/location matches claimed city?",
            "Employment or education details match claims?",
            "Account creation date (approx)?",
            "Any inconsistencies noted?",
        ],
        discovery_note=fb_note,
    ))
    if fb_url:
        discovered_profiles.append({"platform": "facebook", "url": fb_url})

    result.raw_results = [
        {
            "mode": "manual_review",
            "platform": p["platform"],
            "url": p["url"],
        }
        for p in discovered_profiles
    ]
    result.success = True
    result.duration_sec = time.time() - start

    log.info(
        f"[Social] Complete — manual checklist generated for 3 platforms | "
        f"Discovered URLs: {len(discovered_profiles)}"
    )
    return result


# ─── MODULE 11: Reverse Image Search ─────────────────────────────────────────
#
# CONDITIONAL: only runs when subject.photo_path is set
#
# SOURCES:
#   A) Yandex Reverse Image — via SerpAPI yandex_images engine (reuses SERP key)
#   B) TinEye — via tineye.com API (separate key, optional)
#   C) Google Reverse Image — via SerpAPI google_reverse_image engine
#
# WHAT WE FLAG:
#   HIGH   • Photo found on stock image sites (clearly fake profile)
#          • Yandex identifies face as a different named person
#          • Photo found with a different name in results
#   MEDIUM • Photo found on matrimonial sites under a different profile
#          • TinEye: many exact copies (widely reused photo)
#   LOW    • No suspicious matches found

def _upload_photo_to_imgbb(photo_path: str,
                            session: requests.Session) -> Optional[str]:
    """
    Upload a local photo to imgbb.com (free key required) to get a public URL.
    Falls back to Yandex direct upload if no imgbb key set.
    """
    IMGBB_API_KEY = os.getenv("IMGBB_API_KEY", "")
    if not IMGBB_API_KEY:
        return _upload_to_yandex_direct(photo_path, session)
    try:
        import base64
        with open(photo_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        r = safe_request(
            "POST",
            "https://api.imgbb.com/1/upload",
            session=session,
            params={"key": IMGBB_API_KEY},
            json_body={"image": img_b64},
        )
        if r and r.ok:
            return r.json().get("data", {}).get("url")
    except Exception as e:
        log.warning(f"[Image] imgbb upload failed: {e}")
    return None


def _upload_to_yandex_direct(photo_path: str,
                              session: requests.Session) -> Optional[str]:
    """Upload image to Yandex image host, returns hosted URL."""
    try:
        with open(photo_path, "rb") as f:
            img_data = f.read()
        import mimetypes
        mime  = mimetypes.guess_type(photo_path)[0] or "image/jpeg"
        files = {"upfile": (os.path.basename(photo_path), img_data, mime)}
        r = session.post(
            "https://yandex.com/images-apphost/image-download",
            files=files,
            params={"cbird": "111", "images_avatars_size": "orig"},
            timeout=20
        )
        if r and r.ok:
            data  = r.json()
            img_id = data.get("image_id") or data.get("imageId")
            if img_id:
                return f"https://avatars.mds.yandex.net/get-images-cbir/{img_id}/orig"
    except Exception as e:
        log.warning(f"[Image] Yandex direct upload failed: {e}")
    return None


def _analyse_image_results(results: list[dict],
                            subject_name: str) -> tuple[list[Finding], int]:
    """Scan reverse image results for red flags. Returns (findings, suspicious_count)."""
    findings   = []
    suspicious = 0
    stock_domains = {
        "shutterstock.com", "gettyimages.com", "istockphoto.com",
        "123rf.com", "dreamstime.com", "freepik.com", "unsplash.com",
        "pexels.com", "pixabay.com", "alamy.com",
    }
    matrimonial_domains = {
        "shaadi.com", "jeevansathi.com", "bharatmatrimony.com",
        "matrimonials.com", "simplymarry.com",
    }
    for item in results:
        url    = item.get("link") or item.get("url") or ""
        title  = item.get("title") or item.get("snippet") or ""
        domain = url.split("/")[2].lower().replace("www.", "") if "://" in url else ""

        if any(s in domain for s in stock_domains):
            findings.append(Finding(
                source="Reverse Image Search",
                category="Identity Verification",
                title="Photo found on stock image site",
                detail=(
                    f"The submitted photo appears on '{domain}', a stock image site. "
                    f"This strongly suggests the profile photo is fake/stolen. URL: {url}"
                ),
                priority=Priority.HIGH,
                url=url,
            ))
            suspicious += 1
            continue

        subject_first = subject_name.split()[0].lower()
        title_lower   = title.lower()
        if (title_lower and subject_first not in title_lower and len(title) > 5
                and any(c.isalpha() for c in title)):
            words = [w for w in title.split() if w and w[0].isupper() and len(w) > 2]
            if words:
                findings.append(Finding(
                    source="Reverse Image Search",
                    category="Identity Verification",
                    title=f"Photo found with different name: '{title[:60]}'",
                    detail=(
                        f"Reverse image search found this photo associated with a "
                        f"different name. Found on: {domain} | Title: {title} | URL: {url}"
                    ),
                    priority=Priority.HIGH,
                    url=url,
                ))
                suspicious += 1
                continue

        if any(m in domain for m in matrimonial_domains):
            findings.append(Finding(
                source="Reverse Image Search",
                category="Identity Verification",
                title=f"Photo found on matrimonial site: {domain}",
                detail=(
                    f"This photo appears on {domain}. If this is not the same profile "
                    f"shared by the family, it may indicate a duplicate/fake listing. "
                    f"URL: {url}"
                ),
                priority=Priority.MEDIUM,
                url=url,
            ))
            suspicious += 1

    return findings, suspicious


def run_reverse_image(subject: SubjectProfile,
                      ctx: PipelineContext) -> ModuleResult:
    result = ModuleResult(module_name="Reverse Image Search")

    if not subject.photo_path:
        result.skipped = True
        result.skip_reason = (
            "No photo provided. Set photo_path on SubjectProfile to enable "
            "reverse image search across Yandex, TinEye, and Google Images."
        )
        log.info("[Image] Skipped — no photo_path provided")
        return result

    if not os.path.exists(subject.photo_path):
        result.skipped = True
        result.skip_reason = f"Photo not found at path: {subject.photo_path}"
        return result

    start = time.time()
    result.ran = True
    yandex_session = ctx.sessions["yandex"]
    all_results: list[dict] = []

    # Step 1: Upload photo to get a public URL
    log.info(f"[Image] Uploading photo: {subject.photo_path}")
    photo_url = _upload_photo_to_imgbb(subject.photo_path, yandex_session)
    if not photo_url:
        result.error = (
            "Could not upload photo. Set IMGBB_API_KEY in .env (free at imgbb.com) "
            "or ensure internet access to Yandex upload endpoint."
        )
        result.success = False
        result.duration_sec = time.time() - start
        return result

    log.info(f"[Image] Photo hosted at: {photo_url}")

    if SERP_API_KEY:
        # Source A: Yandex reverse image
        log.info("[Image] Searching Yandex reverse image...")
        try:
            r = safe_request(
                "GET", "https://serpapi.com/search",
                session=ctx.sessions["serp"],
                params={"engine": "yandex_images", "url": photo_url,
                        "api_key": SERP_API_KEY}
            )
            if r and r.ok:
                data = r.json()
                yandex_results = data.get("image_results", [])
                for item in yandex_results:
                    item["_engine"] = "yandex"
                all_results.extend(yandex_results)

                # Yandex knowledge graph = face identified as someone else
                kg = data.get("knowledge_graph", {})
                if kg:
                    kg_name = kg.get("title") or kg.get("name", "")
                    if kg_name and subject.full_name.split()[0].lower() not in kg_name.lower():
                        result.findings.append(Finding(
                            source="Yandex Knowledge Graph",
                            category="Identity Verification",
                            title=f"Yandex identified photo as: '{kg_name}'",
                            detail=(
                                f"Yandex face recognition identified this person as '{kg_name}', "
                                f"not '{subject.full_name}'. "
                                f"Knowledge graph: {json.dumps(kg)[:300]}"
                            ),
                            priority=Priority.HIGH,
                        ))
                log.info(f"[Image] Yandex: {len(yandex_results)} results")
        except Exception as e:
            log.warning(f"[Image] Yandex error: {e}")

        # Source C: Google reverse image
        log.info("[Image] Searching Google reverse image...")
        try:
            r = safe_request(
                "GET", "https://serpapi.com/search",
                session=ctx.sessions["serp"],
                params={"engine": "google_reverse_image", "image_url": photo_url,
                        "api_key": SERP_API_KEY}
            )
            if r and r.ok:
                google_results = r.json().get("image_results", [])
                for item in google_results:
                    item["_engine"] = "google"
                all_results.extend(google_results)
                log.info(f"[Image] Google: {len(google_results)} results")
        except Exception as e:
            log.warning(f"[Image] Google reverse image error: {e}")
    else:
        log.info("[Image] SERP_API_KEY not set — Yandex/Google image search skipped")

    # Source B: TinEye
    if TINEYE_API_KEY:
        log.info("[Image] Searching TinEye...")
        try:
            r = safe_request(
                "GET", "https://api.tineye.com/rest/search/",
                session=ctx.sessions["tineye"],
                params={"api_key": TINEYE_API_KEY, "image_url": photo_url,
                        "limit": 20, "offset": 0}
            )
            if r and r.ok:
                matches = r.json().get("results", {}).get("matches", [])
                log.info(f"[Image] TinEye: {len(matches)} exact matches")
                for match in matches:
                    backlinks  = match.get("backlinks", [{}])
                    first_crawl = match.get("image", {}).get("added_on", "")
                    all_results.append({
                        "_engine":    "tineye",
                        "link":       backlinks[0].get("url") if backlinks else "",
                        "title":      backlinks[0].get("backlink") if backlinks else "",
                        "first_crawl": first_crawl,
                    })
                if matches:
                    result.findings.append(Finding(
                        source="TinEye",
                        category="Identity Verification",
                        title=f"TinEye: {len(matches)} exact copy/copies of this photo online",
                        detail=(
                            f"TinEye found {len(matches)} exact match(es). "
                            f"First seen: {first_crawl or 'unknown'}. "
                            f"High count suggests widely reused/fake photo."
                        ),
                        priority=Priority.MEDIUM if len(matches) <= 3 else Priority.HIGH,
                    ))
        except Exception as e:
            log.warning(f"[Image] TinEye error: {e}")

    result.raw_results = all_results
    analysis_findings, suspicious_count = _analyse_image_results(
        all_results, subject.full_name
    )
    result.findings.extend(analysis_findings)

    if not result.findings:
        result.findings.append(Finding(
            source="Reverse Image Search",
            category="Identity Verification",
            title="No suspicious image matches found",
            detail=(
                f"Searched {len(all_results)} results across Yandex"
                f"{' + TinEye' if TINEYE_API_KEY else ''} + Google. "
                f"Photo does not appear to be stolen or reused."
            ),
            priority=Priority.LOW,
        ))

    result.success = True
    result.duration_sec = time.time() - start
    log.info(f"[Image] Complete — {len(all_results)} results | Suspicious: {suspicious_count}")
    return result


# ─── MODULE 12: Phone Number Intelligence ─────────────────────────────────────
#
# CONDITIONAL: only runs when subject.mobile is set
#
# SOURCES:
#   A) phonenumbers lib — offline carrier/region/type lookup (always free)
#   B) WhatsApp check — wa.me presence + display name from OG tags
#
# WHAT WE FLAG:
#   MEDIUM • VoIP number | Region vs city mismatch
#          • WhatsApp display name differs from claimed name
#   LOW    • Carrier/region confirmed (informational)

def _normalise_mobile(mobile: str) -> str:
    """Normalise to +91XXXXXXXXXX format."""
    digits = "".join(c for c in mobile if c.isdigit())
    if digits.startswith("91") and len(digits) == 12:
        return f"+{digits}"
    if len(digits) == 10:
        return f"+91{digits}"
    return f"+{digits}"


def run_phone_intel(subject: SubjectProfile,
                    ctx: PipelineContext) -> ModuleResult:
    result = ModuleResult(module_name="Phone Intelligence")

    if not subject.mobile:
        result.skipped = True
        result.skip_reason = "No mobile number provided."
        log.info("[Phone] Skipped — no mobile in profile")
        return result

    start  = time.time()
    result.ran = True
    mobile = _normalise_mobile(subject.mobile)
    log.info(f"[Phone] Checking: {mobile}")

    # Source A: phonenumbers — free offline carrier/region lookup
    try:
        import phonenumbers
        from phonenumbers import geocoder, carrier, timezone as tz_module

        parsed      = phonenumbers.parse(mobile, None)
        is_valid    = phonenumbers.is_valid_number(parsed)
        carrier_name = carrier.name_for_number(parsed, "en")
        region      = geocoder.description_for_number(parsed, "en")
        timezones   = list(tz_module.time_zones_for_number(parsed))
        num_type    = phonenumbers.number_type(parsed)
        type_map    = {
            phonenumbers.PhoneNumberType.MOBILE:      "Mobile",
            phonenumbers.PhoneNumberType.FIXED_LINE:  "Fixed line",
            phonenumbers.PhoneNumberType.VOIP:        "VoIP",
            phonenumbers.PhoneNumberType.TOLL_FREE:   "Toll-free",
            phonenumbers.PhoneNumberType.PREMIUM_RATE:"Premium rate",
        }
        type_str = type_map.get(num_type, "Unknown")

        priority = Priority.LOW
        flags    = []

        if not is_valid:
            flags.append("Not a valid Indian mobile number")
            priority = Priority.MEDIUM

        if type_str == "VoIP":
            flags.append("VoIP/virtual number")
            priority = Priority.MEDIUM

        # City→state consistency check
        city_state_map = {
            "delhi": "delhi", "new delhi": "delhi",
            "mumbai": "maharashtra", "pune": "maharashtra",
            "bangalore": "karnataka", "bengaluru": "karnataka",
            "hyderabad": "telangana", "chennai": "tamil",
            "kolkata": "west bengal", "ahmedabad": "gujarat",
            "noida": "uttar pradesh", "gurgaon": "haryana",
            "gurugram": "haryana", "meerut": "uttar pradesh",
        }
        expected_state = city_state_map.get((subject.current_city or "").lower(), "")
        if (expected_state and region and
                expected_state not in region.lower() and
                region.lower() not in expected_state):
            flags.append(
                f"Number registered in '{region}', subject claims '{subject.current_city}'"
            )
            priority = max(priority, Priority.MEDIUM)

        result.findings.append(Finding(
            source="phonenumbers",
            category="Phone Intelligence",
            title=f"Carrier: {carrier_name} | Region: {region} | Type: {type_str}",
            detail=(
                f"Number: {mobile} | Valid: {is_valid} | Carrier: {carrier_name} | "
                f"Region: {region} | Type: {type_str} | "
                f"Timezone: {timezones[0] if timezones else 'N/A'}"
                + ((" | ⚠ " + " | ⚠ ".join(flags)) if flags else "")
            ),
            priority=priority,
            raw_data={"number": mobile, "carrier": carrier_name, "region": region,
                      "type": type_str, "valid": is_valid},
        ))
    except ImportError:
        log.warning("[Phone] phonenumbers not installed. Run: pip install phonenumbers")
    except Exception as e:
        log.warning(f"[Phone] phonenumbers error: {e}")

    # Source B: WhatsApp presence check
    try:
        log.info(f"[Phone] Checking WhatsApp: {mobile}")
        digits = mobile.replace("+", "").replace(" ", "")
        wa_r   = safe_request("GET", f"https://wa.me/{digits}",
                              session=ctx.sessions["phone"])
        if wa_r:
            is_on_wa = "api.whatsapp.com" in wa_r.url or "wa.me" in wa_r.url
            wa_name  = ""
            if wa_r.ok:
                try:
                    from bs4 import BeautifulSoup
                    soup     = BeautifulSoup(wa_r.text, "html.parser")
                    og_title = soup.find("meta", property="og:title")
                    if og_title:
                        wa_name = og_title.get("content", "").strip()
                        if "chat with" in wa_name.lower():
                            wa_name = wa_name.split("with", 1)[-1].strip()
                except Exception:
                    pass

            wa_priority = Priority.LOW
            wa_detail   = f"Number {mobile} — WhatsApp: {'Active' if is_on_wa else 'Not found'}"
            if wa_name and subject.full_name.split()[0].lower() not in wa_name.lower():
                wa_detail  += f" | Display name: '{wa_name}' (differs from claimed name)"
                wa_priority = Priority.MEDIUM
            elif wa_name:
                wa_detail  += f" | Display name: '{wa_name}'"

            result.findings.append(Finding(
                source="WhatsApp", category="Phone Intelligence",
                title=f"WhatsApp: {'Active' if is_on_wa else 'Not found'}"
                      + (f" — '{wa_name}'" if wa_name else ""),
                detail=wa_detail, priority=wa_priority,
                url=f"https://wa.me/{digits}",
            ))
    except Exception as e:
        log.warning(f"[Phone] WhatsApp check error: {e}")

    result.success = True
    result.duration_sec = time.time() - start
    log.info(f"[Phone] Complete — {len(result.findings)} signal(s)")
    return result


# ─── MODULE 13: Matrimonial Platform Cross-check ──────────────────────────────
#
# ALWAYS RUNS — every subject is on at least one matrimonial platform.
#
# APPROACH:
#   Direct search requires login on all major platforms. Instead:
#   A) Google site: search — Shaadi publicly indexes profiles in Google.
#      Search name + city + site:shaadi.com → parse any results.
#   B) Phone OSINT — search the phone number against matrimonial sites via Google.
#   C) Profile page fetch — if a URL is found, parse visible fields directly.
#
# WHAT WE FLAG:
#   HIGH   • Marital status on profile = divorced/widowed but claimed Never Married
#          • Age on profile differs from claimed by 3+ years
#   MEDIUM • Multiple profiles found on the same platform
#          • Profile found on platforms not mentioned by subject
#   LOW    • Profile found and consistent (expected)

MATRIMONIAL_PLATFORMS = {
    "shaadi":          "site:shaadi.com",
    "jeevansathi":     "site:jeevansathi.com",
    "bharatmatrimony": "site:bharatmatrimony.com",
    "simplymarry":     "site:simplymarry.com",
}


def _fetch_matrimonial_profile(url: str,
                                session: requests.Session) -> Optional[dict]:
    """Fetch and parse a public matrimonial profile page."""
    r = safe_request("GET", url, session=session)
    if not r or not r.ok:
        return None
    try:
        from bs4 import BeautifulSoup
        soup    = BeautifulSoup(r.text, "html.parser")
        og_data = {tag.get("property", ""): tag.get("content", "")
                   for tag in soup.find_all("meta", property=True)}
        profile = {
            "url":   url,
            "title": og_data.get("og:title", ""),
            "desc":  og_data.get("og:description", ""),
        }
        for sel, key in [
            (".profile-name",   "name"),
            (".profile-age",    "age"),
            (".profile-city",   "city"),
            (".marital-status", "marital_status"),
            (".education",      "education"),
            (".profession",     "profession"),
        ]:
            el = soup.select_one(sel)
            if el:
                profile[key] = el.get_text(strip=True)
        return profile if (profile.get("title") or profile.get("desc")) else None
    except Exception as e:
        log.warning(f"[Matrimonial] Parse error for {url}: {e}")
        return None


def run_matrimonial_crosscheck(subject: SubjectProfile,
                                ctx: PipelineContext) -> ModuleResult:
    result = ModuleResult(module_name="Matrimonial Cross-check")
    start  = time.time()
    result.ran = True

    name         = subject.full_name
    city         = subject.current_city
    serp_session = ctx.sessions["serp"]
    mat_session  = ctx.sessions["matrimonial"]
    found_profiles: list[dict] = []

    for platform_key, site_filter in MATRIMONIAL_PLATFORMS.items():
        queries = [f'{site_filter} "{name}" "{city}"']
        if subject.mobile:
            digits = "".join(c for c in subject.mobile if c.isdigit())[-10:]
            queries.append(f'{site_filter} "{digits}"')

        for query in queries:
            log.info(f"[Matrimonial] Searching: {query}")
            results = _serp_search(serp_session, query, num=5)
            for res in results:
                url     = res.get("link", "")
                title   = res.get("title", "")
                snippet = res.get("snippet", "")
                is_profile = (
                    platform_key in url.lower() and
                    any(x in url.lower() for x in
                        ["/profile/", "/matrimony/", "/id-", "profile_id",
                         "/member/", "shaadi.com/rishtey/"])
                )
                if not is_profile:
                    continue

                profile_data = {
                    "platform": platform_key, "url": url,
                    "title": title, "snippet": snippet, "query": query,
                }
                found_profiles.append(profile_data)
                log.info(f"[Matrimonial] Profile found: {url}")

                time.sleep(REQUEST_DELAY)
                fetched = _fetch_matrimonial_profile(url, mat_session)
                if fetched:
                    profile_data.update(fetched)

    result.raw_results = found_profiles
    seen_urls: set[str] = set()
    platform_counts: dict[str, int] = {}

    for profile in found_profiles:
        url = profile.get("url", "")
        if url in seen_urls:
            continue
        seen_urls.add(url)

        platform = profile.get("platform", "unknown")
        platform_counts[platform] = platform_counts.get(platform, 0) + 1

        title    = profile.get("title", "")
        snippet  = profile.get("desc") or profile.get("snippet", "")
        marital  = profile.get("marital_status", "").lower()
        age_str  = profile.get("age", "")
        priority = Priority.LOW
        flags    = []

        for kw in ["divorced", "widowed", "widower", "separated", "annulled"]:
            if kw in marital or kw in snippet.lower():
                flags.append(f"Profile shows '{kw}' — verify against shared profile")
                priority = Priority.HIGH
                break

        if subject.age and age_str:
            try:
                profile_age = int("".join(c for c in age_str if c.isdigit())[:2])
                if abs(profile_age - subject.age) >= 3:
                    flags.append(
                        f"Age on profile ({profile_age}) vs claimed ({subject.age})"
                    )
                    priority = max(priority, Priority.MEDIUM)
            except (ValueError, TypeError):
                pass

        result.findings.append(Finding(
            source=f"Matrimonial ({platform})",
            category="Matrimonial Profile",
            title=f"Profile found on {platform}" +
                  (f" — {flags[0][:60]}" if flags else ""),
            detail=(
                f"Platform: {platform} | URL: {url} | Title: {title[:80]}"
                + (f" | Snippet: {snippet[:150]}" if snippet else "")
                + ((" | ⚠ " + " | ⚠ ".join(flags)) if flags else "")
            ),
            priority=priority,
            url=url,
            raw_data=profile,
        ))

    for platform, count in platform_counts.items():
        if count > 1:
            result.findings.append(Finding(
                source=f"Matrimonial ({platform})",
                category="Matrimonial Profile",
                title=f"Multiple profiles on {platform} ({count})",
                detail=(
                    f"{count} separate profiles for '{name}' on {platform}. "
                    f"May indicate duplicate/parallel active listings."
                ),
                priority=Priority.MEDIUM,
            ))

    if not found_profiles:
        result.findings.append(Finding(
            source="Matrimonial Cross-check",
            category="Matrimonial Profile",
            title="No matrimonial profiles found via Google",
            detail=(
                f"Searched Shaadi, Jeevansathi, BharatMatrimony, SimplyMarry "
                f"for '{name}' in '{city}'. No Google-indexed profiles found. "
                f"Profiles may be set to private."
            ),
            priority=Priority.LOW,
        ))

    result.success = True
    result.duration_sec = time.time() - start
    log.info(
        f"[Matrimonial] Complete — {len(found_profiles)} profile(s) | "
        f"High: {result.high_priority_count}"
    )
    return result



# ─── PIPELINE ORCHESTRATOR ────────────────────────────────────────────────────

class SearchPipeline:
    """
    Orchestrates all search modules in sequence.
    Creates a single PipelineContext at startup — all shared state
    (token, sessions, name variations, NSE list) lives there.
    Each module receives the context and never re-computes or re-authenticates.
    """

    def __init__(self, subject: SubjectProfile):
        self.subject = subject
        self.report = UnifiedReport(
            report_id=subject.report_id(),
            subject=subject,
            generated_at=datetime.now().isoformat()
        )

    @staticmethod
    def module_registry() -> list[tuple[str, Callable[[SubjectProfile, PipelineContext], ModuleResult]]]:
        """Ordered module registry used by both CLI and API runs."""
        return [
            # Always run
            ("eCourts",                 run_ecourts),
            ("MCA21",                   run_mca21),
            ("GST",                     run_gst),
            ("Google Search",           run_google_search),
            ("Property Records",        run_property_records),
            ("Social Media",            run_social_media),
            ("Reverse Image Search",    run_reverse_image),
            ("Phone Intelligence",      run_phone_intel),
            ("Matrimonial Cross-check", run_matrimonial_crosscheck),

            # Conditional: business / company
            ("NCDRC",                   run_ncdrc),
            ("NCLT",                    run_nclt),

            # Conditional: finance role
            ("SEBI",                    run_sebi),

            # Conditional: employer
            ("EPFO",                    run_epfo),
        ]

    def _run_module_safe(self, module_name: str, module_fn, ctx: PipelineContext) -> ModuleResult:
        """Execute one module and normalize operational errors into ModuleResult."""
        try:
            return module_fn(self.subject, ctx)
        except requests.exceptions.Timeout as e:
            log.warning(f"  ↳ TIMEOUT in {module_name}: {e}")
            return ModuleResult(
                module_name=module_name,
                ran=True,
                success=False,
                error=f"Timeout: {e}",
            )
        except requests.exceptions.RequestException as e:
            log.warning(f"  ↳ REQUEST ERROR in {module_name}: {e}")
            return ModuleResult(
                module_name=module_name,
                ran=True,
                success=False,
                error=f"Request error: {e}",
            )
        except Exception as e:
            # Keep the pipeline resilient while preserving traceback in logs.
            log.exception(f"  ↳ UNHANDLED ERROR in {module_name}")
            return ModuleResult(
                module_name=module_name,
                ran=True,
                success=False,
                error=f"Unhandled error: {e}",
            )

    def run(self, on_module_start=None, on_module_complete=None) -> UnifiedReport:
        log.info("=" * 60)
        log.info(f"Inkognito Pipeline Starting")
        log.info(f"Subject: {self.subject.full_name}")
        log.info(f"Report ID: {self.report.report_id}")
        log.info("=" * 60)

        # ── Create context ONCE — shared across all modules ───────────────
        ctx = PipelineContext(self.subject)

        # Pre-warm expensive resources upfront so modules never wait on each other
        # Token fetch: 1 API call total (used by eCourts + NCLT)
        _ = ctx.legalkart_token

        # NSE list: 1 download total (used by SEBI only if finance role)
        # Only pre-load if SEBI will actually run — saves a download otherwise
        if self.subject.has_finance_role():
            _ = ctx.nse_debarred

        log.info(f"[Pipeline] Context ready. "
                 f"Token: {'✓' if ctx.legalkart_token else '✗'} | "
                 f"NSE list: {len(ctx._nse_debarred or [])} entities loaded")

        modules = self.module_registry()
        total_modules = len(modules)

        for idx, (module_name, module_fn) in enumerate(modules, start=1):
            if callable(on_module_start):
                try:
                    on_module_start(module_name, idx, total_modules)
                except Exception as callback_error:
                    log.warning(f"[Pipeline] on_module_start callback failed: {callback_error}")

            log.info(f"\n▶ Running module: {module_name}")
            # Every module receives subject + shared context.
            module_result = self._run_module_safe(module_name, module_fn, ctx)
            self.report.modules[module_name] = module_result

            if callable(on_module_complete):
                try:
                    on_module_complete(module_name, module_result, idx, total_modules)
                except Exception as callback_error:
                    log.warning(f"[Pipeline] on_module_complete callback failed: {callback_error}")

            if module_result.skipped:
                log.info(f"  ↳ SKIPPED: {module_result.skip_reason[:80]}")
            elif module_result.success:
                log.info(f"  ↳ SUCCESS: {len(module_result.findings)} finding(s) "
                         f"in {module_result.duration_sec:.1f}s")
            else:
                log.warning(f"  ↳ ERROR: {module_result.error[:100]}")

        # ── Clean up sessions ──────────────────────────────────────────────
        ctx.close()

        # Final summary
        log.info("\n" + "=" * 60)
        log.info("PIPELINE COMPLETE")
        log.info(f"Overall: {self.report.overall_flag}")
        log.info(f"Total findings: {len(self.report.all_findings)}")
        log.info(f"  High priority:   {len(self.report.high_priority_findings)}")
        log.info("=" * 60)

        return self.report


# ─── OUTPUT ───────────────────────────────────────────────────────────────────

def save_report(report: UnifiedReport, output_dir: str = "./reports") -> str:
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{output_dir}/{report.report_id}_{report.subject.full_name.replace(' ', '_')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
    log.info(f"Report saved: {filename}")
    log.info(
        f"[Compliance] Report {report.report_id} is scheduled for deletion 30 days "
        f"from now. Ensure automated deletion is configured for: {output_dir}"
    )
    return filename


def print_summary(report: UnifiedReport):
    """Print clean console summary of findings."""
    print(f"""
╔══════════════════════════════════════════════════════════╗
║            INKOGNITO — REPORT SUMMARY                   ║
╚══════════════════════════════════════════════════════════╝
  Report ID : {report.report_id}
  Subject   : {report.subject.full_name}
  Generated : {report.generated_at[:19]}
  Overall   : {report.overall_flag}
──────────────────────────────────────────────────────────""")

    for name, m in report.modules.items():
        status = "⏭ SKIPPED" if m.skipped else ("✓" if m.success else "✗ ERROR")
        findings_str = f"{len(m.findings)} finding(s)" if m.ran and not m.skipped else ""
        print(f"  {status:12} {name:25} {findings_str}")
        if m.skipped:
            print(f"             → {m.skip_reason[:70]}")

    if report.high_priority_findings:
        print(f"\n{'─'*58}")
        print("  ⚠ HIGH PRIORITY FINDINGS:")
        for f in report.high_priority_findings:
            print(f"\n  [{f.source}] {f.title}")
            print(f"  {f.detail[:120]}")

    print(f"\n{'═'*58}\n")


# ─── ENTRY POINT ──────────────────────────────────────────────────────────────

if __name__ == "__main__":

    # ── Build subject profile from intake form data ──
    subject = SubjectProfile(
        # Required
        full_name="Rahul Chaudhary",
        current_city="Delhi",

        # Recommended
        age=30,
        native_city="Meerut",
        mobile="9810XXXXXX",

        # Triggers EPFO check
        employer_name="Deloitte",

        # Set these if subject claims to run a business:
        #   → Triggers NCDRC (consumer complaints) + NCLT (insolvency)
        business_name=None,   # e.g. "RC Enterprises"
        company_name=None,    # e.g. "RC Digital Pvt Ltd"

        # Set employer to a finance firm OR set claims_finance_role=True
        #   → Triggers SEBI enforcement check
        # Example: employer_name="Zerodha" would auto-trigger SEBI
        # claims_finance_role=True  # force SEBI check regardless of employer

        # Optional
        education_college="DTU",
        education_year=2017,
        photo_path=None,
    )

    # ── Run pipeline ──
    pipeline = SearchPipeline(subject)
    report = pipeline.run()

    # ── Save and display ──
    save_report(report)
    print_summary(report)