#!/usr/bin/env python3
"""
Interactive Resume Builder
Saves master profile to ~/resume_profile.json
Run: python3 resume_builder.py
Deps: pip install InquirerPy reportlab rich requests beautifulsoup4
Optional (better role suggestions): install Ollama + run: ollama pull llama3.2
"""

import json
import os
import re
import sys
import platform
import subprocess
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from InquirerPy import inquirer
from InquirerPy.base.control import Choice

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_CENTER

console = Console()

# ── Paths ──────────────────────────────────────────────────────────────────────
PROFILE_PATH = Path.home() / "resume_profile.json"

def _default_output_dir() -> Path:
    """Return the OS-appropriate default output directory."""
    system = platform.system()
    if system == "Windows":
        base = Path(os.environ.get("USERPROFILE", Path.home())) / "Documents"
    elif system == "Darwin":
        base = Path.home() / "Documents"
    else:
        base = Path.home() / "Documents"
    return base / "Resumes"

# ── Colors (ReportLab) ─────────────────────────────────────────────────────────
RL_BLACK  = colors.HexColor("#1a1a1a")
RL_ACCENT = colors.HexColor("#1f4e79")
RL_GRAY   = colors.HexColor("#555555")

# ── ATS summary templates ──────────────────────────────────────────────────────
# Keyed by lowercase keywords found in the role title.
# The first match wins; "default" is the fallback.
# {role} is replaced with the exact title the user typed.
SUMMARY_TEMPLATES = {
    "security|soc|analyst|cybersecurity|cyber": (
        "{role} with hands-on threat detection, log analysis, and incident response experience. "
        "Performed live PCAP analysis (Wireshark), built Python-based detection functions (TP=5, FN=0, FP=0), "
        "and competed in the Ivy Tech Statewide IT Challenge — Cybersecurity Category (Nov 2026). "
        "Pursuing AAS in Cybersecurity / Cyber Assurance at Ivy Tech; CompTIA A+ in progress, Network+ scheduled, Security+ planned. "
        "Proficient in SIEM concepts, firewall management, SSH hardening, and HackTheBox / TryHackMe labs. "
        "Accurate documentation and clear written reporting under time pressure."
    ),
    "network|noc|infrastructure|systems": (
        "{role} with practical experience configuring TCP/IP networks, DNS (A/CNAME/MX/NS), DHCP, "
        "port forwarding, OpenVPN, and UFW firewall rules from scratch. "
        "Provisioned and hardened Ubuntu VPS servers; managed Apache virtual hosts, systemd services, and MySQL. "
        "Built routed networks in Cisco Packet Tracer; pursuing CompTIA Network+ (scheduled). "
        "Pursuing AAS in Cybersecurity at Ivy Tech; strong written and verbal communication; valid driver's license."
    ),
    "cloud|devops|aws|azure|gcp": (
        "{role} with self-directed experience deploying and managing cloud-adjacent Linux infrastructure — "
        "VPS provisioning, LAMP stack configuration, DNS management, and automated service startup via systemd. "
        "Scripting background in Python and Bash; comfortable with SSH, UFW, and remote server administration. "
        "Pursuing AAS in Cybersecurity at Ivy Tech; CompTIA A+ in progress, Network+ scheduled. "
        "Fast learner, detail-oriented, strong documentation habits."
    ),
    "developer|software|web|frontend|backend|fullstack|full-stack": (
        "{role} with hands-on experience in Python, JavaScript (Node.js), Bash, and MySQL. "
        "Built and deployed LAMP stack web environments on self-managed VPS servers; "
        "implemented DNS, Apache virtual hosts, and systemd service management end-to-end. "
        "Strong Linux CLI proficiency across Ubuntu, RHEL, Kali, and Arch-based distributions. "
        "Pursuing AAS in Cybersecurity at Ivy Tech; committed to clean code, accurate documentation, and reliable delivery."
    ),
    "support|help desk|helpdesk|desktop|technician|specialist|tier": (
        "{role} with hands-on experience installing, diagnosing, and repairing "
        "personal computer hardware and software systems. "
        "Self-built and administered VPS servers, LAMP stack environments, and DNS configurations from scratch. "
        "Pursuing AAS in Cybersecurity at Ivy Tech; CompTIA A+ in progress, Network+ scheduled. "
        "Competed in the Ivy Tech Statewide IT Challenge (Nov 2026). "
        "Strong customer service and communication skills; calm under pressure, accurate with documentation. "
        "Valid driver's license; willing to travel to multiple sites."
    ),
    "default": (
        "{role} with broad hands-on IT experience spanning hardware repair, Linux server administration, "
        "networking, scripting, and cybersecurity fundamentals. "
        "Self-directed learner — built LAMP stacks, configured DNS end-to-end, administered VPS servers, "
        "and competed in the Ivy Tech Statewide IT Challenge (Nov 2026). "
        "Pursuing AAS in Cybersecurity / Cyber Assurance at Ivy Tech; CompTIA A+ in progress, Network+ scheduled. "
        "Reliable, detail-oriented, and effective communicator; valid driver's license."
    ),
}

def pick_summary_template(role: str) -> str:
    """Return the best-matching summary template for the given role title."""
    role_lower = role.lower()
    for pattern, template in SUMMARY_TEMPLATES.items():
        if pattern == "default":
            continue
        if any(kw in role_lower for kw in pattern.split("|")):
            return template.format(role=role)
    return SUMMARY_TEMPLATES["default"].format(role=role)

