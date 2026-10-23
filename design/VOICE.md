# Voice guide

How the manuscripts sound. The narrator records them in their own voice, so
this guide is for anyone (human or agent) who gives feedback on a
manuscript or extends it. **The author's wording wins.** When the author
rewrites a suggestion, that rewrite is the rule: add it here.

This version describes the voice of the generics, testing and ASP.NET
videos. Replace it for a different narrator.

## Audience and register

- Students in a backend course, addressed as **"dere"**, consistently (never
  a mix of "du" and "dere").
- Casual Norwegian bokmål, as spoken, with English tech terms used as they
  are in the trade: *code smell*, *property*, *happy path*, *edge cases*,
  *maintainerne*. "Super simpel" and "iffy code-smell" are fine.
- Longer sentences that explain *why*, rather than clipped statements.

## State things directly

Say the positive claim straight out. Avoid contrast framings:

| Avoid                                                      | Prefer                                                    |
| ---------------------------------------------------------- | --------------------------------------------------------- |
| "Testing er ikke bare X, det er også Y"                    | "Testing er nok en måte vi kan snakke sammen på"          |
| "Du ber om kontrakten, ikke klassen"                       | "Vi sier bare hva vi trenger"                             |
| "Ikke et drept program — en kontrollert nedstenging"       | "Dette kalles en kontrollert nedstenging"                 |

No dash punchlines and no "not this, but that" constructions, in the
manuscript or in the captions.

## Moves the author uses

- Open with a question about something the viewers already use:
  "Har dere lagt merke til at …?"
- Link back: "I forrige video så vi …", "Husker dere …?", "Som vi husker fra Basic …"
- Set up an example: "La oss si …", "Se på følgende:"
- Point at the detail: "Legg merke til …"
- Ground it: "Hvor har vi sett dette før?"
- Name the value: "Dette er det generics er fantastisk bra til: …"
- Close: **"Så, kort oppsummert: …"** followed by a bridge,
  "I neste video skal vi …"

## Shape of a video

1. A hook question tied to something familiar.
2. The problem, with a concrete code example (often the version *without*
   the concept, so the code smell is visible).
3. The concept, with the syntax shown as a code block.
4. Details through "Legg merke til …", one at a time.
5. Where the viewers have already met it.
6. "Så, kort oppsummert:" plus the bridge to the next video.

A video is typically 3–7 minutes, with an animation marker
(`*[Animasjon: …]*`) every 20–60 seconds of speech.

## Terminology

- **et typeparameter** (bestemt form *typeparameteret*), **et typeargument**.
- Code names are written as in code: `List<T>`, `Container<T>`, `Value`.
- Keep a term once it is introduced; don't swap synonyms within a video.

## When giving feedback or extending

- Suggest, then let the author decide. Mark what is new so it is easy to
  review.
- Mirror the author's sentences, not a generic "clear writing" style.
- Check consistency: du/dere, gender and form of terms, the same name for
  the same thing.
- Code in the manuscript must compile, or be clearly marked as not
  compiling (`// Kompilerer ikke!`).
