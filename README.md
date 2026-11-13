# lenso_optout

Semi-automated bulk submission of the [lenso.ai](https://lenso.ai/en/opt-out) image opt-out form.

If you need to remove many images of yourself from lenso.ai's reverse image search, filling the opt-out form by hand for each one is slow: every submission requires re-uploading an image, re-typing your details, and re-ticking four consent checkboxes. This script does all of that for you — it fills the form for each image in a folder, one at a time, and pauses so **you** click Submit in your own browser before it loads the next one. You stay in the loop for the actual submission; the script only handles the repetitive form-filling.

## How it works

- Connects to your **normal, already-running Chrome** over its remote debugging port (CDP) instead of launching a separate automated browser. The form is submitted from your real browser session.
- Walks every image in a folder in natural numeric order (`2.jpg` before `10.jpg`).
- For each image: loads the opt-out page, dismisses the cookie banner, uploads the image, fills in your name/email/description, and ticks the four consent checkboxes.
- Waits for you to click **Submit** in the browser, then press **Enter** in the terminal to continue.
- Records each submitted filename in `lenso_submitted.txt` next to the script, so you can stop and resume later without re-submitting images.

## Requirements

- macOS (the Chrome launch instructions below are macOS-specific; on Linux/Windows adjust the Chrome command accordingly)
- Google Chrome
- Python 3.9+
- [Playwright](https://playwright.dev/python/) (Python package only — no browser download needed, since it attaches to your existing Chrome)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Edit the constants at the top of `lenso_optout.py`:

```python
FIRST_NAME = "Jane"
LAST_NAME = "Doe"
EMAIL = "jane.doe9@gmail.com"
DESCRIPTION = "..."   # why you want the images removed; at least 20 characters
IMAGE_DIR = ...       # folder containing the images to submit
```

## Usage

1. Fully quit Chrome (**Cmd+Q**), then relaunch it with remote debugging enabled:

   ```bash
   open -a "Google Chrome" --args --remote-debugging-port=9222
   ```

2. Run the script:

   ```bash
   python lenso_optout.py
   ```

3. For each image, the script fills the form in a Chrome tab and prompts you in the terminal:

   | Key     | Action                                                  |
   |---------|---------------------------------------------------------|
   | `Enter` | I clicked Submit — log this image and load the next one |
   | `s`     | Skip this image (not logged; it will be retried next run) |
   | `q`     | Quit                                                    |

### Options

| Flag          | Description                                              |
|---------------|----------------------------------------------------------|
| `--dir PATH`  | Folder of images to submit (overrides `IMAGE_DIR`)       |
| `--redo`      | Ignore `lenso_submitted.txt` and process every image again |

Supported image types: `.jpg`, `.jpeg`, `.png`, `.webp`.

## Notes

- The script deliberately never clicks Submit itself — the final step is always yours, in your own browser.
- It also never closes your Chrome; it only borrows a tab.
- If the script can't connect, make sure Chrome was **fully quit** before relaunching with the debugging flag — an already-running Chrome ignores the flag.
- `lenso_submitted.txt` is your personal submission log and is git-ignored.
