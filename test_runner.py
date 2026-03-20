"""
Inkognito — Test Runner
==================================
Run this to validate your setup and API keys before live testing.

Usage:
    python test_runner.py              # run all 4 test cases
    python test_runner.py --case 1     # run specific test case
    python test_runner.py --dry        # dry run — no real API calls, check imports only
    python test_runner.py --modules    # list all modules and their status

Each test case uses different field combinations to exercise different modules.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

DEFAULT_TEST_CASES_FILE = "test_cases.json"

# ── Colour output ──────────────────────────────────────────────────────────────
def _c(text, code): return f"\033[{code}m{text}\033[0m"
RED    = lambda t: _c(t, "31")
GREEN  = lambda t: _c(t, "32")
YELLOW = lambda t: _c(t, "33")
CYAN   = lambda t: _c(t, "36")
BOLD   = lambda t: _c(t, "1")
DIM    = lambda t: _c(t, "2")


# ── Import check ───────────────────────────────────────────────────────────────
def check_imports():
    print(BOLD("\nChecking imports..."))
    errors = []

    try:
        import inkognito_pipeline as vp
        print(GREEN("  ✓ inkognito_pipeline.py found"))
    except ImportError as e:
        print(RED(f"  ✗ inkognito_pipeline.py not found: {e}"))
        errors.append("inkognito_pipeline.py missing")
        return False, errors

    optional = {
        "requests":         "pip install requests",
        "bs4":              "pip install beautifulsoup4",
        "phonenumbers":     "pip install phonenumbers",
        "rapidfuzz":        "pip install rapidfuzz",
        "openpyxl":         "pip install openpyxl",
        "dotenv":           "pip install python-dotenv",
    }
    for mod, install_hint in optional.items():
        try:
            __import__(mod)
            print(GREEN(f"  ✓ {mod}"))
        except ImportError:
            print(YELLOW(f"  ⚠ {mod} not installed — {install_hint}"))

    return True, errors


# ── Env key check ──────────────────────────────────────────────────────────────
def check_env():
    print(BOLD("\nChecking API keys..."))

    # Load .env if present
    if Path(".env").exists():
        try:
            from dotenv import load_dotenv
            load_dotenv()
            print(DIM("  .env file loaded"))
        except ImportError:
            pass

    required = {
        "LEGALKART_API_KEY": "legalkart.com/api-partner",
        "SERP_API_KEY":      "serpapi.com",
        "MCA_API_KEY":       "surepass.io / sandbox.co.in",
    }
    optional = {
        "MCA_API_PROVIDER":     "set to: surepass | sandbox | compdata",
        "CAPTCHA_API_KEY":      "2captcha.com — needed for IGRS UP",
        "CAPTCHA_BYPASS_ENABLED":"set True only with legal sign-off (default False)",
        "TINEYE_API_KEY":       "tineye.com — exact image copies",
        "IMGBB_API_KEY":        "imgbb.com — photo hosting for image search",
    }

    configured_required = 0
    for key, hint in required.items():
        val = os.getenv(key, "")
        if val:
            print(GREEN(f"  ✓ {key} set"))
            configured_required += 1
        else:
            print(RED(f"  ✗ {key} not set — get from: {hint}"))

    print()
    configured_optional = 0
    for key, hint in optional.items():
        val = os.getenv(key, "")
        if val:
            print(GREEN(f"  ✓ {key} set"))
            configured_optional += 1
        else:
            print(DIM(f"  · {key} not set ({hint})"))

    print(f"\n  Required: {configured_required}/{len(required)} configured")
    print(f"  Optional: {configured_optional}/{len(optional)} configured")

    return configured_required, len(required)


def load_test_cases(path: str) -> list[dict]:
    """Load test case fixtures from JSON file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Test cases file not found: {path}")

    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Test cases file must contain a list of case objects")

    required = {"id", "label", "description", "subject"}
    for i, case in enumerate(data, start=1):
        if not isinstance(case, dict):
            raise ValueError(f"Case #{i} is not a JSON object")
        missing = required - set(case.keys())
        if missing:
            missing_csv = ", ".join(sorted(missing))
            raise ValueError(f"Case #{i} missing required fields: {missing_csv}")
        if not isinstance(case["subject"], dict):
            raise ValueError(f"Case #{i} has invalid 'subject' (must be object)")

    return sorted(data, key=lambda c: c.get("id", 0))


