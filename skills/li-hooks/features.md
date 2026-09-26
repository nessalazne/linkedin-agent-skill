# Features to formulas

What you can see in a post, and which `../li-post/hooks.json` formula it
points to. Look at the first two lines for the hook, then the body and close
to confirm. A formula needs its **hook cue**. The body and close cues only
raise confidence.

## Hook cues (lines 1-2)

| cue | looks like | id | formula |
| --- | --- | --- | --- |
| names a common belief, then rejects it | "Everyone says X. I think that's wrong." | 1 | Contrarian Take |
| an action over a counted stretch of time | "I posted every day for 90 days." | 2 | Number Reveal |
| leads with what a mistake cost | "$38,000. That's what one hire cost me." | 3 | Mistake Confession |
| then vs now, and one cause | "Two years ago I was broke. Today..." | 4 | Before / After |
| counted list of lessons | "7 things I wish I knew before..." | 5 | The List Promise |
| years of experience plus "what nobody says" | "After 12 years in sales, the part nobody tells you" | 6 | Insider Secret |
| tells a group to stop | "If you're still cold-calling, stop." | 7 | The Callout |
| a costly scenario, then "what do you do?" | "Your best client asks for a discount. What do you do?" | 8 | Question Trap |
| opens on quoted speech, no setup | `"You're fired."` | 9 | Story Cold Open |
| a hard number or screenshot, one line of context | "$14,212. Last month, from one post." | 10 | The Receipt |
| "X is not why Y is happening" | "Your offer is not why you aren't closing." | 11 | Myth Bust |
| two options side by side, surprise winner | "$12k consultant vs a weekend. The weekend won." | 12 | The Comparison |
| "you're allowed to" / "I don't know who needs this" | "You're allowed to charge more." | 13 | Permission Slip |
| one to three words, full stop, alone | "Fired." | 14 | Pattern Interrupt |
| a normal practice framed as a hidden cost | "Your weekly meeting is quietly costing you a hire." | 15 | The Warning |
| "Good X do A. Great X do B." | "Good managers give feedback. Great ones..." | 16 | Good vs Great |
| task time before and after | "This used to take me 5 hours. Now it's 20 minutes." | 17 | Time Anchor |
| "I never do X. Ever." | "I don't do discovery calls. Ever." | 18 | The Unpopular Rule |
| a superlative plus a broken rule, withheld | "The best hire I ever made had no CV." | 19 | Curiosity Gap |
| quitting or killing something valuable | "I deleted my 40k-follower account." | 20 | The Walk-Away |
| "here's the exact thing, steal it" | "Here's the exact script I use. Steal it." | 21 | The Direct Value |

## Body cues

- **Numbered list, 4+ items:** raises 5, 6, 11, 16.
- **Dated beats** ("March: ...", "June: ..."): raises 2, 4, 17.
- **Line-item money** (non-round figures): raises 3, 10, 12.
- **Dialogue or a scene:** raises 9, 20.
- **Step-by-step instructions or an asset:** raises 21.

## Close cues

- **A question only this post could ask:** raises 1, 8, 18.
- **"Who else...?" / "Agree?":** raises nothing. Flag it as bait.
- **"Comment X and I'll send it":** raises 21, and goes on the "what not to
  copy" list.
- **An identity line** ("If you're X, you already know"): raises 7, 13.

## Scoring

Start a formula at 60 when its hook cue is present. Add 10 for each body or
close cue that supports it, cap at 95. Anything under 60 isn't a match.

## Edge cases

- **Hybrid:** a Story Cold Open (9) that becomes a Mistake Confession (3) by
  line 3. Report both, primary first.
- **Carousel or image post:** classify the caption. Say the visual may be
  doing the work and you can't see it.
- **Free-form narrative:** no hook cue fires. Give the structure and "why",
  no formula.
- **Non-English:** structure and "why" only.