# ── Role-based ATS skill suggestions ──────────────────────────────────────────
# Each key is a pipe-separated list of lowercase trigger words matched against
# the role title. Values are lists of (label, description) skill suggestions.
# These are prompts only — the user confirms each one with their own experience.
ROLE_SKILL_SUGGESTIONS = {
    "forklift|warehouse|logistics|freight|shipping|receiving|driver|delivery": [
        ("Forklift Operation",        "Certified forklift operator (sit-down/stand-up/reach); loading, unloading, stacking"),
        ("Inventory Management",      "Cycle counts, barcode scanning, RF gun, WMS software, stock reconciliation"),
        ("Safety & Compliance",       "OSHA forklift certification, PPE usage, incident reporting, safety checklists"),
        ("Physical Stamina",          "Ability to lift 50+ lbs; sustained physical activity across full shift"),
        ("Documentation",             "BOL verification, shipping manifests, driver documentation accuracy"),
        ("Route & Stop Management",   "High-volume daily stop routes, time management, customer-facing issue resolution"),
        ("Vehicle Operation",         "Valid driver's license, DOT compliance, pre-trip vehicle inspection"),
        ("Team Collaboration",        "Coordinating with dispatch, dock supervisors, and drivers"),
    ],
    "support|help.?desk|helpdesk|desktop|technician|specialist|tier": [
        ("Hardware Troubleshooting",  "Diagnosis and repair of desktops, laptops, peripherals, printers"),
        ("Operating Systems",         "Windows 10/11 installation, imaging, configuration, troubleshooting"),
        ("Ticketing Systems",         "Incident triage, escalation paths, SLA tracking, documentation"),
        ("Remote Support",            "RDP, SSH, screen-share tools; guiding non-technical users step by step"),
        ("Active Directory",          "User account management, password resets, group policy, OU structure"),
        ("Networking Basics",         "TCP/IP, DNS, DHCP, VPN, Wi-Fi troubleshooting at the endpoint level"),
        ("Customer Communication",    "Calm, clear communication with end users; translating technical issues"),
        ("Documentation",             "Runbooks, SOPs, incident reports, knowledge base articles"),
    ],
    "security|soc|analyst|cybersecurity|cyber": [
        ("SIEM & Log Analysis",       "Log review, alert triage, event correlation, false positive reduction"),
        ("Network Traffic Analysis",  "Wireshark PCAP analysis, protocol inspection, C2 detection"),
        ("Incident Response",         "IR lifecycle: identification, containment, eradication, recovery, lessons learned"),
        ("Threat Intelligence",       "IOC identification, attacker fingerprinting, TTP mapping to MITRE ATT&CK"),
        ("Vulnerability Management",  "Scanning, risk prioritization, patch validation, remediation tracking"),
        ("Scripting for Detection",   "Python detection scripts, Bash automation, regex for log parsing"),
        ("Firewall & Access Control", "Firewall policy review, UFW/iptables, least-privilege enforcement"),
        ("Compliance Awareness",      "HIPAA, PCI-DSS, NIST CSF, evidence collection for audits"),
    ],
    "network|noc|infrastructure|systems": [
        ("Routing & Switching",       "TCP/IP, VLANs, inter-VLAN routing, STP, static and dynamic routing"),
        ("DNS & DHCP",                "Zone management, A/CNAME/MX/NS records, DHCP scopes, lease management"),
        ("Firewall Configuration",    "ACLs, UFW/iptables rules, NAT, port forwarding, VPN tunnels"),
        ("Network Monitoring",        "SNMP, syslog, ping/traceroute, bandwidth monitoring, alerting"),
        ("Linux Server Admin",        "SSH hardening, systemd, cron, log rotation, package management"),
        ("Cisco Packet Tracer",       "Simulated routed networks with routers, switches, PCs, VLANs"),
        ("Documentation",             "Network diagrams, runbooks, change logs, IP address management"),
        ("Troubleshooting",           "Systematic fault isolation across OSI layers; root-cause analysis"),
    ],
    "cloud|devops|aws|azure|gcp": [
        ("Cloud Infrastructure",      "EC2/compute instances, object storage, IAM, security groups"),
        ("Linux Administration",      "VPS provisioning, SSH, UFW, systemd, cron, log management"),
        ("Scripting & Automation",    "Python/Bash automation, cron jobs, infrastructure-as-code concepts"),
        ("CI/CD Concepts",            "Pipeline awareness, build/test/deploy stages, Git branching strategies"),
        ("Containerization",          "Docker basics — images, containers, volumes, networking"),
        ("Monitoring & Logging",      "CloudWatch/Stackdriver concepts, centralized logging, alerting"),
        ("DNS & SSL",                 "DNS propagation, Let's Encrypt SSL/TLS certificate management"),
        ("Security Basics",           "IAM least privilege, security group rules, secrets management"),
    ],
    "developer|software|web|frontend|backend|fullstack|full-stack": [
        ("Python",                    "Scripts, automation, data parsing, web frameworks (Flask/Django concepts)"),
        ("JavaScript / Node.js",      "Server-side JS, npm, async patterns, REST API consumption"),
        ("SQL / MySQL",               "Schema design, CRUD operations, stored procedures, remote admin"),
        ("Git & Version Control",     "Branching, merging, pull requests, GitHub collaboration"),
        ("Linux CLI",                 "File system navigation, permissions, process management, shell scripting"),
        ("REST APIs",                 "HTTP methods, JSON, API testing with curl/Postman"),
        ("Web Server Config",         "Apache virtual hosts, reverse proxy, SSL termination"),
        ("Debugging & Testing",       "Unit test concepts, error tracing, event viewer / log analysis"),
    ],
    "customer|service|sales|retail|call.?center|agent|representative": [
        ("Customer Communication",    "High-volume inbound/outbound calls; de-escalation; clear written follow-up"),
        ("CRM & Ticketing",           "Logging interactions, case management, follow-through to resolution"),
        ("Data Entry & Accuracy",     "Policy entry, form completion, compliance documentation"),
        ("Product Knowledge",         "Rapid onboarding to new products; training others on tools and policy"),
        ("Performance Metrics",       "Call handle time, CSAT, QA scores, ranked against team benchmarks"),
        ("Compliance",                "PII handling, regulatory requirements, script adherence"),
        ("Upselling / Retention",     "Identifying needs, presenting options, retaining accounts"),
        ("Team Collaboration",        "Shift handoffs, escalation coordination, peer training"),
    ],
    "manager|lead|supervisor|coordinator": [
        ("Team Leadership",           "Supervising staff, assigning tasks, performance feedback"),
        ("Scheduling",                "Shift planning, coverage management, time-off coordination"),
        ("Conflict Resolution",       "Mediating team disputes, customer escalations, disciplinary action"),
        ("Training & Onboarding",     "New hire orientation, skill development, SOP documentation"),
        ("Reporting & Metrics",       "KPI tracking, shift reports, inventory or operational summaries"),
        ("Process Improvement",       "Identifying inefficiencies, proposing changes, documenting new procedures"),
        ("Budget Awareness",          "Cost control, waste reduction, labor hour management"),
        ("Cross-functional Comms",    "Coordinating with other departments, vendors, and upper management"),
    ],
}

