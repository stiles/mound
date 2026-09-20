# Ohtani's strikeouts had a familiar finish: down and away

His strikeout rate changed little across two 20-game stretches. The pitches that finished those at-bats told a different story.

The strikeouts looked familiar: Shohei Ohtani reaching for another pitch down and away. Yet over the 20 games ending Aug. 16, 2026, he struck out only twice more than in the previous 20.

The bigger change was where those strikeouts ended. Twelve finished on pitches outside the zone on the away side, up from four. Against breaking balls and offspeed pitches in that area, he swung at 25 of 56, compared with 18 of 63 in the earlier stretch.

That is a pattern worth examining, though still too small a sample to establish a lasting change. The question is more specific than whether Ohtani was striking out too much: what was happening on the pitches he could have let go?

## A different route to strike three

The comparison covers 40 games, split into two equal stretches. Ohtani struck out in 23.0% of his plate appearances in the first and 26.2% in the second. The difference amounts to two more strikeouts in three fewer plate appearances.

| | June 28–July 24 | July 25–Aug. 16 |
| --- | ---: | ---: |
| Games | 20 | 20 |
| Plate appearances | 87 | 84 |
| Strikeouts | 20 | 22 |
| Strikeout rate | 23.0% | 26.2% |
| Strikeouts ending outside the zone, away | 4 | 12 |
| Breaking and offspeed pitches outside the zone, away | 63 | 56 |
| Swings at those pitches | 18 | 25 |
| Chase rate on those pitches | 28.6% | 44.6% |

The last two rows explain why the at-bats could look different even with a similar strikeout total. Pitchers threw fewer breaking and offspeed pitches outside the zone on the away side in the second stretch. Ohtani swung at seven more of them.

Here are those swings in each window. The charts show the catcher's view, so away from the left-handed Ohtani is to the left.

