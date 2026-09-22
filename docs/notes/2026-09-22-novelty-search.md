# The novelty search, recorded

Date: 2026-09-22

Section 2 of the report closes with a novelty claim: *to our knowledge no
character error rate has been published for a CATMuS-Print fine-tune on a
sixteenth-century French romance corpus.* The outline fixed the condition for
making it — the claim is made only if the search comes back empty, and the
search is recorded. This is the record.

## What was searched

Thirteen queries, run 2026-09-22 against web search, publisher APIs and the HAL
Solr API:

1. `CATMuS-Print dataset consistent approaches to transcribing manuscripts early modern print`
2. `"CATMuS" print early modern dataset paper 2024 2025 Gabay Clérice ground truth printed`
3. `CATMuS-Print fine-tune character error rate 16th century French printed books kraken`
4. `"CATMuS-Print" fine-tuned model CER reported evaluation results French 16th century Zenodo`
5. `"CATMuS-Print" fine-tuning results CER published paper 2025 2026 roman chevalerie French literary print`
6. `"Amadis de Gaule" OCR HTR character error rate 16th century French romance transcription`
7. `"Trésor des Amadis" OR "Amadis de Gaule" automatic text recognition kraken eScriptorium ground truth`
8. `Amadis Gaule Herberay des Essarts digitisation OCR corpus numérique reconnaissance caractères taux erreur`
9. `HTR fine-tuning 16th-century French printed romance chivalric novel CER kraken evaluation study`
10. `SETAF project 16th century French prints gothic HTR model CER Geneva Jean Michel transcription`
11. `HTR-United catalogue Amadis 16th century French print dataset ground truth`
12. `Gabay Clérice CATMuS Print early modern prints dataset publication DH2024 abstract`
13. HAL Solr API, `title_t:"CATMuS print"` — one record, the Humanistica 2024 paper

Also checked directly: the HTR-United catalogue, which holds no *Amadis*
dataset, and Zenodo's `user-ocr_models` community, which surfaces CATMuS-Print
[Large], [Small] and [Tiny], CATMuS Gothic Print, and CATMuS-JH, a fine-tune on
1966–1976 periodicals. No sixteenth-century romance fine-tune among them.

## The four near misses, and why each one misses

| work | how close | why it is not the claim |
|---|---|---|
| CATMuS Gothic Print, `10.5281/zenodo.10599911` | 16th-century French print, CATMuS family, fine-tuned model | fine-tuned from CATMuS **Medieval**, not CATMuS-Print; SETAF religious and polemical Geneva–Neuchâtel imprints in Gothic type, not romance; and the record publishes **no CER at all**, which was checked on the record itself |
| CATMuS-Print, Humanistica 2024, `hal-04557457` | reports CER for CATMuS-Print | the **generic** model across languages and centuries; no romance corpus and no domain fine-tune |
| Momtaz et al. 2025, `10.3390/electronics14153083` | kraken plus a neural post-corrector, CER 38% to 15% | **15th-century incunabula**, and it does not use CATMuS-Print |
| Tiger 2026, `10.63317/23hc8mveght2` | French, early modern, HTR fine-tuning, CER-focused | **17th and 18th centuries**, and the corpus is not romance |

## What the claim may therefore say

Exactly what section 2 says, and no more. *To our knowledge* is load-bearing: a
literature search cannot rule out an unindexed thesis, a project deliverable or
a non-anglophone venue, and the phrasing is not strengthened beyond it.

## One thing worth knowing

Queries 6 and 11 returned this repository, `github.com/Axl-Lvy/amadis-htr`,
among their top hits. It is already indexed, so a reader repeating the search
will find this work before they find the absence it claims. That is not
circular — the claim rests on the four near misses above, each checked at its
own record — but it is worth stating, because the search is no longer
independent of the thing it is searching for.

## Provenance

The search was run by a subagent in the session of 2026-09-22 and every DOI or
stable URL it returned was fetched and checked before being written into
`report/refs.bib`. Two entries carry no DOI because the ACL Anthology minted
none for those volumes, and one carries a HAL URL for the same reason; three
more carry a `note` recording what could not be read directly. Those caveats
are in the `.bib` file itself rather than here, so they travel with the entry.