def _get_role_suggestions(role: str) -> list[tuple[str, str]]:
    """Return ATS skill suggestions for a given role title (empty list if no match)."""
    role_lower = role.lower()
    for pattern, suggestions in ROLE_SKILL_SUGGESTIONS.items():
        if any(re.search(kw, role_lower) for kw in pattern.split("|")):
            return suggestions
    return []

def _ollama_role_suggestions(role: str) -> list[tuple[str, str]] | None:
    """
    Try to get role suggestions from a local Ollama instance.
    Returns list of (label, description) tuples, or None if Ollama is unavailable.
    """
    try:
        import urllib.request, json as _json
        prompt = (
            f"List 8 ATS resume skill categories for a '{role}' role. "
            "For each, give a short label (2-4 words) and a one-line description of specific skills. "
            "Format strictly as: LABEL: description (one per line, no bullets, no numbering, no extra text)."
        )
        payload = _json.dumps({"model": "llama3.2", "prompt": prompt, "stream": False}).encode()
        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = _json.loads(resp.read())
        lines = [l.strip() for l in data.get("response", "").splitlines() if ":" in l and l.strip()]
        results = []
        for line in lines[:10]:
            parts = line.split(":", 1)
            if len(parts) == 2:
                results.append((parts[0].strip(), parts[1].strip()))
        return results if results else None
    except Exception:
        return None

def suggest_role_skills(role: str, cfg: dict, profile: dict) -> None:
    """
    Show ATS skill suggestions for the given role.
    User checks off only what they genuinely have. Nothing is added silently.
    """
    # Try Ollama first, fall back to dictionary
    suggestions = _ollama_role_suggestions(role)
    source = "Ollama (local AI)" if suggestions else None
    if not suggestions:
        suggestions = _get_role_suggestions(role)
        source = "built-in dictionary" if suggestions else None

    if not suggestions:
        console.print(f"  [dim]No role suggestions available for '{role}' — skipping.[/dim]\n")
        return

    console.print(f"  [dim]Suggestions from {source}. Check only skills you genuinely have.[/dim]\n")

    choices = [
        Choice(value=i, name=f"{label}: {desc}", enabled=False)
        for i, (label, desc) in enumerate(suggestions)
    ]
    selected_idx = inquirer.checkbox(
        message=f"Which of these do you actually have experience with?",
        choices=choices,
        transformer=lambda r: f"{len(r)} selected" if r else "none selected — skipping",
    ).execute()

    for i in selected_idx:
        label, desc = suggestions[i]
        console.print(f"\n  [bold]'{label}'[/bold]")
        console.print(f"  [dim]Suggested: {desc}[/dim]")
        console.print(f"  [dim]Describe your real experience (be specific — when, where, outcome):[/dim]")
        value = inquirer.text(
            message=f"  Your '{label}' experience:",
            default=desc,
        ).execute().strip()
        if value:
            new_skill = {"label": label, "value": value}
            cfg["skills"].append(new_skill)
            console.print(f"  [green]✓ Added '{label}'[/green]")
            if inquirer.confirm(message="  Save to master profile for future resumes?", default=False).execute():
                profile["skills"].append(new_skill)
                save_profile(profile)
                console.print("  [green]✓ Saved to master profile[/green]")