![Ohtani's swings at breaking and offspeed pitches outside the zone on the away side, across two 20-game stretches](../images/ohtani_chase_panels.png)

To build the comparison in Mound, start with the pitches Ohtani faced and split them by date:

```python
from mound import Batter

ohtani = Batter("Shohei Ohtani")
faced = ohtani.pitches(since="2026-06-28", until="2026-08-16", cache=True)
prior = faced.filter(until="2026-07-24")
recent = faced.filter(since="2026-07-25")
```

Those fixed dates keep the comparison intact when the example is run later. The collection contains 617 pitches in the original analysis, with 308 in the second window.

## Where the strikeouts ended

Ten of the recent 22 strikeouts finished in the low-away quadrant outside the zone. Baseball Savant calls that zone 13. Eight of those ten came on breaking or offspeed pitches.

![The 22 pitches Ohtani struck out on, July 25 to Aug. 16, 2026](../images/ohtani_strikeout_pitches.png)

The pitch families produced different endings. Nine strikeouts finished on four-seam fastballs or sinkers; eight of those were called strikes or foul tips. All 13 strikeouts on breaking or offspeed pitches ended on swings, and all 13 pitches crossed below the middle of the zone.

That doesn't mean every swing was a chase. Four of those pitches were in the bottom-inside corner of the strike zone. But the low-away cluster gives the initial impression something concrete to rest on.

To isolate the finishing pitches, keep one row per plate appearance before selecting strikeouts:

```python
ends = recent.filter(ends_at_bat=True).to_frame()
strikeouts = ends[ends.at_bat_result.str.contains("Strikeout", na=False)]

print(strikeouts[["game_date", "pitcher_name", "pitch_type", "zone", "pitch_call"]])
```

The order matters. Savant repeats the at-bat result on every pitch, so filtering for strikeouts alone would include the entire at-bat. `ends_at_bat=True` keeps the pitch that finished it.

## More swings at pitches outside the zone

Chase rate measures swings at pitches outside the strike zone, divided by all pitches thrown there. It distinguishes a hitter offering more often from a pitcher simply throwing more pitches to the same area.

In the recent window, Ohtani chased 44.6% of the breaking and offspeed pitches outside the zone on the away side. Against the fastball group in that area—four-seamers, sinkers and cutters—he chased 20.8%.

| Pitch group, outside the zone on the away side | Pitches | Swings | Chase rate |
| --- | ---: | ---: | ---: |
| Four-seamers, sinkers and cutters | 53 | 11 | 20.8% |
| Breaking and offspeed pitches | 56 | 25 | 44.6% |

The difference describes his decisions in this sample. It cannot tell us whether he recognized a pitch late, was protecting with two strikes or had something else in mind.

The low-away location itself was familiar in both periods. Pitchers put 50 breaking and offspeed pitches in that quadrant in the earlier window and 49 in the later one. Its continued use helps explain the repeated look of those at-bats, but the counts alone don't establish a coordinated plan or show that the pitches were equally difficult to hit.

Individual pitch-type rates need even more care. Ohtani chased more than half the out-of-zone sliders and sweepers in the recent window. His splitter chase rate was 100%, but that meant one swing at one pitch.

## The swings behind the numbers

The video brings the low-away cluster into focus. These seven strikeouts all ended on breaking or offspeed pitches in that area:

[![Ohtani striking out on breaking and offspeed pitches away, seven clips back to back](https://i.ytimg.com/vi/N4QMdEfN15M/maxresdefault.jpg)](https://www.youtube.com/watch?v=N4QMdEfN15M)

The lowest two pitches were curveballs from Freddy Peralta and Payton Tolle. They crossed about seven and eight inches above the ground, and both were recorded as swinging strikes on blocked pitches. The sequence also includes sliders, a sweeper, a splitter and a changeup.

Eight strikeouts met that pitch-and-location filter in the recent window. Seven clips were available when the video was assembled; the Aug. 16 changeup from Logan Henderson was missing. The [full compilation](https://www.youtube.com/watch?v=0JUvfzH4aho) includes 21 of the 22 strikeouts, making it possible to compare the low chases with the called strikes and foul tips elsewhere.

## A pattern, with limits

A rise from 18 chases in 63 opportunities to 25 in 56 is a 16-percentage-point difference. It is also a comparison of two short stretches against different pitchers, with potentially different counts and pitch quality. It deserves attention without being treated as a diagnosis.

The strikeout locations changed more visibly than the strikeout rate. Twelve ended outside the zone on the away side, compared with four before; eight of the recent twelve were on breaking or offspeed pitches. Those are related findings, but different groups, and neither tells us why Ohtani swung.

The next useful question is whether the difference persists after accounting for count. A hitter protecting with two strikes faces a different decision from one ahead in the count. For these 40 games, the evidence supports a narrower observation: Ohtani offered more often at breaking and offspeed pitches outside the zone on the away side, and more of his strikeouts finished there.

## Reproduce the analysis

The [companion script](../../examples/shohei_spin_chase.py) prints the tables, lists each strikeout pitch and saves the charts:

```bash
python examples/shohei_spin_chase.py
```

It writes to `examples/output/` and needs access to MLB's Stats API and Baseball Savant. The numbers shown here are from the original analysis; upstream corrections can change later results. Completed game feeds are cached for reuse.

The grouping below includes sliders, sweepers, slurves, curveballs, knuckle curves, changeups and splitters. Zones 11 and 13 are the two outside quadrants on Ohtani's away side. They include pitches above or below the zone on that half, as well as pitches beyond its outer edge.

With `prior` and `recent` from the first code block, this produces the comparison:

```python
import pandas as pd

BREAKING_OFFSPEED = [
    "slider", "sweeper", "slurve", "curveball", "knuckle curve", "changeup", "splitter",
]
AWAY_OUTSIDE = [11, 13]


def summarize(window):
    ends = window.filter(ends_at_bat=True).to_frame()
    strikeouts = ends[ends.at_bat_result.str.contains("Strikeout", na=False)]
    opportunities = window.filter(pitch_type=BREAKING_OFFSPEED, zone=AWAY_OUTSIDE).to_frame()
    return {
        "plate appearances": len(ends),
        "strikeouts": len(strikeouts),
        "strikeout rate": round(100 * len(strikeouts) / len(ends), 1),
        "breaking/offspeed outside, away": len(opportunities),
        "swings": int(opportunities.is_swing.sum()),
        "chase rate there": round(100 * opportunities.is_swing.mean(), 1),
        "strikeouts outside, away (all pitches)": int(strikeouts.zone.isin(AWAY_OUTSIDE).sum()),
    }


print(pd.DataFrame({"Jun 28–Jul 24": summarize(prior), "Jul 25–Aug 16": summarize(recent)}))
```

The strikeout-location row counts all pitch types, while the chase rows count only the specified breaking and offspeed pitches. Strike-zone membership comes from measured location and the hitter's recorded zone, not the umpire's call.

For quick checks, the CLI also supports hitter-first queries:

```bash
mound faced-arsenal "Shohei Ohtani" --since 2026-07-25 --until 2026-08-16 --cache
mound faced "Shohei Ohtani" --since 2026-07-25 --until 2026-08-16 --ends-at-bat --cache
```

To assemble the video, run the [supercut script](../../examples/shohei_strikeout_supercut.py). It requires ffmpeg on `PATH`, downloads the available clips, labels them and joins them into one file. `--spin-away` is the script's shorthand for the breaking-and-offspeed group above.

```bash
python examples/shohei_strikeout_supercut.py --spin-away
python examples/shohei_strikeout_supercut.py  # all strikeouts in the window
```

Clips are reused from `examples/output/clips/`; availability may differ from when the published compilations were made.
