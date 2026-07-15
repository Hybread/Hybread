# Setup

1. Create a **public** GitHub repository whose name exactly matches your GitHub username.
2. Copy every file and folder from this starter into that repository.
3. Commit and push to the default branch.
4. Open **Actions → Update profile telemetry → Run workflow**.
5. Return to your GitHub profile. The repository's `README.md` becomes your profile front page.

No personal access token is required. The workflow uses GitHub's built-in `GITHUB_TOKEN` and grants only `contents: write`, which is needed to commit the regenerated SVG files.

## Local preview

```bash
python today.py --preview
```

The generated cards are written to:

```text
assets/profile-dark.svg
assets/profile-light.svg
```

## Personalization points

Edit the `PROFILE` dictionary near the top of `today.py` to change:

- headline, identity and focus areas
- technology stack
- selected CTF achievements
- challenge/result/language counts
- graduation date

The workflow automatically uses the repository owner's username, so you do not need to hard-code your GitHub username.

## Privacy choice

This starter intentionally excludes your home address, phone number, referees and direct email address. A GitHub profile is public; add those details only when you deliberately want them indexed and scraped.