# ── Default master profile ─────────────────────────────────────────────────────
DEFAULT_PROFILE = {
    "name": "Terrence Fleming",
    "contact": (
        "Danville, IN 46122  ·  812-671-7216  ·  Terrence.fleming.it@gmail.com  ·  "
        "linkedin.com/in/terrence-fleming-it  ·  github.com/StrykrrYT"
    ),
    "skills": [
        # ── Core IT ──
        {
            "label": "Operating Systems",
            "value": "Windows 10/11 (domain & workgroup), Windows Server concepts; "
                     "Linux — Ubuntu LTS, RHEL, Kali, CachyOS (Arch); "
                     "CLI proficient across distros; OS installation, imaging, and configuration",
        },
        {
            "label": "Hardware & Peripherals",
            "value": "PC component installation, replacement, and repair; "
                     "hardware diagnostics, peripheral setup, driver troubleshooting; "
                     "laptop screen/keyboard/battery replacement; "
                     "remote desktop support (RDP/SSH/TeamViewer)",
        },
        {
            "label": "Networking",
            "value": "TCP/IP, DNS (A/CNAME/MX/NS), DHCP, static IP assignment, "
                     "SOHO router/gateway config, port forwarding, VLANs, "
                     "OpenVPN, UFW/iptables firewall; "
                     "nslookup, ipconfig, ping, tracert, netstat; Cisco Packet Tracer",
        },
        {
            "label": "Server & Infrastructure",
            "value": "LAMP stack (Linux/Apache/MySQL/PHP), VPS provisioning from scratch, "
                     "SSH hardening, UFW rules, systemd service management, "
                     "Apache virtual hosts, cron jobs, log rotation",
        },
        # ── Security ──
        {
            "label": "Cybersecurity",
            "value": "Wireshark (PCAP/C2 traffic analysis), firewall policy config, "
                     "log analysis, SSH hardening, vulnerability scanning concepts; "
                     "SIEM fundamentals, incident response lifecycle, "
                     "HackTheBox, TryHackMe; Ivy Tech Statewide IT Challenge (Nov 2026)",
        },
        {
            "label": "Identity & Access",
            "value": "Active Directory concepts (user/group management, GPO, OU structure), "
                     "account provisioning/deprovisioning, MFA, "
                     "principle of least privilege; password policy enforcement",
        },
        # ── Cloud / Virtualization ──
        {
            "label": "Virtualization",
            "value": "VirtualBox, VMware Workstation (VM creation, snapshots, networking); "
                     "basic container concepts (Docker); "
                     "hypervisor types I & II awareness",
        },
        {
            "label": "Cloud Platforms",
            "value": "AWS fundamentals (EC2, S3, IAM — conceptual); "
                     "cloud-adjacent Linux VPS admin (DigitalOcean/Vultr-style); "
                     "DNS propagation, SSL/TLS certificate installation (Let's Encrypt)",
        },
        # ── Dev / Scripting ──
        {
            "label": "Scripting & Development",
            "value": "Python (automation, detection scripts, data parsing), "
                     "Bash (shell scripting, cron, system tasks), "
                     "JavaScript / Node.js; "
                     "MySQL (schema design, CRUD, remote admin, stored procedures); "
                     "Git / GitHub version control",
        },
        # ── Help Desk / Support Tools ──
        {
            "label": "Help Desk & Ticketing",
            "value": "IssueTrax (issue tracking and resolution workflow); "
                     "familiar with ServiceNow and Jira concepts; "
                     "incident triage, escalation paths, SLA awareness; "
                     "remote support tooling (RDP, SSH, screen-share)",
        },
        {
            "label": "Troubleshooting Methodology",
            "value": "CompTIA A+ 6-step troubleshooting model; "
                     "root-cause analysis, systematic isolation of hardware vs. software vs. network faults; "
                     "clear end-user communication throughout resolution",
        },
        # ── Compliance / Documentation ──
        {
            "label": "Compliance & Data Privacy",
            "value": "PII/PHI data handling (HIPAA awareness); "
                     "PCI-DSS concepts; "
                     "strict data compliance during licensed insurance role (Progressive); "
                     "chain-of-custody documentation",
        },
        {
            "label": "Technical Documentation",
            "value": "Network diagrams, runbooks, incident reports, SOPs; "
                     "Markdown and plain-text documentation; "
                     "Microsoft Office (Word, Excel, Outlook); accurate recordkeeping",
        },
        # ── Soft Skills / General ──
        {
            "label": "Customer Service & Communication",
            "value": "High-volume inbound call handling (insurance contact center); "
                     "calm and clear under pressure; "
                     "ranked #3/15 on performance metrics; "
                     "experience translating technical issues for non-technical users",
        },
        {
            "label": "Audio/Visual & Media",
            "value": "OBS Studio (stream/recording setup, scene management, audio routing); "
                     "basic video editing; "
                     "Discord bot hosting and server administration",
        },
        {
            "label": "Physical & Logistics",
            "value": "Valid driver's license; willing to travel to multiple sites; "
                     "certified forklift operator; "
                     "ability to lift 50+ lbs; "
                     "DOT-compliant delivery operations (120–160 stops/day, zero safety incidents)",
        },
    ],
    "education": [
        {
            "degree": "AAS Cybersecurity / Cyber Assurance",
            "school": "Ivy Tech Community College",
            "dates":  "Aug 2025 – Dec 2027",
            "note":   "Online; coursework directly maps to CompTIA A+, Network+, and Security+ objectives",
        }
    ],
    "certifications": [
        "CompTIA A+ — In Progress",
        "CompTIA Network+ — Scheduled",
        "CompTIA Security+ — Planned",
    ],
    "projects": [
        {
            "title": "Ivy Tech Statewide IT Challenge — Cybersecurity Category (Nov 2026)",
            "meta":  "Team 12 — Network Analyst / Detection Engineer",
            "bullets": [
                "Analyzed logs and audit events to identify a compromised account; isolated attacker IP and anomalous fingerprint.",
                "Live PCAP analysis in Wireshark — identified C2 HTTP POST beacon, extracted payload from HTTP layer.",
                "Python detection function: TP=5, FN=0, FP=0. Authored incident containment report for simulated PHI/PII breach; all phases passed.",
            ],
        },
        {
            "title": "Homelab & Personal Infrastructure — Self-Directed (Ongoing)",
            "meta":  "",
            "bullets": [
                "Provisioned Ubuntu LTS VPS servers from scratch via SSH; configured UFW firewall, static IPs, MySQL, and systemd services.",
                "Built full LAMP stack (Apache, MySQL, PHP); complete DNS config — A/CNAME/MX records, nameserver delegation, company email.",
                "Configured OpenVPN, port forwarding, router/gateway management, and Discord bot hosting on self-managed infrastructure.",
                "Built routed networks in Cisco Packet Tracer — routers, switches, PCs, and laptops with VLAN and inter-VLAN routing.",
            ],
        },
        {
            "title": "resume_builder — Open Source CLI Tool (github.com/StrykrrYT/resume-builder)",
            "meta":  "Python · InquirerPy · ReportLab · Rich",
            "bullets": [
                "Built an interactive 6-step CLI wizard that generates tailored, ATS-optimized PDF resumes from a JSON master profile.",
                "Role-aware summary templates auto-select based on job title keywords (support, security, network, cloud, dev).",
                "Supports adding new jobs, projects, and skill categories on the fly with optional save-back to master profile.",
            ],
        },
    ],
    "jobs": [
        {
            "title":   "Delivery Associate",
            "company": "3-Pete Logistics LLC / Index Distributors Inc. (Amazon DSP)",
            "dates":   "May 2026 – Sep 2026",
            "bullets": [
                "Operated Sprinter van routes (120–160 stops/day) across multiple sites with zero safety incidents.",
                "Resolved customer issues in the field; maintained valid driver's license and DOT compliance throughout.",
            ],
        },
        {
            "title":   "Licensed Insurance Agent",
            "company": "Foundever LLC (Progressive)",
            "dates":   "Oct 2024 – May 2025",
            "bullets": [
                "Handled high-volume inbound calls; provided technical assistance and training to system users on policy and software tools.",
                "Ranked #3 of 15 team members on performance metrics; maintained strict PII/data compliance under state and federal regulations.",
            ],
        },
        {
            "title":   "Forklift Operator",
            "company": "R+L Carriers",
            "dates":   "June 2023 – Jan 2024",
            "bullets": [
                "Certified forklift operator — loading/unloading and inventory management; routinely moved equipment up to 50+ lbs.",
                "Verified driver documentation and BOL accuracy; maintained warehouse safety standards.",
            ],
        },
        {
            "title":   "Shift Lead",
            "company": "Dairy Queen",
            "dates":   "Feb 2022 – May 2023",
            "bullets": [
                "Supervised team operations, scheduling, and cash handling; demonstrated reliability and leadership under pressure.",
            ],
        },
    ],
}

# ── Profile helpers ────────────────────────────────────────────────────────────
def load_profile() -> dict:
    if PROFILE_PATH.exists():
        with open(PROFILE_PATH) as f:
            return json.load(f)
    profile = json.loads(json.dumps(DEFAULT_PROFILE))
    save_profile(profile)
    return profile

