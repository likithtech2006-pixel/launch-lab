# Launch content templates

Drafts only. Launch Lab never posts. Write every file in `launch/`.

## Tone rules (apply to every post)

- **Specific beats impressive.** "Scores your README 0-100 using 3 simulated visitors" beats
  "revolutionary README intelligence".
- **Banned words** unless literally true and backed by data: revolutionary, game-changer,
  blazingly, insanely, 10x, magic, effortless, seamless, supercharge, unleash, the future of.
- **No fake claims.** No invented users, testimonials, benchmarks or star counts. Numbers must come
  from the repo, the score report or the user. Unknowns become `[TODO: ...]`.
- **Say the limitations.** One honest "what it does not do yet" line builds more trust than any adjective.
- **Emoji:** at most one per post, none in titles. No hashtag walls (max 2-3 on X/LinkedIn).
- **No fake urgency**, no "please upvote", no vote rings: every platform below penalises them.
- First person, maker voice. Short sentences. Link to the repo once.

Gather the facts first: what it does (from `panel.json` truth), install command, demo GIF path,
score and before/after, the comparison table, real limitations, the license.

## show-hn.md

```markdown
# Show HN draft

## Title options (pick one, <= 80 chars, no emoji, no superlatives)
1. Show HN: <Name> – <what it does, plainly>
2. Show HN: <Name>, <concrete outcome> for <audience>
3. Show HN: I built <thing> because <specific problem>

## URL
<repo URL> (link the repo, not a landing page, for open-source projects)

## Maker comment (post immediately as the first comment)
<2-3 sentences: the problem you had, concretely.>
<What it does and how, in 3-5 sentences. Mention the mechanism.>
<What is different from X and Y, honestly, including where they are better.>
<Limitations / what is not done yet.>
<What feedback you want.>

## Likely questions and factual answers
- Q: How is this different from <alternative>? A: <fact from comparison table>
- Q: Does it send my code anywhere? A: <fact>
- Q: Why <language/design choice>? A: <fact>
- Q: What does it cost / license? A: <fact>
- Q: How accurate is <metric>? A: <honest answer, including uncertainty>
(6-10 questions. If an answer is not known from the repo, write [TODO: answer].)

## Timing note
Weekday morning US Eastern is common advice, not a guarantee. Be available for 3-4 hours to reply.
```

## reddit.md

One section per subreddit (3-5 picked from the repo's topic, e.g. r/programming is strict; prefer
niche ones like r/commandline, r/Python, r/rust, r/selfhosted, r/webdev, r/ClaudeAI,
r/opensource, r/SideProject). For each:

- **Rules check:** what self-promotion rules apply (tell the user to read the sidebar; flairs; some
  require a 9:1 participation ratio or a specific weekday "showcase" thread).
- **Title:** native to that subreddit's style (question or "I made X to do Y").
- **Body:** written for that audience: what problem in *their* terms, a GIF link, how to try it,
  what feedback you want. Vary the text between subreddits; identical cross-posts get removed.

## x-thread.md

5-7 posts. Post 1 states the problem + what it does + the GIF (the hook must stand alone). Then:
how it works (one post), a concrete before/after, the comparison, limitations, the link and a
specific ask. Each post <= 280 chars. Mark which post carries the GIF.

## linkedin.md

150-250 words. Lead with the problem in one line. Short paragraphs. What you built, what you
learned building it (one real lesson), link in the post or first comment, 2-3 hashtags max.
No "I'm thrilled to announce".

## devto.md

A real article, not an ad: frontmatter (`title`, `published: false`, `tags` (max 4), `cover_image`),
then: the problem, the approach (with a diagram or code), one interesting technical decision and
its trade-off, results (only real numbers), how to try it, what is next. 800-1500 words.

## product-hunt.md

- **Name**, **Tagline** (<= 60 chars, plain), **Description** (<= 260 chars)
- **Topics** (3), **Gallery plan** (GIF first, then 2-4 screenshots with captions), **First comment**
  (maker story, what is free/open, what feedback you want)
- Note: Product Hunt suits products with a visual UI or broad audience; for a CLI or library, say
  it is optional and lower priority than HN/Reddit.

## calendar.md (14 days)

A table with Day, Date (`[TODO]` if no launch date), Channel, Action, Asset, Done. Pattern:

| Day | Focus |
|---|---|
| -3 to -1 | Final score check (`/launch-lab score`), demo GIF, social preview, topics, release tag, tell 3-5 friends privately for honest feedback (not upvotes) |
| 0 | Show HN (morning), reply to every comment; X thread |
| 1 | 1-2 niche subreddits; LinkedIn |
| 2 | `/launch-lab diagnose` snapshot; fix the top README issue from comments |
| 3-4 | dev.to article; reply to issues; second subreddit batch |
| 5 | Diagnose snapshot; ship a small release addressing launch feedback |
| 7 | Product Hunt (only if it fits); newsletter/awesome-list submissions |
| 8-13 | One retention piece (tutorial, "what I learned from N comments", v0.2 notes); diagnose every 2-3 days |

Use the user's real dates when known. Never schedule auto-posts.
