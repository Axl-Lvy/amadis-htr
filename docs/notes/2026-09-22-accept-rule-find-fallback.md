# The accept rule has a path where it cannot protect anything

Date: 2026-09-22
Found while running E2, not by reading the code.

Claim C2 is that the marker-anchor accept rule keeps a generative pass from
rewriting text it was not asked to touch. E2 measured the rule and found a
branch on which the rule is comparing against a line the pipeline had already
corrupted, so an acceptance there says nothing.

**68.3% of E2's offered lines took that branch.** The claim rests on the
remaining 31.7%.

## The mechanism

`source_ocr/correction.py`, `suspect_spans`. Character confidences are aligned
to `textRaw`; the line's `text` may differ, because a drop-cap letter can be
prepended to it. The function handles that with a constant offset:

```python
offset = len(text) - len(raw)
clean = offset >= 0 and text[offset:] == raw
```

When `clean` holds, every suspect word's position in `text` is its position in
`raw` plus the offset, and the spans are exact. When it does not, each suspect
word is located by searching:

```python
idx = text.find(word)
if idx < 0:
    continue
s, e = idx, idx + len(word)
```

`str.find` returns the **first** occurrence. Two low-confidence occurrences of
the same word therefore resolve to the same index, and `mark_text` wraps that
one occurrence twice.

Reproduced against the module itself:

```
raw    = "le roy et le roy vint"
text   = "le roy et le roy vint-"      # suffix differs, so clean is False
spans  -> [('roy', 3, 6), ('roy', 3, 6)]
marked -> "le ⟦roy⟧⟦roy⟧ et le roy vint-"
accept_marker_anchored(...) -> accepted=True, text="le royroy et le roy vint-"
```

The model is shown a line the pipeline mangled. It returns it unchanged. The
rule splits the reply on the markers, compares the outside segments against
`mark_text(original, spans)` — the same mangled construction — finds them
identical, and accepts. The accepted text now duplicates a word.

The rule cannot catch this. It is not a failure of the accept logic: the
corruption happens upstream of it, and the rule's reference is the corrupted
line.

Two smaller consequences on the same path. A suspect word absent from `text`
is dropped silently (`if idx < 0: continue`), so a line can be offered with
fewer spans than the recogniser flagged, and E2's `spans` column under-reports
for those lines. And the second genuine occurrence is never offered for
correction at all.

## Why it is so common

68.3%, not a rare edge case. `clean` fails whenever `text` is not `raw` with a
constant prefix — which covers any line the pipeline post-processed in a way
that changes length non-uniformly, not only drop caps. Nothing in the pipeline
records why, and E2 records only whether.

## What E2 can and cannot say about it

**Can:** how much of its own evidence sits on the branch. `VERDICTS.csv` has a
`clean` column, and `correction-verdicts.csv` aggregates it.

**Cannot:** how often the duplicate-span case actually fired within that 68.3%.
`clean` being false is necessary for the bug, not sufficient — it also needs
two low-confidence occurrences of one word on one line. Measuring that needs
the spans themselves, and the spans are text, which this repository does not
hold. The 68.3% is therefore an upper bound on the exposure and not an estimate
of the damage.

## The fix, which belongs in the pipeline

Search forward from the previous span's end rather than from the start:

```python
idx = text.find(word, pos)
```

and assert the spans are strictly non-overlapping before `mark_text` runs,
dropping the line from correction if the assertion fails. A line that cannot be
marked unambiguously should not be offered; leaving it uncorrected is the
behaviour the accept rule exists to guarantee.

Neither change is made here. This repository evaluates the pipeline and does
not modify it, and a fix applied here would mean E2 had measured something
other than the shipped system.

## What this does to the report

Section 7 carries the mechanism, section 8 carries it as a limitation, and
section 9's C2 verdict is written against the 31.7%, not the whole sample. The
abstract says it too, because a reader who stops there should not come away
believing the rule was measured clean.
