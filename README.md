# Locust + Jenkins (Windows) — QA Performance CI/CD Demo

**No Grafana / no Grafana Cloud.** Uses Locust's **own local Web UI** and native **HTML + CSV reports**, published in Jenkins with the **HTML Publisher** plugin.

## Files

- `app/main.py`: tiny FastAPI product API. Change `RESPONSE_DELAY_SECONDS` to simulate a regression or `FORCE_HTTP_ERROR` to simulate HTTP 503 failures.
- `locustfile.py`: tests `GET /api/products` and applies quality thresholds: **P95 <= 800ms**, **failure rate <= 2%**, and **>= 20 requests**. Reports JSON summary and sets exit code on failure.
- `scripts/run_ci.py`: Jenkins runner. Starts API on a free localhost port, checks `/health`, runs Locust headlessly with a selected load profile, shuts down API.
- `Jenkinsfile`: Windows Jenkins Pipeline. Handles install, staging + Locust, quality-gated simulated deployment, HTML report publication, artifact archiving, SCM polling, and optional scheduled runs.

## 1. Install tools on Windows

1. Install Python 3.12 (ensure Python is on PATH for the Jenkins service/agent account).
2. Install Git.
3. Install supported Java (Java 21 or Java 25 for current Jenkins LTS; verify on Jenkins download page).
4. Download Jenkins LTS WAR from https://www.jenkins.io/download/ and run in a terminal:
   ```cmd
   java -jar jenkins.war --httpPort=8080
   ```
5. Open http://localhost:8080, unlock Jenkins using the displayed initial password, install suggested plugins and create admin user.
6. Install **HTML Publisher** plugin under Manage Jenkins > Plugins. Also ensure **Pipeline** and **Git** are installed.

> If Jenkins runs as a Windows service instead of a terminal, ensure the Windows service account can execute `python` and `git`; restart the service after modifying its PATH. `agent any` assumes Jenkins is running on the Windows machine/agent that can run `bat` steps.

## 2. First run LOCALLY using Locust's own Web UI

In a Command Prompt inside this folder:

```cmd
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000
```

Open a second Command Prompt:

```cmd
python -m locust -f locustfile.py --host http://127.0.0.1:8000
```

Visit **http://localhost:8089**. Enter `10` users and `5` users/second, click Start, then Stop, view Statistics / Charts and use **Download Data**. Locust's own live UI is for manual exploration; Jenkins uses the same test in headless mode and saves its built-in reports.

You can also test without any UI:

```cmd
python scripts\run_ci.py --profile smoke
```

Open `reports/locust-report.html` and see `reports/locust_stats.csv` and `reports/quality-gate.json`.

## 3. Create Jenkins CI/CD job

1. Push all the extracted project files (including `Jenkinsfile`) to a GitHub repository.
2. Jenkins dashboard > **New Item** > `Locust-QA-Performance` > **Pipeline**.
3. Under **Pipeline**: **Definition** = `Pipeline script from SCM`; **SCM** = `Git`; **Repository URL** = your GitHub repository URL; **Branch Specifier** = `*/main`; **Script Path** = `Jenkinsfile`.
4. Save and select **Build Now**. After the job initializes, choose **Build with Parameters** and pick `smoke`, `load`, or `stress`.
5. The `pollSCM` trigger checks GitHub for changes every ~2 minutes. On a code change, Jenkins checks out the latest code and runs the pipeline automatically. Since Jenkins on localhost is not publicly accessible, use polling instead of a webhook.
6. Optional `cron('H 2 * * 1-5')` runs the job once daily on weekdays in Jenkins server-local time during the 02:00 hour. Remove this trigger if not needed.

## 4. Show QA pass/fail

**PASS:** `app/main.py` has:

```python
RESPONSE_DELAY_SECONDS = 0.05
FORCE_HTTP_ERROR = False
```

Commit/push. Pipeline should succeed and simulated production stage should run.

**FAIL due to latency:** Change `RESPONSE_DELAY_SECONDS = 1.20`. Commit/push. Locust calculates P95 above 800ms; it sets exit code `1`, the Jenkins stage fails, and the simulated production stage is skipped. HTML/CSV/JSON reports remain archived under the build.

**FAIL due to errors:** Reset delay to `0.05` and set `FORCE_HTTP_ERROR = True`. Commit/push. HTTP 503 errors exceed 2%, so the pipeline fails.

**Recover:** Reset both variables, commit/push; expected PASS again.

## 5. Native Locust reports in Jenkins

- Build page > **Locust HTML Report** (published using HTML Publisher).
- Build page > **Artifacts** > `reports/locust-report.html`, `reports/locust_stats.csv`, `reports/locust_stats_history.csv`, `reports/locust_failures.csv`, `reports/quality-gate.json`.
- Build page > **Console Output** to see current test output and SLA gate decision.
- Reports are published even when the pipeline fails.

## 6. Load profiles

| Profile | Users | Spawn rate | Duration |
|---|---:|---:|---:|
| smoke | 10 | 5/sec | 30 sec |
| load | 30 | 5/sec | 60 sec |
| stress | 60 | 10/sec | 90 sec |

All are only for the **local toy API**. Real tests should use representative loads and environments.

## 7. Notes

- The demo stages the API temporarily within the same Jenkins worker; this does **not** deploy to a real staging environment.
- "Production deployment" is a deliberate **simulation**, not an actual production release. Replace that stage with your real deployment mechanism only after reviewing permissions, approvals, and safety.
- Jenkins on localhost will not receive GitHub push webhooks unless publicly reachable, so this example uses SCM polling.
- If a plugin is unavailable or Jenkins can't run Python because of service-user PATH, fix prerequisites in Jenkins first.

Docs: https://docs.locust.io/en/stable/ | https://www.jenkins.io/doc/book/pipeline/ | https://plugins.jenkins.io/htmlpublisher/