def save_profile(profile: dict):
    with open(PROFILE_PATH, "w") as f:
        json.dump(profile, f, indent=2)

def get_output_dir(profile: dict) -> Path:
    """
    Return the configured output directory, creating it if needed.
    On first run (no 'output_dir' key in profile) ask the user to choose.
    """
    if "output_dir" in profile:
        return Path(profile["output_dir"])

    default = _default_output_dir()
    console.print(Rule("[bold]First-Run Setup — Output Directory[/bold]", style="navy_blue"))
    console.print(
        f"[dim]Where should your finished PDF resumes be saved?\n"
        f"Default: [cyan]{default}[/cyan][/dim]\n"
    )
    chosen = inquirer.text(
        message="Output directory (press Enter to use default):",
        default=str(default),
    ).execute().strip()

    out_dir = Path(chosen) if chosen else default
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"[green]✓ Output directory set to: {out_dir}[/green]\n")
    except Exception as e:
        console.print(f"[yellow]Warning: could not create '{out_dir}': {e} — using default.[/yellow]")
        out_dir = default
        out_dir.mkdir(parents=True, exist_ok=True)

    profile["output_dir"] = str(out_dir)
    save_profile(profile)
    return out_dir

# ── PDF styles ─────────────────────────────────────────────────────────────────
def make_styles() -> dict:
    return {
        "name":      ParagraphStyle("name", fontName="Helvetica-Bold", fontSize=18,
                         leading=22, textColor=RL_ACCENT, alignment=TA_CENTER, spaceBefore=0, spaceAfter=2),
        "contact":   ParagraphStyle("contact", fontName="Helvetica", fontSize=9,
                         leading=12, textColor=RL_GRAY, alignment=TA_CENTER, spaceAfter=3),
        "section":   ParagraphStyle("section", fontName="Helvetica-Bold", fontSize=10,
                         textColor=RL_ACCENT, spaceBefore=2, spaceAfter=2),
        "job_title": ParagraphStyle("job_title", fontName="Helvetica-Bold", fontSize=9.5,
                         textColor=RL_BLACK, spaceBefore=2, spaceAfter=0, keepWithNext=1),
        "job_meta":  ParagraphStyle("job_meta", fontName="Helvetica-Oblique", fontSize=8.5,
                         textColor=RL_GRAY, spaceAfter=1, keepWithNext=1),
        "bullet":    ParagraphStyle("bullet", fontName="Helvetica", fontSize=9,
                         textColor=RL_BLACK, leftIndent=12, firstLineIndent=-8, spaceAfter=1, leading=11.5),
        "summary":   ParagraphStyle("summary", fontName="Helvetica", fontSize=9,
                         textColor=RL_BLACK, spaceAfter=2, leading=12.5),
        "skill_row": ParagraphStyle("skill_row", fontName="Helvetica", fontSize=9,
                         textColor=RL_BLACK, spaceAfter=0, leading=11.5),
        "cert_item": ParagraphStyle("cert_item", fontName="Helvetica", fontSize=9,
                         textColor=RL_BLACK, spaceAfter=1, leading=12),
    }

def _hr():
    return HRFlowable(width="100%", thickness=0.75, color=RL_ACCENT, spaceAfter=2, spaceBefore=0)

def _sec(title, s):
    return [Paragraph(title.upper(), s["section"]), _hr()]

def _blt(text, s):
    return Paragraph(f"• {text}", s["bullet"])

# ── PDF builder ────────────────────────────────────────────────────────────────
def build_pdf(cfg: dict) -> Path:
    s = make_styles()
    story = []

    story.append(Paragraph(cfg["name"], s["name"]))
    story.append(Paragraph(cfg["contact"], s["contact"]))

    story += _sec("Professional Summary", s)
    story.append(Paragraph(cfg["summary"], s["summary"]))

    story += _sec("Technical Skills", s)
    for skill in cfg["skills"]:
        label = skill["label"].replace("&", "&amp;")
        value = skill["value"].replace("&", "&amp;")
        story.append(Paragraph(f"<b>{label}:</b> {value}", s["skill_row"]))

    story += _sec("Education & Certifications", s)
    for edu in cfg["education"]:
        line = f"<b>{edu['degree']}</b> — {edu['school']} &nbsp;({edu['dates']})"
        if edu.get("note"):
            line += f" — {edu['note']}"
        story.append(Paragraph(line, s["cert_item"]))
    if cfg["certifications"]:
        story.append(Paragraph(
            "  |  ".join(f"<b>{c}</b>" for c in cfg["certifications"]),
            s["cert_item"]
        ))

    story += _sec("Projects", s)
    for i, proj in enumerate(cfg["projects"]):
        if i > 0:
            story.append(Spacer(1, 1))
        story.append(Paragraph(proj["title"], s["job_title"]))
        if proj.get("meta"):
            story.append(Paragraph(proj["meta"], s["job_meta"]))
        for b in proj["bullets"]:
            story.append(_blt(b, s))

    story += _sec("Work Experience", s)
    for i, job in enumerate(cfg["jobs"]):
        if i > 0:
            story.append(Spacer(1, 1))
        story.append(Paragraph(job["title"], s["job_title"]))
        story.append(Paragraph(f"{job['company']} | {job['dates']}", s["job_meta"]))
        for b in job["bullets"]:
            story.append(_blt(b, s))

    out = cfg["output"]
    doc = SimpleDocTemplate(
        str(out),
        pagesize=LETTER,
        leftMargin=0.6*inch, rightMargin=0.6*inch,
        topMargin=0.35*inch, bottomMargin=0.3*inch,
    )
    doc.build(story)
    return out

# ── JD match ───────────────────────────────────────────────────────────────────

# Words too generic to be useful as match keywords
_STOPWORDS = {
    "and","or","the","a","an","in","of","to","for","with","on","at","by","from",
    "is","are","be","been","will","you","your","we","our","their","its","this",
    "that","as","it","all","any","have","has","not","do","does","can","may",
    "must","should","would","could","also","well","per","via","new","one","two",
    "each","both","which","who","what","how","when","where","while","than","more",
    "into","upon","about","above","after","before","during","through","within",
    "work","team","role","time","year","day","way","use","help","make","give",
    "get","go","see","know","need","want","look","come","take","provide","ensure",
    "ability","skills","experience","including","related","strong","global",
    "full","part","based","highly","key","main","major","primary","general",
    "various","multiple","large","small","high","low","good","great","best",
    "real","own","free","long","short","cross","next","current","future","other",
}

