# JobFinder

Personal FastAPI dashboard: upload a CV, search public LinkedIn job listings, then score each role for interview fit, sponsorship, remote/hybrid, relocation, and salary.

No login. No Keycloak. No Vault. SQLite only.

## Architecture

Same n-tier layout as [web.service.majva-py](https://github.com/majva/web.service.majva-py):

```
Host (app.py) → Application (controllers, dashboard)
              → Core (CV parser, LinkedIn client, match scoring)
              → Infrastructure (SQLite, repositories, DI, Alembic)
```

Request flow:

```
POST /api/v1/cv/upload
  → CvController → CvService → CandidateRepository → SQLite

POST /api/v1/job/search
  → JobController → JobService
      → LinkedIn public job listings
      → JobAnalyzerService (sponsor / remote / relocate / salary)
      → MatchService (interview success %)
      → JobRepository + JobMatchRepository
```

## Run

Python 3.11+. Install deps yourself, then:

```bash
pip install -r requirements.txt
python src/host/app.py
```

Then open:

| URL | What |
| --- | --- |
| http://localhost:5000 | Dashboard |
| http://localhost:5000/docs | Swagger |
| http://localhost:5000/api/v1/health_check/version | Health |

Optional migrations (schema is also created on startup):

```bash
python src/infrastructure/scripts/run_migrations.py --upgrade
```

## How it works

1. Upload a text-based PDF CV.
2. The parser pulls name, titles, skills, years, and location.
3. Search uses those keywords against LinkedIn’s public job listings (no LinkedIn login).
4. Each job is tagged for workplace type, visa sponsorship, relocation, salary, seniority, and employment type.
5. Interview success is a 0–100 score from skill overlap, title fit, experience, and location/remote match.

## Notes

LinkedIn may rate-limit or bot-check the public job pages. If a search returns HTTP 403/429/999, wait and retry from your own network. This tool is for personal job hunting against publicly listed roles — not for scraping profiles or bypassing login.
