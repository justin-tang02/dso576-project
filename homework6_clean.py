#!/usr/bin/env python
# coding: utf-8

# # Homework 6 — Project data cleaning
#
# **Project:** Emerging Music Artist (Music Discovery)
# **Student:** Sizhou Wang (confirm spelling before submission)
# **Source:** local `9.listens` from the team's ListenBrainz work. Its exact local version is identified by SHA-256 below; the original download date is not recorded in this folder.
# **Assignment:** `Module_6_Homework.pdf`, pp. 1–3.
#
# This is an individual, full-dataset audit. The source is unchanged. The notebook runs from the top and writes a full cleaned Parquet plus a 20-row review sample under `outputs/`. The 14-item checklist and five record checks appear below. Team decisions are labeled **HUMAN DECISION**. No MusicBrainz table is merged here.

# ## 1. Goal, grain, and rules — written before cleaning
#
# **Project vision:** An editorial lead may compare emerging artists for extra playlist exposure (candidate Vision A in `project-start.md`; not a final team decision). **Question:** Which artists show a growing audience with continued engagement? The proposed comparison is distinct listeners per artist per month. This cleaning assignment checks whether listen events and artist identities can support that question; it does not claim an emerging-artist ranking.
#
# **Raw grain:** one ListenBrainz submitted listen. Candidate event key: `(user_id, timestamp, recording_msid)`; verify uniqueness rather than assume it. A repeated `recording_msid` or `user_id` is expected across separate events.
#
# | Rule | Reason | Check |
# |---|---|---|
# | Preserve `9.listens` and record SHA-256, size, and UTC coverage | Trace source version | source exists; hash and counts |
# | Parse Unix seconds to timezone-aware UTC; preserve original integer | Avoid timezone ambiguity | failed parse and min/max |
# | Strip only leading/trailing whitespace on names; preserve case, internal spaces, Unicode and IDs | Avoid joining distinct artists or altering identifiers | changed counts and before/after examples |
# | Keep missing MusicBrainz IDs as missing, and preserve multi-artist arrays | Name-only inference and first-artist attribution would be unsafe | missingness and multi-artist counts |
# | Derive duration in milliseconds from `duration_ms`, otherwise seconds × 1000; flag invalid values | Source uses two units | conversion failure and range checks |
# | Keep all events, including historical and unusual durations; flag suspicious ones | Old imports and long tracks can be real | raw = final row count and flag counts |
# | Do not deduplicate without confirmed duplicate submissions | Same recording can be played repeatedly | exact row and candidate-key duplicate counts |
#
# **HUMAN DECISION:** The team still needs to approve an emerging-artist definition, observation window, repeat-listen interval, artist attribution for collaborations, and treatment of events without MBIDs. This notebook uses no unsupported artist-name to MBID merge.

# In[1]:


from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import sys
import duckdb
import pandas as pd
from IPython.display import display, Markdown

ROOT = Path.cwd()
SOURCE = ROOT / "9.listens"
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)
CLEAN = OUT / "homework6_clean.parquet"
SAMPLE = OUT / "homework6_sample.csv"
assert SOURCE.is_file(), f"Missing source: {SOURCE}"

con = duckdb.connect()
con.execute("SET TimeZone='UTC'")
con.execute("SET preserve_insertion_order=true")
print("Python", sys.version.split()[0], "| DuckDB", duckdb.__version__, "| Pandas", pd.__version__)
print("Source:", SOURCE.name, "| bytes:", SOURCE.stat().st_size)


# ### 1.1 Source fingerprint and raw preview
#
# The SHA-256 identifies the exact local file used. The bounded preview is for inspection; all audit queries below scan the entire source.

# In[2]:


digest = hashlib.sha256()
with SOURCE.open("rb") as file:
    for chunk in iter(lambda: file.read(8 * 1024 * 1024), b""):
        digest.update(chunk)
source_sha256 = digest.hexdigest()
print("9.listens SHA-256:", source_sha256)

RAW_SQL = f"""read_json('{SOURCE.as_posix()}', format='newline_delimited',
    columns={{user_id:'BIGINT', user_name:'VARCHAR', timestamp:'BIGINT',
             track_metadata:'JSON', recording_msid:'VARCHAR'}})"""
