# Lead Dataset Builder

Collect business leads by **city** and **niche** using the Google Places API. Outputs CSV with website, phone (+49), and one verified email per lead. Includes a web UI and supports deployment on **Vercel**.

## CSV columns

| Column            | Description                    |
|-------------------|--------------------------------|
| niche             | Business category              |
| city              | City name                      |
| business_name     | Name of the place              |
| phone             | Phone with +49 country code    |
| google_maps_url   | Link to Google Maps listing    |
| website_url       | Business website               |
| emails_found      | One verified email per lead    |

---

## Deploy on Vercel

1. **Push the project to GitHub** (ensure `config.json` is not committed; it’s in `.gitignore`).

2. **Import the repo in Vercel**
   - Go to [vercel.com](https://vercel.com) → Add New Project → Import your GitHub repo.
   - Framework Preset: **Flask** (or leave as detected).
   - Root directory: leave default.

3. **Set environment variable**
   - In the Vercel project: **Settings → Environment Variables**.
   - Add: **`GOOGLE_PLACES_API_KEY`** = your Google Places API key.
   - (Or **`GOOGLE_API_KEY`** — both are supported.)

4. **Deploy**
   - Click Deploy. Vercel will run `pip install -r requirements.txt` and deploy the Flask app.
   - After the first deploy: in **Project → Settings → Functions**, set **Max Duration** to **300** seconds so the lead-collect job can run up to 5 minutes.

5. **Limits on Vercel**
   - You can request up to **1000 leads**. On the **free/Hobby plan**, `maxDuration` is limited to **300 seconds (~5 minutes)**. The app runs up to ~5 min and returns all leads collected in that time. To use longer runs (up to 13 min), upgrade to Pro and set `maxDuration` to 300–800 in Project → Settings → Functions.
6. **Longer runs (self-hosted or Pro)**  
   - For **~25-minute runs**, self-host the app (e.g. Railway, Render) and set **`MAX_RUN_SECONDS=1500`** in the environment, or run the CLI locally with no time limit.

---

## Run locally (web UI)

1. **API key**  
   - Create `config.json` from `config.example.json` and set `google_api_key`,  
   - or set env: `GOOGLE_PLACES_API_KEY` or `GOOGLE_API_KEY`.

2. **Install and run**
   ```bash
   pip install -r requirements.txt
   python app.py
   ```
   Open **http://127.0.0.1:5000**. You can select multiple cities and niches and request up to 1000 leads per run. For a **~25-minute run** (best results), set **`MAX_RUN_SECONDS=1500`** in the environment before starting the app.

---

## Run CLI (no UI)

For large runs (e.g. 1000 leads) or automation:

```bash
# From project root; config.json or GOOGLE_PLACES_API_KEY must be set
python scrape_businesses.py --max-leads 1000 --clear-checkpoint
```

Output: `outputs/leads_de_bw.csv` (or path set with `--output`).

Options: `--config`, `--max-leads`, `--extract-emails`, `--sleep-api`, `--sleep-web`, `--output`, `--clear-checkpoint`, `-v`.

---

## Google API setup

1. Open [Google Cloud Console](https://console.cloud.google.com/apis/library).
2. Enable **Places API** for your project.
3. Create an API key (Credentials → Create credentials → API key).
4. Use that key in `config.json` or in the **GOOGLE_PLACES_API_KEY** (or **GOOGLE_API_KEY**) environment variable.

Do not commit your API key. Use env vars on Vercel and keep `config.json` out of git (it’s in `.gitignore`).