def _extract_jd_keywords(text: str) -> list[str]:
    """Pull meaningful words and 2-word phrases from JD text."""
    # Normalize
    text = text.lower()
    # Single meaningful words (4+ chars, alpha only, not stopwords)
    words = re.findall(r'\b[a-z]{4,}\b', text)
    singles = [w for w in words if w not in _STOPWORDS]

    # 2-word technical phrases worth keeping together
    phrase_patterns = [
        r'\bactive directory\b', r'\bproject management\b', r'\bmachine learning\b',
        r'\bdata analysis\b', r'\bproblem.?solving\b', r'\bcritical thinking\b',
        r'\bstakeholder\b', r'\bdocumentation\b', r'\brequirements\b',
        r'\bapplication development\b', r'\bapplication support\b',
        r'\binformation technology\b', r'\binformation sciences\b',
        r'\bcomputer science\b', r'\bcybersecurity\b', r'\bnetwork\b',
        r'\bcloud\b', r'\bpython\b', r'\bjava\b', r'\bsql\b', r'\bagile\b',
        r'\bscrum\b', r'\bgit\b', r'\blinux\b', r'\bwindows\b', r'\baws\b',
        r'\bazure\b', r'\bdevops\b', r'\bsecurity\b', r'\bcompliance\b',
        r'\btesting\b', r'\bdebugging\b', r'\bdeployment\b', r'\bmonitoring\b',
        r'\bticket\b', r'\bhelp.?desk\b', r'\bservice.?desk\b', r'\bsupport\b',
        r'\bcollaboration\b', r'\bcommunication\b', r'\bleadership\b',
        r'\bpresent\b', r'\bpresentation\b', r'\binternship\b',
    ]
    phrases = []
    for pat in phrase_patterns:
        if re.search(pat, text):
            phrases.append(re.sub(r'[^a-z ]', '', pat.replace(r'\b', '').replace('.?', ' ')).strip())

    # Deduplicate, preserve order
    seen = set()
    result = []
    for kw in phrases + singles:
        kw = kw.strip()
        if kw and kw not in seen and kw not in _STOPWORDS:
            seen.add(kw)
            result.append(kw)
    return result

def _resume_text(cfg: dict) -> str:
    """Flatten all resume text into one lowercase string for matching."""
    parts = [cfg.get("summary", ""), cfg.get("role_title", "")]
    for sk in cfg.get("skills", []):
        parts += [sk.get("label", ""), sk.get("value", "")]
    for proj in cfg.get("projects", []):
        parts += [proj.get("title", ""), proj.get("meta", "")] + proj.get("bullets", [])
    for job in cfg.get("jobs", []):
        parts += [job.get("title", ""), job.get("company", "")] + job.get("bullets", [])
    for edu in cfg.get("education", []):
        parts += [edu.get("degree", ""), edu.get("school", ""), edu.get("note", "")]
    parts += cfg.get("certifications", [])
    return " ".join(parts).lower()

def _fetch_jd_text(url: str) -> str | None:
    """Try to fetch plain text from a JD URL. Returns None on any failure."""
    try:
        import requests
        from bs4 import BeautifulSoup
        headers = {"User-Agent": "Mozilla/5.0 (compatible; resume-builder/1.0)"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        # Remove nav/header/footer/script noise
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)
    except Exception:
        return None