con.execute(f"CREATE OR REPLACE VIEW raw AS SELECT * FROM {RAW_SQL}")
print("Raw columns and types:")
display(con.execute("DESCRIBE raw").df())
display(con.execute("""SELECT user_id, user_name, timestamp, recording_msid,
    json_extract_string(track_metadata, '$.artist_name') AS artist_name,
    json_extract_string(track_metadata, '$.track_name') AS track_name
    FROM raw LIMIT 5""").df())


# ### 1.2 Full-source profile before changes
#
# Missing means SQL `NULL` or blank text after trimming. Artist and recording MBIDs are metadata fields, not required for a submitted listen.

# In[3]:


con.execute("""CREATE OR REPLACE VIEW extracted AS
SELECT user_id, user_name, timestamp AS listened_at_unix, recording_msid,
       track_metadata,
       json_extract_string(track_metadata, '$.track_name') AS track_name_raw,
       json_extract_string(track_metadata, '$.artist_name') AS artist_name_raw,
       json_extract_string(track_metadata, '$.release_name') AS release_name_raw,
       json_extract_string(track_metadata, '$.additional_info.recording_mbid') AS recording_mbid_raw,
       json_extract(track_metadata, '$.additional_info.artist_mbids') AS artist_mbids_raw,
       json_extract_string(track_metadata, '$.additional_info.duration_ms') AS duration_ms_raw,
       json_extract_string(track_metadata, '$.additional_info.duration') AS duration_s_raw
FROM raw""")

profile = con.execute("""SELECT COUNT(*) AS raw_rows,
    COUNT(DISTINCT user_id) AS distinct_user_ids,
    COUNT(DISTINCT user_name) AS distinct_user_names,
    COUNT(DISTINCT recording_msid) AS distinct_recording_msids,
    MIN(to_timestamp(listened_at_unix)) AS first_utc,
    MAX(to_timestamp(listened_at_unix)) AS last_utc,
    COUNT(*) FILTER (WHERE user_id IS NULL) AS missing_user_id,
    COUNT(*) FILTER (WHERE user_name IS NULL OR trim(user_name)='') AS missing_user_name,
    COUNT(*) FILTER (WHERE recording_msid IS NULL OR trim(recording_msid)='') AS missing_recording_msid,
    COUNT(*) FILTER (WHERE artist_name_raw IS NULL OR trim(artist_name_raw)='') AS missing_artist_name,
    COUNT(*) FILTER (WHERE track_name_raw IS NULL OR trim(track_name_raw)='') AS missing_track_name,
    COUNT(*) FILTER (WHERE release_name_raw IS NULL OR trim(release_name_raw)='') AS missing_release_name,
    COUNT(*) FILTER (WHERE recording_mbid_raw IS NULL OR trim(recording_mbid_raw)='') AS missing_recording_mbid,
    COUNT(*) FILTER (WHERE artist_mbids_raw IS NULL OR json_array_length(artist_mbids_raw)=0) AS missing_artist_mbids,
    COUNT(*) FILTER (WHERE user_name <> trim(user_name)) AS user_name_trim_changes,
    COUNT(*) FILTER (WHERE artist_name_raw <> trim(artist_name_raw)) AS artist_name_trim_changes,
    COUNT(*) FILTER (WHERE track_name_raw <> trim(track_name_raw)) AS track_name_trim_changes,
    COUNT(*) FILTER (WHERE release_name_raw <> trim(release_name_raw)) AS release_name_trim_changes,
    COUNT(*) FILTER (WHERE listened_at_unix <= 0 OR listened_at_unix > epoch(current_timestamp)) AS invalid_or_future_time,
    COUNT(*) FILTER (WHERE listened_at_unix < epoch(timestamp '2010-01-01')) AS pre_2010_events,
    COUNT(*) FILTER (WHERE duration_ms_raw IS NOT NULL AND trim(duration_ms_raw)<>'' AND try_cast(duration_ms_raw AS DOUBLE) IS NULL) AS failed_ms_conversions,
    COUNT(*) FILTER (WHERE duration_s_raw IS NOT NULL AND trim(duration_s_raw)<>'' AND try_cast(duration_s_raw AS DOUBLE) IS NULL) AS failed_s_conversions,
    COUNT(*) FILTER (WHERE json_array_length(artist_mbids_raw)>1) AS multi_artist_events
FROM extracted""").df().iloc[0].to_dict()
display(pd.DataFrame([profile]).T.rename(columns={0:"value"}))


