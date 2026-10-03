# Upload and present this project on GitHub

1. Create a **public repository** named `retail-demand-forecasting-sop` on GitHub. Leave GitHub's README box unticked because this folder already has one.
2. Open Terminal and move into the unzipped `retail-forecasting` folder. Confirm you can see `README.md`, `src`, `docs` and `results`.
3. Run the following, replacing `YOUR_USERNAME` with your GitHub username:

```bash
git init
git add README.md requirements.txt .gitignore src docs tests results
git commit -m "Add verified retail forecasting and S&OP portfolio project"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/retail-demand-forecasting-sop.git
git push -u origin main
```

If Git asks you to sign in, use the browser authentication flow, GitHub CLI, or your approved credential manager. Do not paste a password or token into the repository. `data/raw/` and `.venv/` are excluded by `.gitignore`. Check `git status` and GitHub's file list before sharing. Avoid uploading your personal CV or employer data.

Pin the repository to your profile. In the repository description, use: **“Item-store demand forecasting on public M5 retail data with leakage-safe backtests, replenishment scenarios, exception analysis and an S&OP decision dashboard.”** The README links the dashboard and decision brief. GitHub does not reliably host local interactive HTML as a clickable live app; reviewers can download `results/planning_dashboard.html` and open it locally. Alternatively, publish the static HTML separately if you want a public live demo.

For an interview, walk through one item-store exception, explain the choice of forecast horizon, show the capacity slider, and acknowledge which inputs were simulated. State plainly that the baseline beat the model at weekly/28-day volume planning.

