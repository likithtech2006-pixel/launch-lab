# Stranger Panel: personas, isolation and grading

## Why fold-only

Most visitors decide within one screen. The panel reproduces that: each persona sees only the
README "above the fold" (`scan.py` keeps the first `fold_lines` non-blank-leading lines, default
25: title, tagline, badges, first image, opening text). Images are shown as
`[badge: alt]`, `[image: alt]` or `[animated image: alt]`, so **alt text matters**: a GIF with
alt "demo" tells the persona little, which is also true for screen-reader users.

## Default personas

Defined in `assets/personas.default.json`:

| id | Persona | Looks for |
|---|---|---|
| `skeptical-hn` | Skeptical HN developer | Concrete claims, difference from existing tools, proof over adjectives |
| `beginner` | Beginner developer | Plain language, "is this for me", can I run it in 5 minutes |
| `busy-cto` | Busy CTO evaluating tools | Problem solved for a team, license, maturity, adoption risk |

## Custom personas

Add to `REPO/.launch-lab/config.json`:

```json
{
  "personas": [
    {
      "id": "data-scientist",
      "name": "Data scientist using notebooks",
      "brief": "Lives in Jupyter, knows pandas well, avoids the terminal when possible.",
      "star_bar": "Stars tools that save notebook time and work with pandas out of the box."
    }
  ],
  "replace_default_personas": false,
  "fold_lines": 25
}
```

Keep at least 3 personas in total. Pick personas that match the people you will reach on launch
day (an r/selfhosted persona for a self-hosted app, for example).

## Running the panel

1. **Truth first.** Before reading any persona answer, read the whole repo and write:
   - `truth.purpose`: one sentence, what it actually does (mechanism + outcome).
   - `truth.audience`: one sentence, who it is actually for.
   Note which files you based this on in `truth.derived_from`.
2. `python3 scripts/panel.py prompts REPO` writes `.launch-lab/panel_prompts.json`.
3. Spawn one subagent per persona in parallel with the Agent tool. Pass the prompt verbatim. Do not
   add context, file paths, the truth or other answers. Every round uses **new** subagents so earlier
   versions of the README cannot leak in.
4. Parse each reply as JSON. If a reply is not valid JSON, ask that same subagent once to reply
   with only the JSON; if it still fails, record the persona as failed and say so.

## Grading rubric

Grade each persona's answer against the truth, field by field. Be strict and literal; do not
give credit for what the persona might have meant.

`purpose_match` (compare `what_it_does` with `truth.purpose`):
- **1**: Names the same core function and outcome. Different wording is fine.
- **0.5**: Right category but wrong or missing the key mechanism or differentiator
  (e.g. "a README generator" for a tool that *tests* READMEs).
- **0**: Wrong function, too vague to be falsifiable ("a developer tool"), or the persona said it
  could not tell. **This is a clarity failure.**

`audience_match` (compare `who_its_for` with `truth.audience`):
- **1**: Same audience. **0.5**: Overlapping but too broad or too narrow. **0**: Different audience.

For each clarity failure, quote the fold line most likely responsible and say why it misled.

## panel.json schema

```json
{
  "round": 0,
  "fold_sha": "<copied from .launch-lab/panel_prompts.json>",
  "truth": {
    "purpose": "One sentence.",
    "audience": "One sentence.",
    "derived_from": ["README.md", "src/cli.py"]
  },
  "personas": [
    {
      "id": "skeptical-hn",
      "name": "Skeptical HN developer",
      "response": {
        "what_it_does": "…",
        "who_its_for": "…",
        "would_star": false,
        "confidence": 70,
        "confusions": ["…"],
        "would_make_me_star": "…"
      },
      "grade": {"purpose_match": 0.5, "audience_match": 1, "notes": "Missed that it tests, not writes."}
    }
  ]
}
```

`panel.py validate REPO` checks this and prints understanding, star intent and clarity failures.