# ### 1.3 Duplicates and text examples
#
# An exact duplicate compares **all five raw columns**, including full metadata. The candidate event key is tested separately. Repeated user IDs and recording MSIDs are legitimate across events.

# In[4]:


duplicate_audit = con.execute("""WITH exact_groups AS (
 SELECT user_id,user_name,timestamp,recording_msid,track_metadata,COUNT(*) AS n
 FROM raw GROUP BY ALL HAVING COUNT(*)>1),
 event_groups AS (
 SELECT user_id,timestamp,recording_msid,COUNT(*) AS n
 FROM raw GROUP BY ALL HAVING COUNT(*)>1)
 SELECT (SELECT COUNT(*) FROM exact_groups) AS exact_duplicate_groups,
        (SELECT COALESCE(SUM(n-1),0) FROM exact_groups) AS exact_excess_rows,
        (SELECT COUNT(*) FROM event_groups) AS repeated_event_key_groups,
        (SELECT COALESCE(SUM(n-1),0) FROM event_groups) AS repeated_event_key_excess_rows""").df().iloc[0].to_dict()
display(pd.DataFrame([duplicate_audit]).T.rename(columns={0:"count"}))
print("Repeated user_id events:", profile['raw_rows']-profile['distinct_user_ids'])
print("Repeated recording_msid events:", profile['raw_rows']-profile['distinct_recording_msids'])
display(con.execute("""SELECT user_id,user_name AS before,trim(user_name) AS after
FROM extracted WHERE user_name<>trim(user_name) ORDER BY user_id LIMIT 5""").df())


# ## 2. Clean the full source
#
# The output keeps the original Unix timestamp and username for traceability. A source event is retained even if an enrichment field is missing. The clean file has one row per source event; no merge or imputation occurs.

# In[5]:


CLEAN_SQL = """SELECT
  user_id,
  user_name AS user_name_original,
  NULLIF(trim(user_name),'') AS user_name,
  timestamp AS listened_at_unix,
  to_timestamp(timestamp) AS listened_at_utc,
  recording_msid,
  NULLIF(trim(json_extract_string(track_metadata,'$.track_name')),'') AS track_name,
  NULLIF(trim(json_extract_string(track_metadata,'$.artist_name')),'') AS artist_name,
  NULLIF(trim(json_extract_string(track_metadata,'$.release_name')),'') AS release_name,
  NULLIF(trim(json_extract_string(track_metadata,'$.additional_info.recording_mbid')),'') AS recording_mbid,
  CAST(json_extract(track_metadata,'$.additional_info.artist_mbids') AS VARCHAR) AS artist_mbids_json,
  CASE
    WHEN try_cast(json_extract_string(track_metadata,'$.additional_info.duration_ms') AS DOUBLE) IS NOT NULL
      THEN try_cast(json_extract_string(track_metadata,'$.additional_info.duration_ms') AS DOUBLE)
    WHEN try_cast(json_extract_string(track_metadata,'$.additional_info.duration') AS DOUBLE) IS NOT NULL
      THEN try_cast(json_extract_string(track_metadata,'$.additional_info.duration') AS DOUBLE)*1000
    ELSE NULL END AS duration_ms,
  timestamp < epoch(timestamp '2010-01-01') AS flag_pre_2010,
  COALESCE(try_cast(json_extract_string(track_metadata,'$.additional_info.duration_ms') AS DOUBLE),
           try_cast(json_extract_string(track_metadata,'$.additional_info.duration') AS DOUBLE)*1000) <= 0
    OR COALESCE(try_cast(json_extract_string(track_metadata,'$.additional_info.duration_ms') AS DOUBLE),
                try_cast(json_extract_string(track_metadata,'$.additional_info.duration') AS DOUBLE)*1000) > 86400000
    AS flag_duration_out_of_range
FROM raw"""
con.execute(f"COPY ({CLEAN_SQL}) TO '{CLEAN.as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD)")
con.execute(f"CREATE OR REPLACE VIEW clean AS SELECT * FROM read_parquet('{CLEAN.as_posix()}')")
print("Wrote", CLEAN.relative_to(ROOT), "| bytes", CLEAN.stat().st_size)
display(con.execute("SELECT * FROM clean LIMIT 5").df())


