setup supabase.
reviewed some best practices of CS.
We have an orchestrator for our services so that we properly differentiate core logics vs services.
launch supabase start in local env (SUPABASE_PROJECT_URL=http://127.0.0.1:54321)
do supabase db reset to reset local tables (if needed or changed things). Currently 5 tables for full end2end.
Build the pipeline to get the content from youtube and x and extract the value from each. **(ON THIS!)**
Create the agentic logic to put all the extracted infos together nicely.
Create the logic to save everything and connect to front end.
Add opik for tracing and costs.