# ── Run a single test case ─────────────────────────────────────────────────────

def run_test(case: dict, dry: bool = False) -> dict:
    print(BOLD(f"\n{'='*60}"))
    print(BOLD(f"Test {case['id']}: {case['label']}"))
    print(DIM(f"  {case['description']}"))
    print()

    import inkognito_pipeline as vp

    subject = vp.SubjectProfile(**case["subject"])
    print(f"  Subject: {subject.full_name} | {subject.current_city}")

    if dry:
        print(YELLOW("  [DRY RUN — skipping actual pipeline execution]"))
        return {"case_id": case["id"], "dry": True}

    t0     = time.time()
    pipeline = vp.SearchPipeline(subject)
    report   = pipeline.run()
    elapsed  = time.time() - t0

    # ── Print per-module summary ──
    print(f"\n  {'Module':<30} {'Status':<10} {'Findings':<10} {'Duration'}")
    print(f"  {'-'*65}")

    pass_count = fail_count = skip_count = 0
    for mod_name, mod_result in report.modules.items():
        if mod_result.skipped:
            status_str = DIM("SKIPPED")
            skip_count += 1
        elif mod_result.success:
            status_str = GREEN("OK")
            pass_count += 1
        else:
            status_str = RED("FAILED")
            fail_count += 1

        findings_str = (
            f"{mod_result.high_priority_count}H "
            f"{mod_result.medium_priority_count}M "
            f"{sum(1 for f in mod_result.findings if f.priority.value == 'LOW')}L"
        ) if not mod_result.skipped else "—"

        dur = f"{mod_result.duration_sec:.1f}s" if mod_result.duration_sec else "—"
        print(f"  {mod_name:<30} {status_str:<18} {findings_str:<10} {dur}")

        if mod_result.error:
            print(RED(f"    Error: {mod_result.error}"))

    # ── Expectation checks ──
    print(f"\n  {'─'*65}")
    check_pass = True

    for expected_ran in case.get("expect_ran", []):
        mod = report.modules.get(expected_ran)
        if mod and mod.ran:
            print(GREEN(f"  ✓ {expected_ran} ran as expected"))
        else:
            print(YELLOW(f"  ⚠ {expected_ran} did not run (may be key not configured)"))

    for expected_skip in case.get("expect_skipped", []):
        mod = report.modules.get(expected_skip)
        if mod and mod.skipped:
            print(GREEN(f"  ✓ {expected_skip} skipped as expected"))
        else:
            print(YELLOW(f"  ⚠ {expected_skip} was not skipped"))

    # ── High priority findings ──
    high = report.high_priority_findings
    if high:
        print(f"\n  {RED('HIGH PRIORITY FINDINGS:')}")
        for f in high:
            print(f"    • [{f.source}] {f.title}")

    # ── Summary ──
    total_findings = len(report.all_findings)
    high_priority = len(report.high_priority_findings)
    print(f"\n  Summary: {total_findings} findings | "
          f"{pass_count} ran | {skip_count} skipped | {fail_count} failed | "
          f"{elapsed:.1f}s total")

    # Save report
    os.makedirs("reports", exist_ok=True)
    report_path = f"reports/test_{case['id']}_{report.report_id}.json"
    with open(report_path, "w") as f:
        json.dump(report.to_dict(), f, indent=2, default=str)
    print(GREEN(f"  Report saved: {report_path}"))

    return {
        "case_id":    case["id"],
        "passed":     pass_count,
        "skipped":    skip_count,
        "failed":     fail_count,
        "findings":   total_findings,
        "high":       high_priority,
        "elapsed":    elapsed,
        "report_path":report_path,
    }


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Inkognito test runner")
    parser.add_argument("--case",    type=int, help="Run a specific test case (1–4)")
    parser.add_argument("--dry",     action="store_true", help="Dry run — check setup only")
    parser.add_argument("--modules", action="store_true", help="List all modules")
    parser.add_argument("--cases-file", default=DEFAULT_TEST_CASES_FILE,
                        help=f"Path to test cases JSON (default: {DEFAULT_TEST_CASES_FILE})")
    args = parser.parse_args()

    print(BOLD(CYAN("\n  Inkognito — Test Runner")))
    print(DIM(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"))

    ok, errors = check_imports()
    if not ok:
        print(RED("\nFix import errors above before running tests."))
        sys.exit(1)

    configured, total_required = check_env()

    if args.modules:
        print(BOLD("\nAll modules:"))
        modules = [
            ("1", "eCourts",               "Always", "LEGALKART_API_KEY"),
            ("2", "MCA21",                 "Always", "MCA_API_KEY"),
            ("3", "GST",                   "Always", "—"),
            ("4", "Google Search",         "Always", "SERP_API_KEY"),
            ("5", "Property Records",      "Delhi/UP location", "CAPTCHA_BYPASS_ENABLED=True + CAPTCHA_API_KEY (UP only)"),
            ("6", "Social Media",          "Always", "SERP_API_KEY (for URL discovery)"),
            ("7", "Reverse Image Search",  "photo_path set", "SERP_API_KEY + IMGBB_API_KEY"),
            ("8", "Phone Intelligence",    "mobile set", "—"),
            ("9", "Matrimonial Cross-check","Always", "SERP_API_KEY"),
            ("10","NCDRC",                 "business_name set", "—"),
            ("11","NCLT",                  "business_name set", "LEGALKART_API_KEY"),
            ("12","SEBI",                  "finance role detected", "—"),
            ("13","EPFO",                  "employer_name set", "—"),
        ]
        print(f"  {'#':<4} {'Module':<28} {'Trigger':<25} {'Key needed'}")
        print(f"  {'-'*80}")
        for n, name, trigger, key in modules:
            print(f"  {n:<4} {name:<28} {trigger:<25} {DIM(key)}")
        return

    if args.dry:
        print(BOLD("\n[DRY RUN] Checking setup only — no API calls will be made."))
        if configured == total_required:
            print(GREEN("\n✓ All required keys configured. Ready to run."))
        else:
            print(YELLOW(f"\n⚠ {total_required - configured} required key(s) missing."))
            print("  Pipeline will run but affected modules will fail.")
        return

    try:
        test_cases = load_test_cases(args.cases_file)
    except Exception as e:
        print(RED(f"\nFailed to load test cases: {e}"))
        sys.exit(1)

    # Select test cases
    if args.case:
        cases = [c for c in test_cases if c["id"] == args.case]
        if not cases:
            print(RED(f"Test case {args.case} not found. Valid: 1–{len(test_cases)}"))
            sys.exit(1)
    else:
        cases = test_cases

    print(BOLD(f"\nRunning {len(cases)} test case(s)...\n"))

    results = []
    for case in cases:
        try:
            result = run_test(case, dry=args.dry)
            results.append(result)
        except KeyboardInterrupt:
            print(YELLOW("\nInterrupted."))
            break
        except Exception as e:
            print(RED(f"\nTest {case['id']} crashed: {e}"))
            import traceback
            traceback.print_exc()
            results.append({"case_id": case["id"], "crashed": True, "error": str(e)})

    # Final summary
    print(BOLD(f"\n{'='*60}"))
    print(BOLD("FINAL SUMMARY"))
    print(f"{'='*60}")
    for r in results:
        if r.get("crashed"):
            print(RED(f"  Case {r['case_id']}: CRASHED — {r.get('error','')}"))
        elif r.get("dry"):
            print(DIM(f"  Case {r['case_id']}: [dry run]"))
        else:
            high_str = RED(f"{r['high']} HIGH") if r['high'] else DIM("0 HIGH")
            print(
                f"  Case {r['case_id']}: "
                f"{GREEN(str(r['passed']))} ran, "
                f"{DIM(str(r['skipped']))} skipped, "
                f"{RED(str(r['failed'])) if r['failed'] else DIM('0')} failed | "
                f"{r['findings']} findings ({high_str}) | "
                f"{r['elapsed']:.1f}s"
            )

    print()


if __name__ == "__main__":
    main()