# ## 3. Full-dataset validation
#
# Counts below use the full `9.listens` source and full cleaned Parquet. Missing values remain missing. No name-only artist mapping or MusicBrainz merge is attempted.

# In[6]:


after = con.execute("""SELECT COUNT(*) AS clean_rows,
 COUNT(DISTINCT user_id) AS distinct_user_ids,
 COUNT(DISTINCT recording_msid) AS distinct_recording_msids,
 COUNT(*) FILTER (WHERE user_id IS NULL) AS missing_user_id,
 COUNT(*) FILTER (WHERE user_name IS NULL) AS missing_user_name,
 COUNT(*) FILTER (WHERE recording_msid IS NULL) AS missing_recording_msid,
 COUNT(*) FILTER (WHERE artist_name IS NULL) AS missing_artist_name,
 COUNT(*) FILTER (WHERE track_name IS NULL) AS missing_track_name,
 COUNT(*) FILTER (WHERE release_name IS NULL) AS missing_release_name,
 COUNT(*) FILTER (WHERE recording_mbid IS NULL) AS missing_recording_mbid,
 COUNT(*) FILTER (WHERE artist_mbids_json IS NULL OR artist_mbids_json='[]') AS missing_artist_mbids,
 COUNT(*) FILTER (WHERE duration_ms IS NULL) AS missing_duration,
 COUNT(*) FILTER (WHERE flag_pre_2010) AS pre_2010_events,
 COUNT(*) FILTER (WHERE flag_duration_out_of_range) AS duration_out_of_range,
 MIN(listened_at_utc) AS first_utc, MAX(listened_at_utc) AS last_utc
FROM clean""").df().iloc[0].to_dict()
missing_map = [('user_id','missing_user_id'),('user_name','missing_user_name'),
 ('recording_msid','missing_recording_msid'),('artist_name','missing_artist_name'),
 ('track_name','missing_track_name'),('release_name','missing_release_name'),
 ('recording_mbid','missing_recording_mbid'),('artist_mbids','missing_artist_mbids')]
missing_table = pd.DataFrame([{'field':name,'before':profile[key],'after':after[key]} for name,key in missing_map])
display(missing_table)
display(pd.DataFrame([{'raw_rows':profile['raw_rows'],'clean_rows':after['clean_rows'],
 'excluded_rows':profile['raw_rows']-after['clean_rows'],
 'pre_2010_flagged':after['pre_2010_events'],
 'duration_flagged':after['duration_out_of_range'],
 'missing_duration':after['missing_duration']}]))
assert profile['raw_rows']==after['clean_rows']
assert duplicate_audit['exact_excess_rows']==0
assert duplicate_audit['repeated_event_key_excess_rows']==0
assert all(profile[k]==after[k] for _,k in missing_map)
assert profile['distinct_user_ids']==after['distinct_user_ids']
assert profile['distinct_recording_msids']==after['distinct_recording_msids']
assert profile['first_utc']==after['first_utc'] and profile['last_utc']==after['last_utc']
print("PASS: source/clean row, missingness, identity and time bounds reconcile")


# ### 3.1 Conversion and suspicious values
#
# Durations above 24 hours and listens before 2010 are **flags**, not automatic deletions. Missing duration does not mean zero. No source date is shifted out of UTC.

# In[7]:


display(con.execute("""SELECT user_id,listened_at_utc,artist_name,track_name,duration_ms,
 flag_pre_2010,flag_duration_out_of_range
 FROM clean WHERE flag_duration_out_of_range OR flag_pre_2010
 ORDER BY flag_duration_out_of_range DESC, listened_at_utc LIMIT 10""").df())
print("Failed duration_ms conversions:",profile['failed_ms_conversions'])
print("Failed duration seconds conversions:",profile['failed_s_conversions'])
print("Future/nonpositive timestamps:",profile['invalid_or_future_time'])
print("Events with multiple artist MBIDs:",profile['multi_artist_events'])


