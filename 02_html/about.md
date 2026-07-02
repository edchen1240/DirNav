# About DirNav

DirNav is a personal directory navigator. It turns a `projects.json` manifest into a local dashboard, then opens folders, urls, and files through a custom `kickoff://` URI scheme that bridges the browser and PowerShell.

## How to use

- Click **Kickoff** on any card to open every checked folder, url, and file. Uncheck items first to open a subset.
- Click **Open P00** to open the project log in VSCode. Shift+click opens its folder in Explorer. Ctrl+click copies the P00 path to the clipboard.
- Hold Ctrl while clicking any folder link to copy its path to the clipboard.
- Use the search box at the top to fuzzy-find any folder, url, file, or P00 path across every project.
- Click attribute chips to filter cards. Click **Reset** to clear chips and the search.

## Header buttons

- **projects.json** — Click opens the manifest in VSCode. Shift+click opens its folder. Ctrl+click copies the path.
- **Compile** — Re-runs `[B]_P01-Compile Dashboard.bat` to regenerate `index.html` after editing the manifest.
- **About** — This dialog. Edit `02_html/about.md` to change the content (no recompile needed).

## Links

- [GitHub repo](https://github.com/edchen1240/DirNav)
- [Hosted demo](https://edchen1240.github.io/DirNav/)

MIT licensed.
