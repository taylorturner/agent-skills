---
name: youtube-sermon-transcript
description: Extract, clean, and organize sermon transcripts from YouTube URLs or WebVTT (.vtt) caption files. Use when Codex needs to isolate a sermon from a church service containing worship, offering messages or prayers, and music; retrieve YouTube title, description, livestream date, and other metadata; remove rolling-caption duplication; preserve original timestamps; identify sermon boundaries; or produce readable timestamped paragraphs and logical chapters. Never infer a speaker's identity merely from a list of possible pastors.
---

# YouTube Sermon Transcript

Produce faithful, readable sermon transcript files with original-video timestamps while preserving the relationship between text and the video. Name final deliverables with the service date. Always save the deliverables as files; do not provide the organized transcript only in chat. Separate deterministic caption cleanup from semantic sermon detection and chapter organization.

## Workflow

1. Run `scripts/prepare_transcript.py` on a YouTube URL or local `.vtt` file.
2. Read the generated `.segments.json` and `.cleaned.md` files. For YouTube sources, use the metadata stored in `.segments.json`, including the release/livestream date and description.
3. Identify the sermon boundaries using the service structure and evidence rules below.
4. Organize only the sermon into logical paragraphs and chapters.
5. Proofread the entire selected sermon semantically. Correct obvious ASR spelling, clipped words, duplicated caption fragments, biblical names, Scripture references, and punctuation without changing the speaker's meaning.
6. Determine the service date and write `YYYY-MM-DD.sermon.txt`, `YYYY-MM-DD.sermon.md`, and `YYYY-MM-DD.boundaries.json` beside the prepared files unless the user requests another location. Both transcript files must contain original-video timestamps throughout.
7. Read the final outputs from beginning to end and verify spelling, boundary timestamps, chapter order, and transcript fidelity.

Run:

```bash
python3 scripts/prepare_transcript.py "YOUTUBE_URL_OR_VTT" --output-dir OUTPUT_DIRECTORY
```

The script requires `yt-dlp` only for YouTube URLs. Local VTT processing uses the Python standard library.

## Expected Service Structure

Assume this common order as a strong heuristic, not an inflexible rule:

1. Worship
2. Short message and offering prayer
3. Worship
4. Sermon
5. Worship

Do not select the first substantial spoken passage automatically. Offering messages and prayers occur before the sermon.

## Detect Sermon Boundaries

Use multiple adjacent signals. Never use `[music]` alone because music appears several times.

Strong sermon-start signals include:

- A speaker introduction such as “My name is Brett,” “I’m John,” or “I’m one of the pastors here.”
- A transition out of the second worship block.
- An opening sermon prayer, Scripture reading, sermon title, or sustained teaching immediately after the introduction.
- A speaker identity explicitly stated in the transcript, title, description, or other reliable video metadata.

Strong sermon-end signals include:

- The pastor clearly concluding the teaching.
- A closing prayer that belongs to the sermon; retain this prayer.
- A handoff to the worship team, dismissal, benediction, or sustained `[music]` after the conclusion.

Exclude:

- Opening worship.
- The giving or offering message and its prayer.
- The worship block between the offering and sermon.
- Music, announcements, or unrelated transitions after the sermon.

When a boundary is uncertain, choose the conservative range that preserves complete sermon speech and record the uncertainty and competing evidence in `.boundaries.json`.

## Organize the Sermon

- Preserve the speaker’s words and original order. Do not summarize, paraphrase, modernize, or silently add content.
- Set the speaker to a name only when the transcript or reliable metadata explicitly identifies that person. Visual familiarity, a list of usual pastors, service context, or an unsupported inference is insufficient. Otherwise use `Unknown` in Markdown and `null` in JSON.
- Remove caption duplication, markup, obvious non-speech noise, false starts created by rolling-caption overlap, and unmistakable transcription artifacts.
- Correct punctuation, capitalization, clipped words, and spelling conservatively when context makes the intended wording clear.
- Verify biblical names and recognizable quoted passages against the stated Scripture reference. Correct ASR renderings such as `Yodia`/`Eodia` to `Euodia` and `Syndici` to `Syntyche`; do not leave plausible-looking misspellings merely because they came from captions.
- Correct recognizable proper names only when context provides strong evidence. When uncertain, mark `[unclear]` or retain the uncertain wording and record it instead of inventing a spelling.
- Collapse accidental repeated words and repeated phrase fragments caused by caption overlap. Preserve intentional rhetorical repetition when it is clearly spoken for emphasis.
- Remove caption speaker-change chevrons such as `>` and `>>`. Never place them at the beginning of a Markdown paragraph, where they render as blockquotes. Preserve any actual spoken words that follow them.
- Retain meaningful cues such as `[laughter]` or `[applause]` when relevant. Remove worship-only `[music]` outside the selected sermon.
- Form paragraphs around complete ideas, usually 2–6 sentences.
- Begin every paragraph with the timestamp of its first included caption.
- Create chapters only at meaningful topic transitions. Prefer a small number of substantive chapters over many short sections.
- Give every chapter a descriptive heading and the timestamp at which it begins.
- Keep timestamps from the original full video; do not reset the sermon to `00:00`.
- For YouTube sources, make timestamps clickable in Markdown using `https://youtu.be/VIDEO_ID?t=SECONDS`.

## Output Formats

Use the actual service date—not the processing date—for every final filename. Prefer, in order: a date explicitly supplied by the user, YouTube's livestream/release date from the prepared metadata, a clearly stated service date in the title or description, then the upload date when it reliably represents the service date. If the date is ambiguous, ask the user rather than guessing. Use exactly `YYYY-MM-DD` with no title or video ID in the final filenames.

Always create `YYYY-MM-DD.sermon.txt` with paragraph timestamps and no chapter headings:

```text
[00:34:17]

Paragraph text...
```

Always create `YYYY-MM-DD.sermon.md` with title, detected speaker when supported, chapters, and clickable timestamps:

```markdown
# Sermon Transcript

**Speaker:** Unknown
**Sermon:** [00:34:17](https://youtu.be/VIDEO_ID?t=2057)–[01:21:42](https://youtu.be/VIDEO_ID?t=4902)

## Introduction
[00:34:17](https://youtu.be/VIDEO_ID?t=2057)

Paragraph text...
```

Create `YYYY-MM-DD.boundaries.json` containing:

- `sermon_start` and `sermon_end` as timestamps and seconds.
- `speaker` or `null`.
- Concise start and end evidence copied or closely excerpted from the captions.
- `confidence` as `high`, `medium`, or `low`.
- `uncertainties` as a list, empty when none exist.

Do not finish with transcript content that exists only in the conversation. Confirm that all three files were written successfully and provide links or paths to them.

## Quality Check

Before delivery, verify:

- The offering message and offering prayer are absent.
- The sermon introduction and sermon closing prayer are present.
- Worship before and after the sermon is absent.
- Paragraph and chapter timestamps point to the first included words.
- Both transcript deliverables contain timestamps throughout, not only a single sermon-start timestamp.
- All final filenames begin with the correct service date and contain no sermon title or video ID.
- The date was checked against YouTube release/livestream metadata when the source was a URL.
- The speaker is `Unknown`/`null` unless an explicit identification appears in the transcript or reliable metadata.
- Chapter boundaries follow the argument rather than arbitrary time intervals.
- No paragraph is accidentally rendered as a Markdown blockquote because of caption `>` or `>>` markers.
- No obvious clipped words, caption-overlap repetitions, misspelled biblical names, or malformed Scripture quotations remain.
- A final whole-document proofreading pass was completed after chapter organization, not only on the raw captions.
- The organized transcript contains no invented wording.