# ### 3.2 Metric denominator check
#
# An illustrative quality gate for Vision A counts **submitted listens** and distinct listeners. It does not claim causation, artist eligibility, or an approved ranking. `artist_name` is used only as source text; same-name artists may collide. Missing artist keys remain in the all-event denominator and are excluded only from artist-level groups, with that count shown explicitly.

# In[8]:


metric_check = con.execute("""SELECT COUNT(*) AS all_listens,
 COUNT(*) FILTER (WHERE artist_name IS NOT NULL) AS artist_named_listens,
 COUNT(*) FILTER (WHERE artist_name IS NULL) AS no_artist_name,
 COUNT(*) FILTER (WHERE artist_mbids_json IS NOT NULL AND artist_mbids_json<>'[]') AS events_with_artist_mbid,
 COUNT(DISTINCT user_id) AS distinct_listeners,
 COUNT(*) FILTER (WHERE duration_ms IS NOT NULL) AS duration_denominator,
 AVG(duration_ms) AS avg_duration_ms_of_present_values
 FROM clean""").df()
display(metric_check)
assert int(metric_check.all_listens[0])==int(metric_check.artist_named_listens[0]+metric_check.no_artist_name[0])
assert int(metric_check.events_with_artist_mbid[0])<=int(metric_check.all_listens[0])


# ## 4. Five original → expected → actual record checks
#
# The cases are selected from source conditions: whitespace username, missing recording MBID, multi-artist metadata, historical event, and unusual duration. Expected values are computed from **raw input and the rules above before reading the cleaned row**. The composite event key identifies the result. This also checks a Codex suggestion: stripping username whitespace is accepted only after comparing original and cleaned values, while changing case or inferring missing MBIDs is rejected.

# In[9]:


case_conditions = [
 ('username whitespace',"user_name<>trim(user_name)"),
 ('missing recording MBID',"json_extract_string(track_metadata,'$.additional_info.recording_mbid') IS NULL"),
 ('multiple artist MBIDs',"json_array_length(json_extract(track_metadata,'$.additional_info.artist_mbids'))>1"),
 ('historical timestamp',"timestamp<epoch(timestamp '2010-01-01')"),
 ('duration over 24h',"try_cast(json_extract_string(track_metadata,'$.additional_info.duration_ms') AS DOUBLE)>86400000 OR try_cast(json_extract_string(track_metadata,'$.additional_info.duration') AS DOUBLE)>86400")
]
raw_cases=[]
used_keys=set()
for label,condition in case_conditions:
    candidates=con.execute(f"SELECT * FROM raw WHERE {condition} ORDER BY user_id,timestamp,recording_msid LIMIT 20").fetchall()
    chosen=next((row for row in candidates if (row[0],row[2],row[4]) not in used_keys),None)
    assert chosen is not None, f"No unique example for {label}"
    used_keys.add((chosen[0],chosen[2],chosen[4]))
    raw_cases.append((label,chosen))

checks=[]
for label,(user_id,user_name,timestamp,meta_json,recording_msid) in raw_cases:
    meta=json.loads(meta_json)
    info=meta.get('additional_info') or {}
    raw_ms=info.get('duration_ms')
    raw_s=info.get('duration')
    try: expected_ms=float(raw_ms) if raw_ms is not None else float(raw_s)*1000 if raw_s is not None else None
    except (TypeError,ValueError): expected_ms=None
    expected={
      'user_name':user_name.strip() or None,
      'artist_name':(meta.get('artist_name') or '').strip() or None,
      'recording_mbid':(info.get('recording_mbid') or '').strip() or None,
      'listened_at_utc':datetime.fromtimestamp(timestamp,timezone.utc),
      'duration_ms':expected_ms,
      'flag_pre_2010':timestamp<1262304000,
      'flag_duration_out_of_range':None if expected_ms is None else expected_ms<=0 or expected_ms>86400000,
    }
    result=con.execute("""SELECT user_name,artist_name,recording_mbid,listened_at_utc,
      duration_ms,flag_pre_2010,flag_duration_out_of_range FROM clean
      WHERE user_id=? AND listened_at_unix=? AND recording_msid=?""",
      [user_id,timestamp,recording_msid]).df()
    assert len(result)==1
    actual=result.iloc[0].to_dict()
    matches={key:(pd.isna(actual[key]) and value is None) or actual[key]==value for key,value in expected.items()}
    checks.append({'case':label,'event_key':f'{user_id}|{timestamp}|{recording_msid}',
      'original':{'user_name':user_name,'artist_name':meta.get('artist_name'),
                  'recording_mbid':info.get('recording_mbid'),'timestamp':timestamp,
                  'duration_ms':raw_ms,'duration_s':raw_s},
      'expected':expected,'actual':actual,'match':all(matches.values()),'field_matches':matches})

