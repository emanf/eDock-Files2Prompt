<p align="center"><img src="ss_files2prompt.png?v=1" width="600" alt="Files2Prompt screenshot"></p>

# eDock Files2Prompt

Files2Prompt is a focused eDock utility for collecting selected files from a project and turning their contents into clean, structured text. It is designed for preparing context for AI assistants, debugging sessions, code reviews, documentation, and development help.

## Purpose

When a project contains many files, copying useful context manually is slow and error-prone. Files2Prompt lets you select a project root, exclude irrelevant files, choose exactly what should be included, preview the result, and copy or export the final text.

## Exclude Patterns

The Exclude Patterns dialog supports `.gitignore`-style rules. The default list avoids common source-control, dependency, cache, and build files:

```text
.git/
__pycache__/
node_modules/
.venv/
venv/
*.pyc
*.pyo
.DS_Store
dist/
build/
```

Patterns can be edited, loaded from a file, or reset to the defaults. The pattern syntax supports:

- `*` and other filename wildcards.
- A trailing `/` for directories.
- A leading `/` for root-anchored rules.
- `!pattern` to keep a matching file or directory.
- Comments beginning with `#`.

Saving the patterns automatically rescans the selected root folder.

## Export Format

Each selected file is written as a structured block containing its relative path, part information, character count, line count, and content:

```xml
<file_content name="src/example.py"
part="1/1"
has_more_parts="false"
characters="42"
lines="3">
...
</file_content>
```

This format keeps multiple files distinguishable when the result is pasted into an AI assistant or shared with another developer.

## Splitting Large Exports

Large exports can be split before previewing, copying, or saving:

- Enable or disable splitting.
- Split by Characters or Lines.
- Set the maximum size for each part.
- Character-based splitting prefers newline boundaries when possible.
- Every part keeps file and part metadata.

Splitting is useful when an AI tool, clipboard workflow, or message field has an input-size limit.

## Usage

1. Open <a href="https://github.com/emanf/eDock">eDock</a>.
2. Launch Spotlight and type `>Files2Prompt`.
3. Install the app if it is not installed.
4. Restart eDock when prompted.
5. Launch Files2Prompt from the dock.
6. Click **Select Root Folder** and choose a project folder.
7. Click **Scan Root** if you want to rescan manually.
8. Adjust **Exclude Patterns** when needed.
9. Filter the file list and check the files to include.
10. Click **Add Checked** to build the export list.
11. Click **Preview** to inspect the generated context.
12. Use **Copy All**, **Copy Part**, or **Export** to save the result.
13. Send the copied or exported content to an AI assistant when needed.

## Settings and Data

Files2Prompt stores app-specific data through eDock, including:

- The last selected root folder.
- The current exclude-pattern list.

This allows recurring project exports to be resumed without configuring the app again from scratch.

## App Info

- App name: eDock Files2Prompt
- App ID: `emanf.files2prompt`
- Type: eDock source app
- Category: Utility
- Version: `0.3.3`
- Purpose: Export file content for AI assistance, debugging, and code review
- Minimum eDock version: `0.1.0`
- Repository: <a href="https://github.com/eManF/eDock-Files2Prompt">eDock-Files2Prompt</a>
