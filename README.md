# agent-skills

Reusable Agent Skills for ChatGPT, Codex, and other compatible agent environments.

## Available skills

### YouTube Sermon Transcript

Extracts, cleans, and organizes sermon transcripts from YouTube captions or WebVTT files. It can separate a sermon from the surrounding worship service, preserve timestamps, identify logical chapters, and produce readable transcript files.

See [`youtube-sermon-transcript/SKILL.md`](youtube-sermon-transcript/SKILL.md) for its complete instructions.

## Install in ChatGPT

For a non-technical user, the easiest installation method is a ZIP package attached to a GitHub Release:

1. Download the `youtube-sermon-transcript.zip` release asset.
2. In ChatGPT, open **Skills**.
3. Select **Create**, then **Upload**.
4. Choose the downloaded ZIP file.

Availability can depend on the user's ChatGPT plan and workspace settings.

## Install locally in Codex

Copy or link the individual skill folder into your Codex skills directory. Keep the directory intact so that `SKILL.md`, `agents/`, and `scripts/` remain together.

Typical personal location:

```text
~/.codex/skills/youtube-sermon-transcript/
```

Review a skill and its scripts before installing it. Skills can contain executable code and should be treated like other software dependencies.

## Repository structure

Each top-level skill directory is self-contained and includes a `SKILL.md` file. Supporting scripts, references, and agent metadata live alongside it.

## License

Licensed under the [MIT License](LICENSE).
