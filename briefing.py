import os
import time
import feedparser
import google.generativeai as genai
from datetime import datetime, timezone
from urllib.parse import quote

# --- Config ---
COMPANIES = [
    "Microsoft", "AWS Amazon Web Services", "Google Cloud", "Oracle",
    "IBM", "Salesforce", "SAP", "ServiceNow", "Workday",
    "Nvidia", "Cisco", "Dell Technologies", "Adobe"
]

# Get the Gemini API key from GitHub's secret storage
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-2.5-flash")

def fetch_news(company):
    """Fetch recent headlines for a company from Google News RSS."""
    query = quote(f"{company} product OR launch OR release OR feature when:1d")
    url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(url)
    items = []
    for entry in feed.entries[:5]:
        items.append({
            "title": entry.title,
            "link": entry.link,
            "published": entry.get("published", "")
        })
    return items

def summarize(company, headlines):
    """Ask Gemini to summarize a company's news."""
    if not headlines:
        return "No major updates in the last 24 hours."
    headline_text = "\n".join([f"- {h['title']}" for h in headlines])
    prompt = f"""You are summarizing tech news for a busy executive.

Company: {company}

Recent headlines from the last 24 hours:
{headline_text}

In 2-3 concise sentences, summarize what's actually new and noteworthy about {company}'s products, launches, or announcements. Skip stock-price news. If nothing notable, say "No major product updates." Be factual — only summarize what's in the headlines, don't invent details."""
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"(Summary unavailable: {e})"

def build_html(briefings):
    """Generate the HTML page."""
    today = datetime.now(timezone.utc).strftime("%A, %B %d, %Y")
    cards = ""
    for company, summary, headlines in briefings:
        links = "".join([
            f'<li><a href="{h["link"]}" target="_blank">{h["title"]}</a></li>'
            for h in headlines[:3]
        ])
        cards += f"""
        <div class="card">
          <h2>{company}</h2>
          <p class="summary">{summary}</p>
          {f'<details><summary>Sources ({len(headlines)})</summary><ul>{links}</ul></details>' if headlines else ''}
        </div>
        """
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tech News Briefing — {today}</title>
<style>
  body {{ font-family: -apple-system, system-ui, sans-serif; max-width: 900px; margin: 0 auto; padding: 24px; background: #f6f8fb; color: #0a1628; line-height: 1.55; }}
  header {{ background: linear-gradient(135deg, #0a1628, #1e6091); color: white; padding: 32px; border-radius: 16px; margin-bottom: 24px; }}
  header h1 {{ margin: 0 0 8px; font-size: 26px; }}
  header p {{ margin: 0; opacity: .85; font-size: 14px; }}
  .card {{ background: white; border: 1px solid #e3eaf3; border-radius: 14px; padding: 20px 24px; margin-bottom: 14px; box-shadow: 0 1px 3px rgba(0,0,0,.04); }}
  .card h2 {{ margin: 0 0 8px; font-size: 18px; color: #1e3a5f; }}
  .summary {{ margin: 0 0 12px; }}
  details {{ font-size: 13px; color: #5a6b82; }}
  details ul {{ margin: 8px 0 0; padding-left: 20px; }}
  details a {{ color: #1e6091; text-decoration: none; }}
  details a:hover {{ text-decoration: underline; }}
  footer {{ text-align: center; color: #5a6b82; font-size: 12px; padding: 24px; }}
</style>
</head>
<body>
  <header>
    <h1>📰 Tech News Briefing</h1>
    <p>{today} · 13 companies · auto-summarized by Gemini</p>
  </header>
  {cards}
  <footer>Auto-updated daily at 07:00 UTC by GitHub Actions. Sources: Google News RSS.</footer>
</body>
</html>"""
    return html

def main():
    briefings = []
    for company in COMPANIES:
        print(f"Fetching {company}...")
        headlines = fetch_news(company)
        summary = summarize(company, headlines)
        briefings.append((company, summary, headlines))
        time.sleep(6)
    html = build_html(briefings)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Done. index.html written.")

if __name__ == "__main__":
    main()
