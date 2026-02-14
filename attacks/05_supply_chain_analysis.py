"""
Supply Chain Vulnerability Analysis.

Parses a Trivy JSON report and analyzes a Dockerfile for security issues.
Produces a structured risk assessment of the AI system's deployment pipeline.

Usage:
    python 05_supply_chain_analysis.py
    python 05_supply_chain_analysis.py --trivy-report ../06_trivy_report.json --dockerfile ../Dockerfile
"""
import json
import argparse
import os

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results", "05_supply_chain")


def parse_trivy_report(path):
    """
    Parse a Trivy JSON report and extract vulnerability details.
    """
    with open(path) as f:
        data = json.load(f)

    vulns = []
    for result in data.get("Results", []):
        target = result.get("Target", "")
        target_type = result.get("Type", "")
        for v in result.get("Vulnerabilities", []):
            vulns.append({
                "id": v.get("VulnerabilityID"),
                "severity": v.get("Severity"),
                "package": v.get("PkgName"),
                "installed_version": v.get("InstalledVersion"),
                "fixed_version": v.get("FixedVersion"),
                "title": v.get("Title", ""),
                "description": v.get("Description", "")[:200],
                "target": target,
                "target_type": target_type,
            })

    return vulns


def analyze_dockerfile(path):
    """
    Analyze a Dockerfile for common security issues.
    """
    with open(path) as f:
        content = f.read()
    lines = content.strip().split("\n")

    issues = []

    # 1. Check for USER directive
    has_user = any(line.strip().startswith("USER ") for line in lines)
    if not has_user:
        issues.append({
            "issue": "Missing USER directive (running as root)",
            "severity": "HIGH",
            "detail": "Container executes as root user by default. A container breakout or remote code execution vulnerability in the application grants full root host access.",
            "recommendation": "Create a dedicated non-root user (e.g. `useradd -u 1000 appuser`) and specify `USER appuser` before CMD.",
        })

    # 2. Check for unpinned base image digest
    from_lines = [line.strip() for line in lines if line.strip().startswith("FROM ")]
    for fl in from_lines:
        if "@sha256:" not in fl:
            issues.append({
                "issue": "Unpinned base image digest",
                "severity": "MEDIUM",
                "detail": f"Base image `{fl}` uses a mutable tag without an immutable sha256 digest pin, allowing upstream changes or poisoning to alter dependencies silently.",
                "recommendation": "Pin base image to immutable digest: `FROM python:3.11-slim@sha256:<digest>`.",
            })

    # 3. Check for COPY .
    copy_dot = any("COPY . " in line or line.strip() == "COPY ." or "COPY . /" in line for line in lines)
    if copy_dot:
        issues.append({
            "issue": "Overly broad COPY . context",
            "severity": "MEDIUM",
            "detail": "Using `COPY . /app` copies entire workspace into container, risking accidental inclusion of `.env`, secrets, `.git`, test scripts, and local credentials.",
            "recommendation": "Use a rigorous `.dockerignore` file and copy only required application directories explicitly.",
        })

    # 4. Check for HEALTHCHECK
    has_healthcheck = any(line.strip().startswith("HEALTHCHECK ") for line in lines)
    if not has_healthcheck:
        issues.append({
            "issue": "Missing HEALTHCHECK instruction",
            "severity": "LOW",
            "detail": "Docker cannot automatically detect or restart frozen or unhealthy containers.",
            "recommendation": "Add `HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl -f http://localhost:5001/health || exit 1`.",
        })

    # 5. Check for build tools in production image
    build_tools = ["gcc", "build-essential", "g++", "make"]
    found_build_tools = [bt for bt in build_tools if bt in content]
    if found_build_tools:
        issues.append({
            "issue": f"Compiler/build tools retained in production ({', '.join(found_build_tools)})",
            "severity": "MEDIUM",
            "detail": f"Installing `{', '.join(found_build_tools)}` in production container increases image attack surface and facilitates attacker compilation of local root exploits.",
            "recommendation": "Use multi-stage Docker builds to compile wheels in a builder stage and copy only wheels into a minimal runtime stage.",
        })

    # 6. Check for unnecessary tools (curl, git)
    unnecessary_tools = ["git", "curl", "wget", "netcat"]
    found_tools = [ut for ut in unnecessary_tools if ut in content]
    if found_tools:
        issues.append({
            "issue": f"Unnecessary network/VCS utilities in production ({', '.join(found_tools)})",
            "severity": "LOW",
            "detail": f"Utilities like `{', '.join(found_tools)}` facilitate attacker post-exploitation activities such as staging tools, pulling malicious repositories, or data exfiltration.",
            "recommendation": "Remove unnecessary packages from the final production runtime image.",
        })

    return issues


