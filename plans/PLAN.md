- setup supabase.
- reviewed some best practices of CS.
- We have an orchestrator for our services so that we properly differentiate core logics vs services.
- launch supabase start in local env (SUPABASE_PROJECT_URL=http://127.0.0.1:54321)
- do supabase db reset to reset local tables (if needed or changed things). Currently 5 tables for full end2end.
- you can check connection by doing: uv run python scripts/verify_db_setup.py
- PYTHONPATH=src uv run python src/app/main.py
- Build the pipeline to get the content from youtube and x and extract the value from each in db. (only youtube for now)
- extract transcripts with youtube-transcript.io and save in db.
- Create the agentic logic to put all the extracted infos together nicely. v1
- Add opik for tracing and costs.
- Review implementation, improve traces, opik login, implementaiton and visibility. clean code.
- Create the agent that create the per day digest with all the relevant context.
- create the v2 of both video extraction and daily digest to improve value created/ease of consuming.
- add rls layer and security around supabase + frontend.
- Re-run into prod db and connect to front end.
- hitting output tokens limit. Needs to save final response in a better sequence to manage best context windows. **(ON THIS!)**


Live coding session(s):
Batch 1:
- add if 0 videos in the day edge case *
- style of cards for issues in newsletter view *
- enhance contrarian corner: add source attribution, more details, links/resources
- add search/filter by keywords & preferences across past issues

Batch 2:
- fix some UI newsletter things (url in deep dive section, youtube links broken and num of videos repeated)
- more UI things -> improved filtering logics + filter btw ALL, daily, weekly.
- weekly processing (future improvement of this is to use past week as ref for this week analysis. creating momentum)
    - backend - generated 2 versions
    - frontend -> generated v1 and adapted for v2
- review 15th weekly generation
(note: check the prmpt for weekly bcse it has v2 in it - and prompt versioning is off. future simple fix.)

Batch 3:


BACKLOG:
- add prevous day(s) section to the digest.
- would be cool to allow user to easily share a video/insights from any daily/weekly digest.
BONUS: - add weekly & monthly recaps (different abstraction levels for newsletter fatigue)

