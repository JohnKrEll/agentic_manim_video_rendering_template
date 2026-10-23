# Generics intro (example): scene plan

**Status:** done. The reference video and smoke test for the template; build it with `./pipeline build example`.

## Scenes

| # | Class             | Manuscript part                                  | What happens on screen                                                                 | Cues                                            | Length |
| - | ----------------- | ------------------------------------------------ | -------------------------------------------------------------------------------------- | ----------------------------------------------- | ------ |
| 1 | `Opening`         | "Har dere lagt merke til …"                      | `List<string>` and `List<int>` pills, ghost classes that were never written, title card | `ghosts`, `title`                               | 0:09   |
| 2 | `WithoutGenerics` | "Se hva som skjer …" to "Se på følgende:"        | Three container classes typed out, types highlighted, `{ get; set; }` × 3, merged into `Container<T>` | `identical`, `rule`, `smell`, `merge`, `param` | 0:35   |
| 3 | `ContainerT`      | "Her har vi en super simpel …"                   | The one-liner grows to four lines, `<T>` marked, `set`/`get` pills with arrows          | `brackets`, `object`, `value`                   | 0:26   |

## Colour roles in this video

As in DESIGN.md: `ACCENT` (warm) is the type parameter `T` and the
repeated rule; `ACCENT_2` (cool) is a concrete type (`string`, `int`, `Person`).

## Continuity

`WithoutGenerics` ends on the one-line `Container<T>` card; `ContainerT`
starts from exactly that picture (`container_one_line()`), so the cut is
invisible.

## Decisions to check

- The three recordings are cut from the generics intro, so the example's
  opening sentence ("en slik beholder") refers to a part that is not in it.

## Log

- 2026-10-23: built from the generics intro scenes 1, 3 and 4 and their
  recordings. The «× 3» pill was moved under the card: next to it, it was
  outside the frame (found in the stills).