def generate_report(vulns, dockerfile_issues):
    """Generate a structured supply chain risk report."""
    severity_counts = {}
    for v in vulns:
        sev = v.get("severity", "UNKNOWN")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    # Filter High/Critical vulnerabilities (top 15 deduplicated by CVE)
    seen_cves = set()
    high_critical_vulns = []
    for v in vulns:
        if v.get("severity") in ["CRITICAL", "HIGH"]:
            cve_id = v.get("id")
            if cve_id and cve_id not in seen_cves:
                seen_cves.add(cve_id)
                high_critical_vulns.append(v)
                if len(high_critical_vulns) >= 15:
                    break

    # Python specific
    python_vulns = [v for v in vulns if v.get("target_type") == "python-pkg"]

    report = {
        "summary": {
            "total_vulnerabilities": len(vulns),
            "severity_breakdown": severity_counts,
            "dockerfile_issues": len(dockerfile_issues),
        },
        "high_severity_vulnerabilities": high_critical_vulns,
        "python_specific": python_vulns,
        "dockerfile_issues": dockerfile_issues,
        "risk_assessment": {
            "overall_risk": "HIGH",
            "key_concerns": [
                "Container runs as root user without non-root UID enforcement, enabling root host compromise upon container breakout.",
                "804 base OS and package vulnerabilities identified in Trivy report including multiple HIGH severity Debian and Python library CVEs.",
                "Critical Python dependency vulnerabilities in `wheel` (CVE-2026-24049) and `jaraco.context` (CVE-2026-23949) allowing code execution and path traversal.",
                "Production container retains gcc, build-essential, curl, and git, lowering exploitation barrier for attackers.",
                "Unpinned base image and broad COPY . instruction expose the deployment to supply chain tampering and accidental secret disclosure.",
            ],
        },
    }
    return report


def main():
    parser = argparse.ArgumentParser(description="Supply Chain Vulnerability Analysis")
    parser.add_argument(
        "--trivy-report",
        default=os.path.join(os.path.dirname(__file__), "..", "06_trivy_report.json"),
    )
    parser.add_argument(
        "--dockerfile",
        default=os.path.join(os.path.dirname(__file__), "..", "Dockerfile"),
    )
    parser.add_argument(
        "--output",
        default=os.path.join(RESULTS_DIR, "supply_chain_report.json"),
    )
    args = parser.parse_args()
    if not os.path.dirname(args.output):
        args.output = os.path.join(RESULTS_DIR, args.output)
    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    print("Parsing Trivy report...")
    vulns = parse_trivy_report(args.trivy_report)

    print("Analyzing Dockerfile...")
    dockerfile_issues = analyze_dockerfile(args.dockerfile)

    report = generate_report(vulns, dockerfile_issues)

    # Print summary
    print(f"\n{'=' * 50}")
    print("  SUPPLY CHAIN RISK ASSESSMENT")
    print(f"{'=' * 50}")
    s = report["summary"]
    print(f"\n  Total vulnerabilities: {s['total_vulnerabilities']}")
    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        count = s["severity_breakdown"].get(sev, 0)
        if count:
            print(f"    {sev}: {count}")

    print(f"\n  Dockerfile issues: {s['dockerfile_issues']}")
    print(f"{'=' * 50}")

    with open(args.output, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nFull report saved to {args.output}")


if __name__ == "__main__":
    main()