def run_jd_match(cfg: dict) -> None:
    """
    Optional wizard step: fetch or paste a JD, extract keywords,
    show a match report against the built resume config.

    IMPORTANT — this tool only reports. It never adds anything to the resume
    without the user explicitly describing their own real experience in their
    own words. Inflating skills to match keywords is resume fraud and can get
    a candidate blacklisted. Every addition must be earned and honest.
    """
    console.print(Rule("[bold]JD Match — optional[/bold]", style="navy_blue"))
    console.print(
        "[dim]This step compares the job description against your resume and shows gaps.\n"
        "Nothing is added automatically. Any additions require you to describe\n"
        "your real experience in your own words.[/dim]\n"
    )

    use_link = inquirer.confirm(
        message="Do you have a link to the job posting?",
        default=True,
    ).execute()

    jd_text = None

    if use_link:
        url = inquirer.text(message="Paste the job posting URL:").execute().strip()
        if url:
            console.print("  [dim]Fetching...[/dim]", end="")
            jd_text = _fetch_jd_text(url)
            if jd_text:
                console.print(" [green]✓[/green]")
            else:
                console.print(" [yellow]couldn't read that page (login wall or private link) — switching to paste[/yellow]")

    if not jd_text:
        console.print("\n  [dim]Paste the full job description text below.")
        console.print("  When done, enter a line containing only '---' and press Enter:[/dim]\n")
        lines = []
        while True:
            line = inquirer.text(message="").execute()
            if line.strip() == "---":
                break
            lines.append(line)
        jd_text = "\n".join(lines)

    if not jd_text.strip():
        console.print("[yellow]  No JD text — skipping match.[/yellow]\n")
        return

    keywords = _extract_jd_keywords(jd_text)
    resume   = _resume_text(cfg)

    matched = list(dict.fromkeys([kw for kw in keywords if kw in resume]))[:30]
    missing = list(dict.fromkeys([kw for kw in keywords if kw not in resume]))[:30]
    score   = int(100 * len(matched) / max(len(matched) + len(missing), 1))

    console.print()
    color = "green" if score >= 70 else "yellow" if score >= 45 else "red"
    console.print(Panel.fit(
        f"[bold {color}]JD Match Score: {score}%[/bold {color}]  "
        f"({len(matched)} of {len(matched) + len(missing)} key terms covered)\n\n"
        f"[green]✓ Covered:[/green]  {', '.join(matched) if matched else 'none detected'}\n\n"
        f"[yellow]△ Missing:[/yellow]  {', '.join(missing) if missing else 'none — great coverage!'}",
        border_style=color,
        padding=(0, 2),
    ))

    if not missing:
        console.print()
        return

    # ── Guided honest gap review ───────────────────────────────────────────────
    console.print(
        "\n  [dim]For each missing term below, you'll be asked if you genuinely have\n"
        "  that experience. Only say yes if you can describe it honestly — this\n"
        "  goes on a legal document you sign off on.[/dim]\n"
    )

    # Let user pick which missing terms to review (don't force through all of them)
    gap_choices = [Choice(value=kw, name=kw, enabled=False) for kw in missing]
    to_review = inquirer.checkbox(
        message="Select any missing terms you DO have real experience with to describe:",
        choices=gap_choices,
        transformer=lambda r: f"{len(r)} selected" if r else "none — skip",
    ).execute()

    for kw in to_review:
        console.print(f"\n  [bold]'{kw}'[/bold] — describe your actual experience with this:")
        console.print(
            f"  [dim]Be specific: when, where, what you did, what the outcome was.\n"
            f"  If you can't describe a specific instance, skip it.[/dim]\n"
        )
        skip = inquirer.confirm(
            message=f"  Do you have genuine, describable experience with '{kw}'?",
            default=False,
        ).execute()
        if not skip:
            continue

        # Determine whether this fits better as a skill category or a bullet
        dest = inquirer.select(
            message="Where does this belong on your resume?",
            choices=[
                Choice(value="skill", name="Skill category (e.g. 'Cloud Platforms: AWS...')"),
                Choice(value="project", name="Project bullet point"),
                Choice(value="job", name="Job bullet point"),
            ],
        ).execute()

        if dest == "skill":
            label = inquirer.text(
                message="Skill category name:",
                default=kw.title(),
            ).execute().strip()
            value = inquirer.text(
                message=f"Describe your '{label}' experience honestly (your words):",
            ).execute().strip()
            if label and value:
                new_skill = {"label": label, "value": value}
                cfg["skills"].append(new_skill)
                console.print(f"  [green]✓ Added skill category '{label}'[/green]")
                if inquirer.confirm(message="  Save to master profile?", default=True).execute():
                    # profile not in scope here — handled via save on next run
                    console.print("  [dim]Noted — save to master profile by re-running and adding via Step 4.[/dim]")

        elif dest == "project":
            if cfg["projects"]:
                proj_choices = [
                    Choice(value=i, name=p["title"][:70])
                    for i, p in enumerate(cfg["projects"])
                ]
                proj_idx = inquirer.select(
                    message="Which project does this relate to?",
                    choices=proj_choices,
                ).execute()
                bullet = inquirer.text(
                    message="Write the bullet in your own words (honest, specific):",
                ).execute().strip()
                if bullet:
                    cfg["projects"][proj_idx]["bullets"].append(bullet)
                    console.print(f"  [green]✓ Added bullet to '{cfg['projects'][proj_idx]['title'][:50]}'[/green]")
            else:
                console.print("  [dim]No projects on this resume to add to.[/dim]")

        elif dest == "job":
            if cfg["jobs"]:
                job_choices = [
                    Choice(value=i, name=f"{j['title']} — {j['company']}")
                    for i, j in enumerate(cfg["jobs"])
                ]
                job_idx = inquirer.select(
                    message="Which job does this relate to?",
                    choices=job_choices,
                ).execute()
                bullet = inquirer.text(
                    message="Write the bullet in your own words (honest, specific):",
                ).execute().strip()
                if bullet:
                    cfg["jobs"][job_idx]["bullets"].append(bullet)
                    console.print(f"  [green]✓ Added bullet to '{cfg['jobs'][job_idx]['title']}'[/green]")
            else:
                console.print("  [dim]No jobs on this resume to add to.[/dim]")

    console.print()
    if to_review:
        console.print(
            "[dim]Reminder: re-run the builder after this session to save any new\n"
            "skill categories to your master profile permanently.[/dim]\n"
        )

# ── Wizard helpers ─────────────────────────────────────────────────────────────
def _add_bullets_interactively(item_name: str) -> list[str]:
    """Prompt for bullet points one at a time until the user enters a blank line."""
    console.print(f"  [dim]Enter bullet points for '{item_name}' (blank line to finish):[/dim]")
    bullets = []
    idx = 1
    while True:
        b = inquirer.text(message=f"  Bullet {idx}:").execute().strip()
        if not b:
            break
        bullets.append(b)
        idx += 1
    return bullets

