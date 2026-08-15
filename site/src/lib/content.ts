/** Every command and every number on this page is copied verbatim from the
 *  repo's README and worked examples. Nothing here is illustrative. */

export const heroCommand = 'mound arsenal "Roki Sasaki" --game 825051';

export const heroOutput = `                    pitches  velocity  spin_rate  release_extension  horizontal_break  induced_vertical_break  whiff_rate  chase_rate
pitch_type
four-seam fastball       35      98.8     2427.1                7.1              11.2                    16.9        27.3         6.2
splitter                 32      90.2      868.1                7.2               5.3                     1.0        13.6        57.9
slider                   14      87.1     2099.3                7.1               3.0                     0.1        40.0        33.3
forkball                  5      88.2      758.2                7.1               2.8                    -2.0        50.0         0.0`;

export const questions = [
  "How many splitters did Roki Sasaki throw against the Diamondbacks last night?",
  "How often has he thrown it relative to his other pitches over his last four starts?",
  "What does its location look like over that period?",
  "How does he attack one particular hitter, and does that hitter chase the splitter?",
];

export const arsenal = {
  caption: "Roki Sasaki, game 825051",
  rows: [
    {
      pitch: "four-seam fastball",
      color: "var(--color-pitch-fastball)",
      pitches: 35,
      velocity: 98.8,
      spin: 2427.1,
      whiff: 27.3,
      chase: 6.2,
    },
    {
      pitch: "splitter",
      color: "var(--color-pitch-splitter)",
      pitches: 32,
      velocity: 90.2,
      spin: 868.1,
      whiff: 13.6,
      chase: 57.9,
    },
    {
      pitch: "slider",
      color: "var(--color-pitch-slider)",
      pitches: 14,
      velocity: 87.1,
      spin: 2099.3,
      whiff: 40.0,
      chase: 33.3,
    },
    {
      pitch: "forkball",
      color: "var(--color-pitch-forkball)",
      pitches: 5,
      velocity: 88.2,
      spin: 758.2,
      whiff: 50.0,
      chase: 0.0,
    },
  ],
};

export const features = [
  {
    title: "Start from a name",
    code: 'mound search "Roki Sasaki"',
    body: "Resolve a player to an MLB ID, accents optional. Every other command takes the name directly, so you rarely need the ID at all.",
  },
  {
    title: "Filter how you'd ask",
    code: "--last 4 --pitch splitter",
    body: "Last N appearances, a date range, one game, one pitch type, one batter side, one at-bat, one exact pitch. Filters compose freely.",
  },
  {
    title: "Stuff and results together",
    code: "mound arsenal",
    body: "Velocity, spin and movement next to whiff and chase rate, so how nasty a pitch was gets answered from three angles in one table.",
  },
  {
    title: "Charts that arrive finished",
    code: "mound zone --kind heatmap",
    body: "A headline, dek and source render around the strike zone. Scatter, heatmap or KDE, optionally split into vs-LHB and vs-RHB panels.",
  },
  {
    title: "Matchups from either side",
    code: "--batter perdomo",
    body: "Pitcher(batter=...) and Batter(pitcher=...) return the same pitches. Pick whichever player the question is actually about.",
  },
  {
    title: "Broadcast clips, by pitch",
    code: "mound video --limit 1",
    body: "Download the video for one pitch, one at-bat or a whole filtered collection, resolved straight from each pitch's own ID.",
  },
  {
    title: "A cache that can't go stale",
    code: "--cache",
    body: "A finished game never changes, so a hit is always good. A game in progress is never written, so tonight's fourth inning never sticks.",
  },
  {
    title: "Export anywhere",
    code: "--export roki.csv",
    body: "CSV, JSON or Parquet from the CLI, or to_frame() for a pandas DataFrame with every field the feed returned.",
  },
];

export const plots = [
  {
    src: "/plots/roki_splitter_zone.png",
    width: 1005,
    height: 1289,
    label: 'kind="scatter"',
    caption:
      "The default. Points colored by pitch type, using the same fixed palette across every chart.",
    alt: "Strike zone scatter plot of Roki Sasaki's splitter locations",
  },
  {
    src: "/plots/diaz_ff_season_heatmap.png",
    width: 1005,
    height: 1289,
    label: 'kind="heatmap"',
    caption:
      "Binned density for larger samples. No colorbar — darker means more pitches, and the panel stays aligned with every other kind.",
    alt: "Strike zone heatmap of Edwin Díaz's four-seam fastball locations",
  },
];

/** The commands, pitch IDs and pitch details come from step 7 of the Díaz
 *  walkthrough. The poster frames are pulled from the clips those commands
 *  downloaded; only the YouTube IDs originate outside the repo. */
export const clips = {
  commands: [
    "mound video-id a08dfb7d-1acd-3776-a6d8-0f5e80cdb0c6 --out clips/perdomo_triple_aug8.mp4",
    "mound video-id 13f4b8d1-39f4-3499-b696-8a3311899fde --out clips/carroll_triple_aug8.mp4",
  ],
  cards: [
    {
      youtube: "GBGhs2vNCeI",
      poster: "/clips/perdomo-triple-aug8.jpg",
      batter: "Geraldo Perdomo",
      result: "Triple",
      detail:
        "Four-seam fastball, 96.5 mph, middle third of the zone and 0.06 feet off the center of the plate.",
    },
    {
      youtube: "fB3AgDta6dU",
      poster: "/clips/carroll-triple-aug8.jpg",
      batter: "Corbin Carroll",
      result: "Triple",
      detail:
        "Four-seam fastball, 98.6 mph, middle third of the zone and 0.07 feet off the center of the plate.",
    },
  ],
};

export const splitPlot = {
  src: "/plots/roki_splitter_zone_by_stand.png",
  width: 1865,
  height: 1289,
  label: 'split_by="stand"',
  caption:
    "Location isn't mirrored for handedness, so mixing lefties and righties in one panel blurs the picture. Split it into a pair, each with its own zone and pitch count.",
  alt: "Roki Sasaki's splitter locations split into versus-LHB and versus-RHB panels",
};
