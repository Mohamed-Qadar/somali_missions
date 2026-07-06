# Executive Presentation — Deliverables

Prepared for the **Ministry of Foreign Affairs, Federal Republic of Somalia**.

| Deliverable | File |
|---|---|
| **Executive PowerPoint (18 slides, 16:9)** | `Somali_MFA_Consular_Platform.pptx` |
| **Speaker notes (every slide)** | `SPEAKER_NOTES.md` — also embedded in the .pptx notes pane |
| **Executive summary (2 pages)** | `EXECUTIVE_SUMMARY.md` |
| **List of screenshots used** | `SCREENSHOTS.md` |
| **UI improvements made before capture** | `UI_IMPROVEMENTS.md` |
| **Screenshots (20, presentation quality)** | `screenshots/01-home.png … 20-mobile-view.png` |
| **Deck build script (reproducible)** | `build_deck.py` |

## Notes for the presenter

- The deck opens directly in Microsoft PowerPoint (16:9 widescreen). Fonts used are Cambria
  (headings) and Calibri (body) — both ship with Microsoft Office, so the deck renders identically
  on any standard install.
- Speaker notes are in the notes pane of every slide (View → Notes Page), and also collected in
  `SPEAKER_NOTES.md` for printing.
- Every screenshot is from the live application. No feature shown is fictional.
- Suggested length: a 15–20 minute briefing, ~1 minute per slide with time for discussion.

## Regenerating the deck

`python build_deck.py` rebuilds the `.pptx` from the screenshots in `screenshots/`.
