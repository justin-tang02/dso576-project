"""Reusable backend analysis for the Emerging Artist Exposure dashboard.

Modules (each has one job; see BUILD_SPEC.md "Architecture"):
    keys       canonical text keys (stdlib only, shared with the cleaner)
    config     analysis window, thresholds, file paths
    load       read the analysis-ready listens table, population and window filters
    pairs      one row per (listener, artist): discovery, return, repeat
    artists    one row per artist: reach, engagement, growth, concentration
    trends     weekly series per artist
    entry      entry-track table per artist
    segments   listener activity segments and segment return rates
    scoring    live status, shortlist and exposure score (used by the dashboard)
    quality    data coverage summary for the Data Notes view
    store      read/write and validate the aggregate files
"""
