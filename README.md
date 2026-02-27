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

5. **Limits on Vercel**
   - You can request up to **1000 leads**. The function runs up to **~13 minutes** (800s on Pro/Enterprise; `maxDuration` in `vercel.json`) for best results, then returns all leads collected in that time. On Hobby the max is 300s (~5 min). Set **Function max duration** to 800 in Vercel: Project → Settings → Functions (Pro plan).
6. **25-minute runs (self-hosted only)**  
   - Vercel cannot run longer than 800s. For **~25-minute runs** (best results), self-host the app (e.g. Railway, Render) and set **`MAX_RUN_SECONDS=1500`** in the environment; the job will run up to 25 min and return all leads collected. Or run the CLI locally with no time limit.

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
