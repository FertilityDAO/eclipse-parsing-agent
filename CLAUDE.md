\# Total Solar Eclipse Parsing Agent



\## Purpose

This project parses NASA public-domain solar eclipse data files into

clean, analysis-ready outputs.



\## Module Scope (what we are doing right now)

\- Keep the project simple and beginner-friendly

\- Use small sample CSV data while learning the workflow

\- Build one parser script in /src that reads from /data and writes to /outputs



\## Folder Rules

\- /data = raw input files (do not manually edit once real NASA files are added)

\- /src = python scripts that parse and clean data

\- /outputs = cleaned CSV outputs produced by scripts

\- /prompts = saved prompt drafts and notes for the agent



\## First Build Target

Create a script:

\- src/parse\_eclipses.py

That reads:

\- data/raw\_eclipses.csv

And outputs:

\- outputs/eclipses\_clean.csv

