# Advanced FAF analytics

## What are we extracting

- Social graph: who is playing with whom, how successful this partnership is, and how player cluster together
- Veterancy stats. Probably, as replay highlights

## How it is supposed to work

Now, pipeline looks like this:

- Download a bunch of repos with `mass_download.py`. A bunch of replays will be recorded in the database. 
- Extract replay headers with basic info with `extract_data.py` (ToDo) 
- Compute visualizations (ToDo)

