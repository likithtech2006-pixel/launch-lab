# Post-launch star conversion diagnosis

## Data

`scripts/github_metrics.py` calls the GitHub REST API through `gh` (your own auth, nothing else):

| Endpoint | Data | Limits |
|---|---|---|
| `/repos/{r}/traffic/views` | daily views + unique visitors | last 14 days, push access needed |
| `/repos/{r}/traffic/clones` | daily clones + unique cloners | last 14 days |
| `/repos/{r}/traffic/popular/referrers` | top 10 referrers (views, uniques) | 14-day aggregate, no daily breakdown |
| `/repos/{r}/traffic/popular/paths` | top 10 pages | 14-day aggregate |
| `/repos/{r}/stargazers` (`star+json`) | timestamp of every star | full history; capped at 100 pages (10k stars) |

Each run appends a snapshot to `.launch-lab/history.json`. Daily series from all snapshots are
merged, so running it every few days builds a trend longer than GitHub's 14-day window.

## Metrics

- **Star conversion rate** = new stars / unique visitors for the same days. Daily uniques are
  summed, so a person visiting on two days counts twice: the rate is a lower bound.
- **Per period**: last 7 days, previous 7 days, all tracked days.
- **Per referrer**: GitHub does not say which referrer a stargazer came from. With two or more
  snapshots, the script splits the stars gained between consecutive snapshots across referrers in
  proportion to each referrer's *new* unique visitors in that interval (14-day aggregates are
  differenced and clamped at 0). Different referrers dominate different intervals, so the rates
  separate over time. With one snapshot it reports traffic share only and says so. Treat
  per-referrer conversion as directional.

## Diagnosis rules

Thresholds are defaults, overridable in `.launch-lab/config.json` under `"diagnosis"`:
`high_traffic_per_day` 30, `low_conversion` 0.02, `high_conversion` 0.04, `spike_factor` 4,
`flat_ratio` 0.25, `min_uniques` 10. They are rules of thumb, not industry benchmarks: tune them
for your niche.

| Pattern | Rule | Diagnosis | Meaning |
|---|---|---|---|
| High traffic, low conversion | uniques/day >= 30 and conversion < 2% | `readme` | People arrive and leave. The first screen does not convince them. |
| Low traffic, high conversion | uniques/day < 30 and conversion >= 4% | `distribution` | The README works; not enough of the right people see it. |
| Low traffic, low conversion | both low | `readme` then `distribution` | Fix the funnel before buying traffic. |
| Spike then flat | peak >= 4x median and >= 20 uniques, peak not in the last 2 days, last-7-day mean <= 25% of peak | `retention` | Launch worked once; nothing brought people back. |
| Both good | high traffic, conversion >= 2% | `healthy` | Keep the cadence. |
| No data | no traffic rows at all | `insufficient-data` | Check `gh auth status` and push access. |

`retention` can co-occur with the others; the report lists secondary diagnoses.
Confidence is `low` under 10 uniques or 5 days of data, `medium` under 200 uniques, else `high`.

## Turning a diagnosis into actions

Always make actions specific to the data, not generic advice:

- **readme**: name the top referrer and tailor to it (HN: specifics and the comparison;
  Reddit: problem in the subreddit's words; X: the GIF). Offer `/launch-lab panel` and point at the
  top fixes in `launch/report.md`. If popular paths show visitors reaching `/issues` or
  `/releases` but not starring, the README is likely fine but install may be failing: offer
  `/launch-lab install`.
- **distribution**: list launch channels from `launch/calendar.md` not yet seen in referrers. Never
  suggest vote-asking, buying stars or spam.
- **retention**: propose a follow-up content plan: release notes post, tutorial, FAQ from launch
  questions, good-first-issues, a second launch angle 2-3 weeks later.
- Clones much higher than stars (> 2x uniques cloning vs starring) suggests people try it but do
  not come back to star: add a short "If this helped, a star helps others find it" line at the
  end of the README (once, not above the fold).

## Offline / eval input

`--from-file` accepts the same shape `fetch()` builds (or a list of them, as several snapshots):

```json
{
  "repo": "owner/name", "fetched_at": "2026-10-20T12:00:00+00:00", "stars_total": 140,
  "views": {"views": [{"timestamp": "2026-10-07T00:00:00Z", "count": 40, "uniques": 30}]},
  "clones": {"clones": []},
  "referrers": [{"referrer": "news.ycombinator.com", "count": 900, "uniques": 700}],
  "paths": [],
  "stargazers": [{"starred_at": "2026-10-07T10:00:00Z"}]
}
```
