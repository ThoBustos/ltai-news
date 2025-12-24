- setup supabase.
- reviewed some best practices of CS.
- We have an orchestrator for our services so that we properly differentiate core logics vs services.
- launch supabase start in local env (SUPABASE_PROJECT_URL=http://127.0.0.1:54321)
- do supabase db reset to reset local tables (if needed or changed things). Currently 5 tables for full end2end.
- you can check connection by doing: uv run python scripts/verify_db_setup.py
- PYTHONPATH=src uv run python src/app/main.py
- Build the pipeline to get the content from youtube and x and extract the value from each in db. (only youtube for now)
- extract transcripts with youtube-transcript.io and save in db.
- Create the agentic logic to put all the extracted infos together nicely.  **(ON THIS!)**
- Create the logic to save everything and connect to front end.
- Add opik for tracing and costs.





