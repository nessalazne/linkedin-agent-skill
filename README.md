# The LinkedIn agent skill (Ness edition)

Twelve Claude skills that run a LinkedIn account. Eleven of them write, and
they need no signup, no API key, nothing to connect. The twelfth posts, through
Blotato, and only after you have said "publish".

Forked from Jake Schincariol's
[linkedin-agent-skill](https://github.com/Jakeschincariol/linkedin-agent-skill)
(MIT). What changed in this edition is at the bottom.

One of them writes your posts off 21 hook formulas. One comments on other
people's posts. One handles the replies under yours. One scores your profile
out of 100 and rewrites what lost points. One plans the week: what to post,
when, and who to engage with.

And one is the humanizer, which is the reason the rest are usable. It strips
the em dashes, the slop vocabulary and the invisible watermark characters out
of a draft, then scores what is left against a five-check detection panel
before you ever see it.

**Nothing gets posted until you say publish.** The writing skills never
touch LinkedIn. `/li-publish` does, once, after you approve the exact text.

## Install

Paste this into Claude:

```
https://github.com/nessalazne/linkedin-agent-skill

Install this skill, then confirm /li-post works.
```

Or do it yourself, in Claude Code:

```bash
git clone https://github.com/nessalazne/linkedin-agent-skill.git
cp -r linkedin-agent-skill/skills/li-* ~/.claude/skills/
```

Or as a plugin:

```
/plugin marketplace add nessalazne/linkedin-agent-skill
/plugin install linkedin-agent
```

Project-local instead of global: copy the same folders into your repo's
`.claude/skills/`. No Claude Code at all? Paste any single `SKILL.md` at the
top of a chat and it runs as a mode - you lose the two Python tools, which is
most of the point of `/li-human`, but the rest works.

Then spend ten minutes on `templates/voice.md`. Copy it to
`~/.claude/linkedin/voice.md` and fill it in, or paste three of your own posts
into Claude and say "write my voice.md from these". Every skill reads that
file. Skip it and everything comes out sounding like everyone else.

## The twelve

| command | what it does |
| --- | --- |
| `/li-post` | One idea into a post. Three hook options from [21 formulas](skills/li-post/hooks.json), one full draft, humanized before you see it. |
| `/li-comment` | Comments on other people's posts. Nine types, picked by what the post actually is. Never "Great post!". |
| `/li-reply` | The thread under your own post. Sorts every comment into lead / substance / peer / support / noise, then writes in that order. |
| `/li-profile` | Scores your profile against a [12-part rubric](skills/li-profile/rubric.json) out of 100, then rewrites in fix-first order. |
| `/li-plan` | The week. What to post, when to post it, and the 10 people to engage with. Writes `~/.claude/linkedin/plan.md`. |
| `/li-human` | The humanizer. Two scripts that actually run. See below. |
| `/li-carousel` | Document posts. Slide-by-slide copy, the cover that earns the swipe, and the PDF to upload. |
| `/li-repurpose` | One video, newsletter or transcript into a week of posts that each stand alone. |
| `/li-dm` | The 200-character invite note, the first message, and the two follow-ups. Two. |
| `/li-inbox` | Triages the inbox into lead / recruiter / peer / ask / spam, and tells you which tell gave the sequence away. |
| `/li-audit` | Post-mortem on what you have already published. Ranks by engagement rate and reach multiple, not impressions. |
| `/li-publish` | Posts or schedules the approved draft to LinkedIn through Blotato. Asks for the word "publish" first, polls until it is live, prints the URL. See below. |

## The humanizer

`/li-human` ships two Python scripts with no dependencies. They run on your
machine, on your text, and nothing is uploaded.

```bash
python3 humanize.py draft.txt --report      # clean it, show every change
python3 detect.py draft.txt                  # score it, five checks
python3 detect.py before.txt after.txt       # prove the delta
```

**What comes out automatically:**

- **Invisible characters.** Zero-width spaces and joiners, word joiners, soft
  hyphens, byte-order marks, Unicode tag characters, non-breaking and narrow
  spaces. Your keyboard does not make these. They survive copy-paste and they
  are invisible in every editor you own.
- **Typography.** Em dash to comma, en dash to hyphen, curly quotes to
  straight, ellipsis to three dots.
- **The lexicon.** 113 stock words and phrases with plain-English
  replacements - delve, leverage, robust, seamless, crucial, testament to, "in
  today's fast-paced world", "let that sink in" - with capitalisation preserved
  and URLs untouched. It lives in
  [`slop.json`](skills/li-human/slop.json) and it is meant to be edited.

**What gets flagged instead of fixed:** "It's not just X, it's Y", rule-of-three
triads, one-word rhetorical questions, hashtag walls, reflex engagement bait,
uniform sentence length. Changing the shape of a sentence needs judgement, so
those are handed back for a rewrite rather than mangled by a regex.

**The five checks**, scored 0-100, higher is more human:

| check | what it measures |
| --- | --- |
| BURSTINESS | sentence-length variation. Models write even. |
| SPECIFICITY | numbers, names and concrete markers per 100 words |
| SLOP DENSITY | lexicon hits per 100 words |
| FINGERPRINT | invisible characters, em dashes, curly quotes per 1,000 |
| VOICE | contractions, person, structural tells |

The verdict weights the mean at 60% and the **weakest single check** at 40%,
because a detector only needs one signal to fire.

Run against a deliberately terrible draft:

```
  BURSTINESS    ##################......  73.0
  SPECIFICITY   ######################## 100.0
  SLOP DENSITY  ........................   0.0    19 stock terms, 24.1 per 100 words
  FINGERPRINT   ........................   0.0    1 invisible, 1 em dash, 3 curly quote
  VOICE         ########................  33.3    3 structural tells
  ------------------------------------------------------------
  HUMAN SCORE   ######..................  24.8   FLAGGED
```

After `humanize.py`, with the flagged structures still unrewritten:

```
  HUMAN SCORE   #################.......  69.7   REVIEW    (+44.9)
```

The last stretch to PASS is the part the script deliberately leaves to you.

## Publishing

`/li-publish` is the one skill that sends anything. It uses
[Blotato](https://blotato.com/?ref=ness), which is an approved LinkedIn partner, so the
post goes through LinkedIn's own partner API rather than a browser pretending
to be you. It needs two lines in `~/.claude/linkedin/.env`:

```
BLOTATO_API_KEY=your-key
BLOTATO_ACCOUNT_LINKEDIN=1234
```

The account id comes from Blotato's account list. Then:

```bash
python3 skills/li-publish/publish.py --check              # is that id really LinkedIn?
python3 skills/li-publish/publish.py draft.txt --dry-run  # show the payload, send nothing
python3 skills/li-publish/publish.py draft.txt            # post now
python3 skills/li-publish/publish.py draft.txt --schedule next_slot
python3 skills/li-publish/publish.py draft.txt --schedule 2026-09-22T22:15:00Z
python3 skills/li-publish/publish.py draft.txt --image cover.png
```

Inside Claude the skill does this for you, but it will not run the last four
until you type the word "publish" under the final text. It polls Blotato every
20 seconds until the post is published, scheduled or failed, and prints the
URL. Every send is appended to `~/.claude/linkedin/log.md`.

The script needs Python 3 and the `requests` package. Nothing else is
uploaded anywhere; your draft goes to Blotato and from there to LinkedIn.

## The fine print, which is the honest part

**The writing skills do not post to LinkedIn, and they should not.** There is
no official API for posting to a personal profile without an approved partner
app, and automating the site with a browser or a third-party tool violates
[LinkedIn's User Agreement](https://www.linkedin.com/legal/user-agreement) and
gets accounts restricted. So every writing skill ends the same way: a
copy-ready block. The only way out of this pack is `/li-publish`, which goes
through a partner app and asks you twice. That is the design, not a setting.

**The five checks are local heuristics, not detector APIs.** They are modelled
on the signals public detectors key on, and they run entirely on your machine.
They are not GPTZero, Originality, Copyleaks, Winston or Turnitin, they do not
call those services, and they cannot promise those verdicts. Fixing what they
measure tends to move those numbers, because they are measuring the same
underlying things. That is the whole claim. Nobody can honestly sell you
"undetectable", and anybody who does is selling you something.

**The invisible-character pass is real and it is narrow.** It removes the
zero-width and format characters that end up in generated text and survive a
copy-paste. That is a genuine, checkable fingerprint. It is not a claim about
defeating a cryptographic watermarking scheme, and this repo does not make
one.

**Nothing here fabricates.** No invented metrics, clients or outcomes go under
your name. If a draft needs a number you have not given, it comes back with
`{{your number}}` in it and a flag, every time.

## Files

```
skills/li-post/hooks.json        21 hook formulas: template, example, what it is for, how it gets ruined
skills/li-human/slop.json        the lexicon: 113 terms, 17 invisible classes, 11 structural tells
skills/li-human/humanize.py      the three cleaning passes
skills/li-human/detect.py        the five-check panel
skills/li-profile/rubric.json    the 100-point profile score
skills/li-publish/publish.py     the Blotato sender: check, dry run, post, schedule, poll
templates/voice.md               your voice profile. Fill this in first.
```

## What changed in the Ness edition

- `/li-publish`: new skill and `publish.py`, posting or scheduling through
  Blotato's LinkedIn partner integration, with a dry run, an account check,
  a 3,000 character guard and status polling.
- `slop.json`: added vibrant, "let's dive in", "dive in", "game changer",
  "I hope this helps", and an announcement-opener structural tell, to match
  the house humanizer rules.
- `/li-post`, `/li-plan`, `/li-repurpose`, `/li-carousel`: one line each
  pointing at `/li-publish` after the user's yes. Nothing else in those
  skills changed.
- Plugin manifests and this README.

## Credit

Original pack by Jake Schincariol, [opusjake.ai](https://opusjake.ai). The
full write-up is at
[opusjake.ai/r/linkedin-agent](https://opusjake.ai/r/linkedin-agent).
This edition is maintained by Ness Alazne,
[builds.digicuratoragency.com](https://builds.digicuratoragency.com).

## License

MIT. Take it, change it, ship it.
