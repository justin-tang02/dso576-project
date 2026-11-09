# Emerging Artist Exposure

Our dashboard is designed for music marketing teams looking to identify emerging artists using ListenBrainz data. Users can compare artists based on audience growth and listening engagement, identify tracks that attract new listeners, and explore which listener segments may be worth targeting for future promotions.

## App and Video Links

* Live Streamlit App: https://dso576-project-emerging-artist-discovery.streamlit.app/
* Demo Video: https://drive.google.com/file/d/1Tpmd70i0Rj6KDhUs-c9NRysDfMnsSvqO/view?usp=sharing
* Github Repository: https://github.com/justin-tang02/dso576-project

## Local Run Instructions
Run these commands in your VSCode terminal:

```
git clone https://github.com/justin-tang02/dso576-project.git
cd dso576-project
pip install -r app_final/requirements.txt
PYTHONPATH="$PWD" streamlit run app_final/streamlit_app.py
```
## Data Scope

We used two ListenBrainz data snapshots from September 28 and October 27, 2026. The September dataset contained approximately 5.02 million cleaned listening records.

For the artist ranking, we focused on 17,827 listeners who appeared in both snapshots and 7,929 eligible artists. Artists needed at least five listeners in each snapshot and no more than 200 listeners in October to qualify.

The Exposure Score combines audience growth (35%), listener recurrence (30%), listening depth (20%), and audience breadth (15%). The Entry Track and Listener Segment analyses use the September listening data.

The dashboard uses summarized listening data and focuses on 17,827 listeners who appeared in both datasets and 7,929 artists who met our ranking criteria.

## Current Limitations

The two snapshots do not cover complete calendar months, so differences between them should not be interpreted as exact month to month growth. Since we only compare listeners who appeared in both snapshots, our results may not represent the full ListenBrainz user base.

Some artists, tracks, and listener segments also have relatively small sample sizes, which may affect the reliability of their metrics. Finally, we chose the Exposure Score weights ourselves, so we don't know yet how well they reflect an artist's actual commercial success.

