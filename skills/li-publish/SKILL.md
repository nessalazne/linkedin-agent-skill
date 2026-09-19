---
name: li-publish
description: >-
  Post or schedule an approved LinkedIn draft through Blotato, the one route to
  a personal profile that does not break LinkedIn's rules. Use when the user
  says "post this", "publish it", "schedule this post", "send it to LinkedIn",
  or answers "publish" after /li-post. Requires a humanized draft and two
  explicit yeses. Never runs on its own.
---

# li-publish

The only skill in this pack that touches LinkedIn. The other eleven write.
This one sends, and only after the user has said so twice.

It goes through Blotato, an approved LinkedIn partner, using the account the
user pinned in `~/.claude/linkedin/.env`. No browser, no cookies, no scraping.

## Before you run anything

1. **The draft must have been through `/li-human` in this conversation** and
   the user must have said "yes" to it. If either is missing, run `/li-human`
   now, show the result, and ask. Do not publish a draft you have not cleaned.
2. **Check the keys exist.** `~/.claude/linkedin/.env` needs
   `BLOTATO_API_KEY` and `BLOTATO_ACCOUNT_LINKEDIN`. If it is missing, tell
   the user exactly those two lines and stop. Never ask them to paste the key
   into the chat.
3. **No links in the body.** LinkedIn suppresses posts with outbound links.
   If the draft has one, move it out, tell the user to add it as the first
   comment after publishing, and print the link so they can.

## The second yes

Show the user, in one block:

```
PUBLISH CHECK
account:   LinkedIn (BLOTATO_ACCOUNT_LINKEDIN from .env)
when:      now  |  next free slot  |  2026-09-22 08:15 local (22:15 UTC)
image:     none  |  cover.png
length:    1,140 characters

<the final text, exactly as it will go out>

Reply "publish" to send it, or tell me what to change.
```

Wait for the word "publish". "yes", "ok", "looks good" are not enough for an
action that goes out under their name. Ask once more if it is ambiguous.

## Scheduling

Blotato wants ISO 8601 UTC. Convert from the user's local time, say both, and
put the UTC one in the command. Three modes:

- `--schedule now` (default)
- `--schedule next_slot` uses Blotato's next free slot for that account
- `--schedule 2026-09-22T22:15:00Z` for an exact time

## Run it

Write the approved text to a temp file exactly as shown, then:

```bash
python3 publish.py draft.txt
python3 publish.py draft.txt --schedule next_slot
python3 publish.py draft.txt --schedule 2026-09-22T22:15:00Z
python3 publish.py draft.txt --image cover.png
```

The script polls Blotato every 20 seconds until the post is `published`,
`scheduled` or `failed`, up to ten minutes, and prints one of:

```
PUBLISHED https://www.linkedin.com/feed/update/...
SCHEDULED 2026-09-22T22:15:00Z
FAILED <reason>
```

Do not end your turn while it is still polling. Relay the final line to the
user with the URL. If it says FAILED, quote the reason and do not retry with
the same command; the reason tells you what to fix.

If the user has not set up the keys yet, `python3 publish.py --check` confirms
the pinned account is actually LinkedIn without creating anything.

## After

The script appends a line to `~/.claude/linkedin/log.md` with the date,
status, schedule, URL and first line, so `/li-audit` can find it later. If
`/li-post` already logged the draft on the first "yes", leave both lines; the
audit reads the status column.

## Never

- Never run the script without the word "publish" from the user in this
  conversation.
- Never publish to any platform other than LinkedIn from this skill, even if
  the workspace has other accounts.
- Never change the text between the PUBLISH CHECK and the command. What they
  approved is what goes out.