for check in checks:
    print('\nCASE:',check['case'],'| match:',check['match'],'| key:',check['event_key'])
    fields=['user_name','artist_name','recording_mbid','listened_at_utc',
            'duration_ms','duration_s','flag_pre_2010','flag_duration_out_of_range']
    original=check['original']
    display(pd.DataFrame([{'field':field,
      'original':repr(original.get({'listened_at_utc':'timestamp'}.get(field,field))),
      'expected':repr(check['expected'].get(field,'—')),
      'actual':repr(check['actual'].get(field,'—'))} for field in fields]))
    if not check['match']: print('Field matches:',check['field_matches'])
assert all(check['match'] for check in checks)
print('PASS: 5/5 record checks match expected cleaning rules')


# ## 5. Review sample and repeatability
#
# The sample contains the five difficult cases above and 15 deterministic events spread through the source (ordered by the candidate event key). It is for review only; all reported counts are from the full dataset. `homework6_sample.csv` has 20 rows.

# In[10]:


case_where=' OR '.join(['(user_id=? AND listened_at_unix=? AND recording_msid=?)' for _ in checks])
params=[]
for _,row in raw_cases: params.extend([row[0],row[2],row[4]])
difficult=con.execute(f"SELECT * FROM clean WHERE {case_where}",params).df()
other=con.execute("""SELECT * FROM clean ORDER BY user_id,listened_at_unix,recording_msid LIMIT 30""").df()
sample=pd.concat([difficult,other],ignore_index=True).drop_duplicates(
    subset=['user_id','listened_at_unix','recording_msid']).head(20)
assert len(sample)==20
sample.to_csv(SAMPLE,index=False)
print('Wrote',SAMPLE.relative_to(ROOT),'| rows',len(sample),'| bytes',SAMPLE.stat().st_size)
display(sample[['user_id','listened_at_utc','artist_name','track_name','recording_mbid',
                'flag_pre_2010','flag_duration_out_of_range']].head(20))


# ### 5.1 Saved output check
#
# This cell verifies the persisted Parquet and CSV by reopening them. For a clean-room rerun, restart the kernel and run all cells from the top. The same source SHA-256, row count, five record checks, and sample contents should reappear.

# In[11]:


sample_reloaded=pd.read_csv(SAMPLE)
saved=duckdb.sql(f"SELECT COUNT(*) n FROM read_parquet('{CLEAN.as_posix()}')").fetchone()[0]
assert saved==profile['raw_rows']
assert len(sample_reloaded)==20
assert sample_reloaded[['user_id','listened_at_unix','recording_msid']].duplicated().sum()==0
print('PASS: saved Parquet rows',saved,'| sample rows',len(sample_reloaded))


# ## 6. Assignment checklist and decision log
#
# Statuses and evidence are produced from the executed checks. **Not applicable** is used only for a table merge, because this assignment uses one raw file. The cleaning rules were stated in Section 1 before execution.

# In[12]:


