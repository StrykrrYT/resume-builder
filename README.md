# resume_builder

An interactive CLI tool that builds tailored, ATS-ready resumes as PDF files.

Stores a master profile so you never re-enter your contact info, then walks you through every section in a few minutes — skills, projects, work history, and a live JD keyword match.

> **Privacy:** Everything stays on your machine. Your profile is saved to `~/resume_profile.json` — a plain text file on your own computer. No data is sent anywhere, no account is required, and I have zero access to anything you enter.

---

## What it does

- **Role-based skill suggestions** — type a role like "Forklift Operator" and get a checklist of ATS skills common to that role; check off only what you genuinely have
- **JD keyword match** — paste or link a job posting; the tool shows what's covered and what's missing, then lets you describe any missing experience honestly (nothing is added silently)
- **Checklist menus** — toggle skills, projects, and jobs on/off per resume without editing the master profile
- **Add on the fly** — add new skills, projects, or jobs during the wizard and optionally save them to your master profile
- **ATS-safe PDF** — single-column, no tables, standard section headings (`Professional Summary`, `Technical Skills`, `Education & Certifications`, `Projects`, `Work Experience`)
- **First-run setup** — on first launch you choose where to save PDFs; the choice is remembered
- **Optional Ollama integration** — if you have [Ollama](https://ollama.com) running locally, the tool uses it for smarter role suggestions; falls back to the built-in dictionary automatically if you don't

---

## Requirements

- Python **3.10 or higher**
- pip packages: `InquirerPy reportlab rich requests beautifulsoup4`

---

## Installation

Pick your platform below.

### Linux (Arch / Manjaro)

```bash
# Install Python if not already present
sudo pacman -S python python-pip

# Install dependencies (Arch uses --break-system-packages outside a venv)
pip install InquirerPy reportlab rich requests beautifulsoup4 --break-system-packages

# Clone or download the repo, then run
python3 resume_builder.py
```

> **Optional — page count after build:**
> Install `poppler` for `pdfinfo` support. Without it the tool still works; it just shows "pages unknown" after building.
> ```bash
> sudo pacman -S poppler
> ```

---

### Linux (Ubuntu / Debian)

```bash
# Install Python if not already present
sudo apt update && sudo apt install python3 python3-pip -y

# Install dependencies
pip3 install InquirerPy reportlab rich requests beautifulsoup4

# Run
python3 resume_builder.py
```

> **Optional — page count:**
> ```bash
> sudo apt install poppler-utils
> ```

---

### macOS

```bash
# Install Homebrew if not already present
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python

# Install dependencies
pip3 install InquirerPy reportlab rich requests beautifulsoup4

# Run
python3 resume_builder.py
```

> **Optional — page count:**
> ```bash
> brew install poppler
> ```

---

### Windows (PowerShell)

> **Note:** Python on Windows uses `python` or `py`, not `python3`.

**Step 1 — Install Python 3.10+**

Go to [python.org/downloads](https://www.python.org/downloads/) and download the latest installer.
During install, **check "Add Python to PATH"** before clicking Install.

**Step 2 — Install dependencies**

Open PowerShell or Windows Terminal and run:

```powershell
pip install InquirerPy reportlab rich requests beautifulsoup4
```

**Step 3 — Run the tool**

```powershell
python resume_builder.py
```

> **Tip:** Use **Windows Terminal** (free on the Microsoft Store) for the best experience — the interactive checkboxes render better than in the legacy Command Prompt.

> **Page count after build:** `pdfinfo` is not available on Windows by default. The tool will show "pages unknown" — your PDF is still built correctly. If you want page count, install [Poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases) and add its `bin/` folder to your PATH.

---

## Usage

```bash
python3 resume_builder.py    # Linux / macOS
python resume_builder.py     # Windows
```

### First run

On first launch you'll be asked where to save finished PDFs. The default is:

| OS      | Default path                        |
|---------|-------------------------------------|
| Linux   | `~/Documents/Resumes`               |
| macOS   | `~/Documents/Resumes`               |
| Windows | `C:\Users\<you>\Documents\Resumes`  |

Your choice is saved to `~/resume_profile.json` and remembered on future runs.

### Wizard steps

| Step | What happens |
|------|--------------|
| 1 — Role title | Type the target job title (e.g. `IT Support Technician`) |
| 2 — Contact info | Name, email, phone, location, LinkedIn, GitHub — pre-filled from profile |
| 3 — Summary | Auto-generated ATS summary with your role injected; edit if needed |
| 4 — Skills | Role-based suggestions shown first → then pick from master profile → add new ones |
| 5 — Projects | Toggle which projects to include; add new ones on the fly |
| 6 — Work history | Toggle which jobs to include; add new ones on the fly |
| Optional — JD match | Paste or link a job posting; see match score and fill gaps honestly |

---

## Role-based skill suggestions

When you enter a role title, the tool immediately shows a checklist of ATS skills common to that role. **Check only what you genuinely have.** For each checked item you describe your real experience in your own words — the suggestion is a prompt, not an auto-fill.

Built-in role families:

- Forklift Operator / Warehouse / Logistics / Shipping
- IT Support / Help Desk / Desktop Technician
- Cybersecurity / SOC Analyst
- Network / NOC / Infrastructure / Systems
- Cloud / DevOps / AWS / Azure / GCP
- Software Developer / Web / Full-Stack
- Customer Service / Sales / Call Center
- Manager / Lead / Supervisor / Coordinator

Roles outside these families show no suggestions (the step is skipped automatically).

---

## Optional: Ollama (smarter suggestions, free, local, no API key)

The built-in dictionary covers 8 common role families. For anything else — or just better suggestions across the board — you can install [Ollama](https://ollama.com). It runs a local AI model entirely on your own machine: no account, no API key, no internet required, no ongoing cost.

**It is completely optional.** The tool checks for it automatically and falls back to the dictionary if it's not running. Nothing breaks either way.

### Install

**Linux / macOS:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2   # ~2 GB one-time download
```

**Windows:**
Download the installer from [ollama.com/download](https://ollama.com/download), run it, then in PowerShell:
```powershell
ollama pull llama3.2
```

### How it works

When you reach Step 4 (Skills), the tool silently pings `http://localhost:11434`. If Ollama is running with `llama3.2`, it generates role-specific suggestions on the fly. If it's not running, the built-in dictionary kicks in instead — you won't see an error either way.

On Linux/macOS, Ollama runs as a background service after install — no manual start needed. On Windows, launch the Ollama desktop app before running the resume builder.

---

## Master profile

Your master profile lives at `~/resume_profile.json` — a plain text file **on your own computer**. Nothing is uploaded, phoned home, or stored anywhere else. I have no access to it.

It stores:

- Contact info (name, email, phone, location, LinkedIn, GitHub)
- Skills library
- Projects list
- Work history
- Preferred output directory

Skills, projects, and jobs added during the wizard can be saved back to this file so they're available on future runs.

You can open and edit it in any text editor at any time, or delete it to start fresh.

---

## ATS design decisions

- Skills use plain `Label: value` paragraphs instead of tables — tables fragment on ATS extraction
- Section headings match standard ATS buckets exactly
- `keepWithNext` on job title and company lines prevents orphaned bullets across page breaks
- All text is single-column, no headers/footers/text boxes/images
- Font is Helvetica (guaranteed embedded, universally parsed)

---

## License

MIT