# ── Wizard ─────────────────────────────────────────────────────────────────────
def run_wizard(profile: dict) -> dict:
    cfg = {}

    # Banner
    console.print()
    console.print(Panel.fit(
        "[bold navy_blue]Resume Builder[/bold navy_blue]\n"
        "[dim]Builds a tailored, ATS-ready PDF from your master profile[/dim]",
        border_style="navy_blue",
        padding=(0, 2),
    ))
    console.print()

    # ── Step 1: Role & filename ────────────────────────────────────────────────
    console.print(Rule("[bold]Step 1 of 6 — Target Role[/bold]", style="navy_blue"))
    role = inquirer.text(
        message="Job title you're targeting:",
        default="IT Support Technician",
    ).execute()
    cfg["role_title"] = role

    safe_name = role.strip().replace(" ", "_").replace("/", "_").replace("\\", "_")
    suggested = f"Terrence_Fleming_{safe_name}_Resume.pdf"
    fname = inquirer.text(
        message="Output filename:",
        default=suggested,
    ).execute()
    output_dir = get_output_dir(profile)
    cfg["output"] = output_dir / fname
    console.print()

    # ── Step 2: Contact info ───────────────────────────────────────────────────
    console.print(Rule("[bold]Step 2 of 6 — Contact Info[/bold]", style="navy_blue"))
    console.print(f"[dim]Current:[/dim] {profile['contact']}\n")
    if inquirer.confirm(message="Update contact info?", default=False).execute():
        profile["contact"] = inquirer.text(
            message="Contact line:",
            default=profile["contact"],
        ).execute()
        save_profile(profile)
        console.print("[green]✓ Saved to master profile[/green]")
    cfg["name"]    = profile["name"]
    cfg["contact"] = profile["contact"]
    console.print()

    # ── Step 3: Summary ────────────────────────────────────────────────────────
    console.print(Rule("[bold]Step 3 of 6 — Professional Summary[/bold]", style="navy_blue"))
    auto_summary = pick_summary_template(role)
    console.print(f"[dim]Auto-generated for '[cyan]{role}[/cyan]':[/dim]\n{auto_summary}\n")
    if inquirer.confirm(message="Use auto-generated summary?", default=True).execute():
        cfg["summary"] = auto_summary
    else:
        cfg["summary"] = inquirer.text(
            message="Your summary:",
            default=auto_summary,
        ).execute()
    console.print()

    # ── Step 4: Skills ─────────────────────────────────────────────────────────
    console.print(Rule("[bold]Step 4 of 6 — Technical Skills[/bold]", style="navy_blue"))

    # Role-based suggestions before showing master profile list
    if inquirer.confirm(
        message=f"Show ATS skill suggestions for '{role}'?",
        default=True,
    ).execute():
        suggest_role_skills(role, cfg, profile)

    console.print("[dim]Space to toggle  ·  ↑↓ to move  ·  Enter to confirm[/dim]\n")
    skill_choices = [
        Choice(
            value=i,
            name=f"{sk['label']}: {sk['value'][:60]}…" if len(sk['value']) > 60 else f"{sk['label']}: {sk['value']}",
            enabled=True,
        )
        for i, sk in enumerate(profile["skills"])
    ]
    chosen_skill_idx = inquirer.checkbox(
        message="Select skill categories to include:",
        choices=skill_choices,
        transformer=lambda r: f"{len(r)} categories selected",
    ).execute()
    cfg["skills"] = [profile["skills"][i] for i in chosen_skill_idx]

    while inquirer.confirm(message="Add a new skill category?", default=False).execute():
        new_label = inquirer.text(message="Category name:").execute().strip()
        new_value = inquirer.text(message=f"Skills for '{new_label}':").execute().strip()
        if new_label and new_value:
            new_skill = {"label": new_label, "value": new_value}
            cfg["skills"].append(new_skill)
            console.print(f"[green]✓ Added '{new_label}'[/green]")
            if inquirer.confirm(message="Save to master profile for future resumes?", default=True).execute():
                profile["skills"].append(new_skill)
                save_profile(profile)
                console.print("[green]✓ Saved to master profile[/green]")
    console.print()

    # ── Step 5: Projects ───────────────────────────────────────────────────────
    console.print(Rule("[bold]Step 5 of 6 — Projects[/bold]", style="navy_blue"))
    proj_choices = [
        Choice(value=i, name=p["title"][:80], enabled=True)
        for i, p in enumerate(profile["projects"])
    ]
    chosen_proj_idx = inquirer.checkbox(
        message="Select projects to include:",
        choices=proj_choices,
        transformer=lambda r: f"{len(r)} projects selected",
    ).execute()
    cfg["projects"] = [profile["projects"][i] for i in chosen_proj_idx]

    while inquirer.confirm(message="Add a new project?", default=False).execute():
        p_title = inquirer.text(message="Project title:").execute().strip()
        p_meta  = inquirer.text(message="Subtitle/stack (optional, press Enter to skip):").execute().strip()
        p_bullets = _add_bullets_interactively(p_title)
        if p_title and p_bullets:
            new_proj = {"title": p_title, "meta": p_meta, "bullets": p_bullets}
            cfg["projects"].append(new_proj)
            console.print(f"[green]✓ Added project '{p_title}'[/green]")
            if inquirer.confirm(message="Save to master profile for future resumes?", default=True).execute():
                profile["projects"].append(new_proj)
                save_profile(profile)
                console.print("[green]✓ Saved to master profile[/green]")

    cfg["education"]      = profile["education"]
    cfg["certifications"] = profile["certifications"]
    console.print()

    # ── Step 6: Work Experience ────────────────────────────────────────────────
    console.print(Rule("[bold]Step 6 of 6 — Work Experience[/bold]", style="navy_blue"))
    job_choices = [
        Choice(
            value=i,
            name=f"{j['title']} — {j['company']} ({j['dates']})",
            enabled=True,
        )
        for i, j in enumerate(profile["jobs"])
    ]
    chosen_job_idx = inquirer.checkbox(
        message="Select jobs to include:",
        choices=job_choices,
        transformer=lambda r: f"{len(r)} jobs selected",
    ).execute()
    cfg["jobs"] = [profile["jobs"][i] for i in chosen_job_idx]

    while inquirer.confirm(message="Add a new job?", default=False).execute():
        j_title   = inquirer.text(message="Job title:").execute().strip()
        j_company = inquirer.text(message="Company name:").execute().strip()
        j_dates   = inquirer.text(message="Dates (e.g. Jan 2025 – Present):").execute().strip()
        j_bullets = _add_bullets_interactively(j_title)
        if j_title and j_company and j_bullets:
            new_job = {"title": j_title, "company": j_company, "dates": j_dates, "bullets": j_bullets}
            cfg["jobs"].append(new_job)
            console.print(f"[green]✓ Added job '{j_title} — {j_company}'[/green]")
            if inquirer.confirm(message="Save to master profile for future resumes?", default=True).execute():
                profile["jobs"].append(new_job)
                save_profile(profile)
                console.print("[green]✓ Saved to master profile[/green]")

    console.print()

    # ── Optional: JD match ─────────────────────────────────────────────────────
    if inquirer.confirm(message="Run JD keyword match against this resume?", default=False).execute():
        run_jd_match(cfg)

    return cfg

# ── Entry point ────────────────────────────────────────────────────────────────
def main():
    profile = load_profile()
    cfg     = run_wizard(profile)

    console.print(Rule("[bold]Building PDF[/bold]", style="navy_blue"))
    console.print(f"  [dim]Output:[/dim] [cyan]{cfg['output']}[/cyan]")

    try:
        out = build_pdf(cfg)
        try:
            result = subprocess.run(
                ["pdfinfo", str(out)], capture_output=True, text=True, timeout=5
            )
            pages = next(
                (ln.split(":")[1].strip() for ln in result.stdout.splitlines() if "Pages:" in ln),
                "?"
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pages = "unknown (pdfinfo not installed)"
        console.print()
        console.print(Panel.fit(
            f"[bold green]✓ Resume built successfully[/bold green]\n\n"
            f"  [dim]File:[/dim]  {out.name}\n"
            f"  [dim]Pages:[/dim] {pages}\n"
            f"  [dim]Role:[/dim]  {cfg['role_title']}",
            border_style="green",
            padding=(0, 2),
        ))
    except Exception as e:
        console.print(f"\n[bold red]✗ Build failed:[/bold red] {e}")
        sys.exit(1)

    console.print()

if __name__ == "__main__":
    main()