checklist = [
 (1,'Done','Candidate Vision A, business question, and proposed distinct-listener metric are in Section 1.'),
 (2,'Done',f"One submitted listen per row; candidate composite key has {duplicate_audit['repeated_event_key_excess_rows']} excess rows (Section 1.3)."),
 (3,'Done',f"Local 9.listens from ListenBrainz work; exact file version SHA-256 {source_sha256}; {SOURCE.stat().st_size} bytes; original unchanged. Download date unrecorded (Section 1.1)."),
 (4,'Done',f"Explicit BIGINT/VARCHAR/JSON load; Unix seconds → UTC; duration unit conversion; failures ms={profile['failed_ms_conversions']}, s={profile['failed_s_conversions']} (Sections 1.2, 2)."),
 (5,'Done',f"Trim outer whitespace, preserve case/IDs; changed usernames={profile['user_name_trim_changes']}, artists={profile['artist_name_trim_changes']}, tracks={profile['track_name_trim_changes']}; before/after in Section 1.3."),
 (6,'Done',f"Exact duplicate excess={duplicate_audit['exact_excess_rows']}; repeated candidate-key excess={duplicate_audit['repeated_event_key_excess_rows']}; user/recording IDs repeat legitimately (Section 1.3)."),
 (7,'Done','Before/after missingness table in Section 3; no missing IDs or values imputed or dropped.'),
 (8,'Done',f"Invalid/future times={profile['invalid_or_future_time']}; pre-2010={after['pre_2010_events']}; out-of-range durations={after['duration_out_of_range']}; flagged, not deleted (Section 3.1)."),
 (9,'Not applicable','No merge was performed. Artist MBIDs remain an array and name-only matching is avoided (Section 2).'),
 (10,'Done',f"Raw={profile['raw_rows']}, clean={after['clean_rows']}, excluded=0; distinct users and recordings and UTC range reconcile (Section 3)."),
 (11,'Done',f"All-event denominator={int(metric_check.all_listens[0])}; artist-named denominator={int(metric_check.artist_named_listens[0])}; duration denominator={int(metric_check.duration_denominator[0])}; NULL groups counted separately (Section 3.2)."),
 (12,'Done','Five original → expected → actual difficult-record checks passed (Section 4).'),
 (13,'Done','This executed notebook ran from original data and reopened its saved Parquet and CSV (Section 5.1). Restart/Run All is the repeat command.'),
 (14,'Done','Team decisions and data coverage limits are documented below.')]
display(pd.DataFrame(checklist,columns=['item','status','evidence']))
decision_log = pd.DataFrame([
 ('UTC timestamp','Unix seconds → UTC; keep original','Unambiguous time comparisons','Raw/clean bounds and invalid/future count reconcile'),
 ('Outer whitespace','Trim names only; preserve case and IDs','Avoid accidental whitespace categories','Before/after examples and change counts'),
 ('Duplicates','Keep all events','No exact or candidate-key duplicate rows found','Full-data duplicate audit'),
 ('Missing IDs','Retain NULL; no name inference','Avoid false MusicBrainz identity','Before/after missingness unchanged'),
 ('Duration','Use ms first, else seconds × 1000; flag >24h or ≤0','Mixed source units; unusual values need review','Failed conversion and suspicious-value counts'),
 ('Old events','Flag pre-2010, retain','Historical imports may be real','Full-data time range and five record checks')],
 columns=['rule','action','reason','check'])
display(decision_log)
display(Markdown(f"""**Remaining limits.** Artist MBIDs are missing for {after['missing_artist_mbids']:,} of {after['clean_rows']:,} listens; recording MBIDs are missing for {after['missing_recording_mbid']:,}. Artist-name grouping can conflate namesakes and collaborations. The dump covers submitted ListenBrainz histories and may not represent a streaming platform. The first observed listen is not necessarily first discovery. Exposure and recommendation impressions are absent. **HUMAN DECISION:** the team must approve eligibility, attribution, observation and follow-up windows before ranking artists or estimating retention."""))


# ## Submission notes
#
# - Run from this directory with the `dso576-project` Python 3.13 kernel (`duckdb`, `pandas`, `nbformat`, `pyarrow`, `ipykernel` are in `pyproject.toml` / `uv.lock`). In VS Code choose **Restart Kernel and Run All**. From a terminal, `uv sync --frozen` followed by `.venv/bin/python -m jupyter nbconvert --execute --to notebook --inplace Homework6.ipynb` works if `nbconvert` is installed; otherwise use VS Code/Jupyter.
# - GitHub branch required by the PDF: `siz_datafit` is the current local branch. Branch URL and commit ID must refer to the **submitted commit**; they are not filled in until the work is committed and pushed.
# - Gradescope requires an individual PDF containing the checklist, decision log, and five record checks. This notebook contains that evidence and can be exported after reviewing your name and final branch/commit details. Do not share the full raw file if its source terms prohibit redistribution.
