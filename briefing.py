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

# Three tabs per company, each with its own search query and summarization style
TABS = [
    {
        "id": "products",
        "label": "Products",
        "icon": "🚀",
        "query_suffix": "product launch OR new feature OR release OR update",
        "prompt": "Summarize in 2-3 short sentences what new products, features, or releases {company} announced in the last 24 hours. Focus only on actual launches and product updates. If nothing notable, say 'No major product launches today.' Be factual — only summarize what's in the headlines."
    },
    {
        "id": "newsroom",
        "label": "Newsroom",
        "icon": "📣",
        "query_suffix": "announcement OR partnership OR acquisition OR earnings",
        "prompt": "Summarize in 2-3 short sentences the key company news for {company} from the last 24 hours — partnerships, acquisitions, leadership changes, earnings, major announcements. End with one short sentence on why this matters. If nothing notable, say 'No major company news today.'"
    },
    {
        "id": "analysis",
        "label": "Analysis & POV",
        "icon": "💡",
        "query_suffix": "analysis OR opinion OR review OR commentary",
        "prompt": "Summarize in 2-3 short sentences the key expert takes, analyst opinions, or notable points of view on {company}'s recent products and announcements from the last few days. Focus on what experts and journalists are saying — not just what {company} is saying about itself. If nothing notable, say 'No major analysis or expert commentary today.'"
    }
]

# --- Setup Gemini ---
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-2.5-flash")


def fetch_news(company, query_suffix):
    """Fetch recent headlines for a company from Google News RSS."""
    query = quote(f"{company} {query_suffix} when:2d")
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


def summarize(company, headlines, prompt_template):
    """Ask Gemini to summarize a company's news with the given prompt template."""
    if not headlines:
        return "No recent news found.", []

    headline_text = "\n".join([f"- {h['title']}" for h in headlines])
    prompt = f"""{prompt_template.format(company=company)}

Recent headlines:
{headline_text}

Keep your response to 2-3 short sentences. Be direct and factual. Do not invent details that aren't in the headlines."""

    for attempt in range(3):
        try:
            response = model.generate_content(prompt)
            return response.text.strip(), headlines
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                time.sleep(45)
                continue
            return f"(Summary unavailable today — try again tomorrow.)", headlines
    return "(Summary unavailable.)", headlines


def build_html(briefings, generated_at):
    """Generate the HTML page with three-tab structure per company."""
    today = generated_at.strftime("%A, %B %d, %Y")
    cards = ""

    for company, tabs_data in briefings:
        # Build the tab buttons
        tab_buttons = ""
        tab_panels = ""
        company_id = company.replace(" ", "-").lower()

        for i, tab in enumerate(TABS):
            active_class = "active" if i == 0 else ""
            summary, headlines = tabs_data[tab["id"]]

            tab_buttons += f"""
                <button class="tab-btn {active_class}" data-target="{company_id}-{tab['id']}">
                  <span class="tab-icon">{tab['icon']}</span>{tab['label']}
                </button>"""

            sources_html = ""
            if headlines:
                links = "".join([
                    f'<li><a href="{h["link"]}" target="_blank" rel="noopener">{h["title"]}</a></li>'
                    for h in headlines[:3]
                ])
                sources_html = f'<details class="sources"><summary>Sources ({len(headlines)})</summary><ul>{links}</ul></details>'

            tab_panels += f"""
                <div class="tab-panel {active_class}" id="{company_id}-{tab['id']}">
                  <p class="summary">{summary}</p>
                  {sources_html}
                </div>"""

        cards += f"""
        <article class="card" data-company="{company.lower()}">
          <header class="card-head">
            <h2>{company}</h2>
          </header>
          <nav class="tabs">
            {tab_buttons}
          </nav>
          <div class="tab-panels">
            {tab_panels}
          </div>
        </article>"""

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tech News Briefing — {today}</title>
<style>
  :root {{
    --ink:#0a1628;
    --ink-2:#1e3a5f;
    --bg:#f6f8fb;
    --surface:#ffffff;
    --line:#e3eaf3;
    --line-2:#cdd8e6;
    --muted:#5a6b82;
    --accent:#1e6091;
    --gold:#b8860b;
    --shadow-sm:0 1px 2px rgba(10,22,40,.04), 0 1px 3px rgba(10,22,40,.06);
    --shadow:0 4px 12px rgba(10,22,40,.06), 0 2px 4px rgba(10,22,40,.04);
    --t:180ms cubic-bezier(.4,0,.2,1);
  }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    margin: 0; padding: 0;
    background: var(--bg);
    color: var(--ink);
    line-height: 1.55;
    -webkit-font-smoothing: antialiased;
  }}
  .container {{ max-width: 1100px; margin: 0 auto; padding: 24px 18px; }}

  header.hero {{
    background: linear-gradient(135deg, var(--ink), var(--accent));
    color: white;
    padding: 32px 28px;
    border-radius: 18px;
    margin-bottom: 24px;
    box-shadow: var(--shadow);
    position: relative;
    overflow: hidden;
  }}
  header.hero::before {{
    content: "";
    position: absolute;
    top: -80px; right: -80px;
    width: 250px; height: 250px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(184,134,11,.25), transparent 70%);
  }}
  header.hero h1 {{ margin: 0 0 8px; font-size: 26px; letter-spacing: -.4px; position: relative; }}
  header.hero p {{ margin: 0; opacity: .88; font-size: 14px; position: relative; }}

  .filter-bar {{
    display: flex; gap: 8px; margin-bottom: 18px; flex-wrap: wrap;
    background: var(--surface);
    padding: 10px 14px;
    border-radius: 12px;
    border: 1px solid var(--line);
    box-shadow: var(--shadow-sm);
  }}
  .filter-bar input {{
    flex: 1; min-width: 180px;
    border: none; background: transparent;
    font-size: 14px; padding: 6px 4px;
    outline: none;
    color: var(--ink);
  }}
  .filter-bar input::placeholder {{ color: var(--muted); }}

  .grid {{
    display: grid;
    grid-template-columns: 1fr;
    gap: 14px;
  }}
  @media (min-width: 720px) {{ .grid {{ grid-template-columns: repeat(2, 1fr); }} }}

  .card {{
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 14px;
    box-shadow: var(--shadow-sm);
    overflow: hidden;
    transition: var(--t);
  }}
  .card:hover {{ box-shadow: var(--shadow); border-color: var(--line-2); }}

  .card-head {{
    padding: 16px 20px 0;
  }}
  .card-head h2 {{
    margin: 0;
    font-size: 17px;
    color: var(--ink);
    font-weight: 700;
    letter-spacing: -.2px;
  }}

  .tabs {{
    display: flex;
    gap: 4px;
    padding: 12px 20px 0;
    border-bottom: 1px solid var(--line);
  }}
  .tab-btn {{
    background: transparent;
    border: none;
    padding: 8px 12px;
    font-size: 12px;
    font-weight: 600;
    color: var(--muted);
    cursor: pointer;
    border-radius: 6px 6px 0 0;
    border-bottom: 2px solid transparent;
    transition: var(--t);
    display: inline-flex;
    align-items: center;
    gap: 5px;
    margin-bottom: -1px;
    font-family: inherit;
  }}
  .tab-btn:hover {{ color: var(--ink); background: var(--bg); }}
  .tab-btn.active {{
    color: var(--accent);
    border-bottom-color: var(--accent);
    background: var(--bg);
  }}
  .tab-icon {{ font-size: 13px; }}

  .tab-panels {{ padding: 16px 20px 18px; }}
  .tab-panel {{ display: none; }}
  .tab-panel.active {{ display: block; animation: fadeIn 200ms ease-out; }}
  @keyframes fadeIn {{
    from {{ opacity: 0; transform: translateY(2px); }}
    to {{ opacity: 1; transform: translateY(0); }}
  }}
  .summary {{
    margin: 0 0 10px;
    font-size: 14px;
    color: var(--ink-2);
  }}
  .sources {{
    font-size: 12px;
    color: var(--muted);
    margin-top: 8px;
  }}
  .sources summary {{
    cursor: pointer;
    color: var(--accent);
    font-weight: 600;
    user-select: none;
  }}
  .sources summary:hover {{ text-decoration: underline; }}
  .sources ul {{
    margin: 8px 0 0;
    padding-left: 20px;
  }}
  .sources li {{ margin-bottom: 4px; }}
  .sources a {{
    color: var(--ink-2);
    text-decoration: none;
  }}
  .sources a:hover {{ color: var(--accent); text-decoration: underline; }}

  footer {{
    text-align: center;
    color: var(--muted);
    font-size: 12px;
    padding: 30px 12px 20px;
  }}
  footer code {{
    background: var(--surface);
    padding: 2px 6px;
    border-radius: 4px;
    border: 1px solid var(--line);
    font-size: 11px;
  }}
</style>
</head>
<body>
  <div class="container">
    <header class="hero">
      <h1>📰 Tech News Briefing</h1>
      <p>{today} · 13 companies · auto-summarized by Gemini · 3 lenses per company</p>
    </header>

    <div class="filter-bar">
      <span style="font-size:14px">🔎</span>
      <input type="text" id="search" placeholder="Filter companies (e.g. Microsoft, AWS)…" />
    </div>

    <main class="grid" id="grid">
      {cards}
    </main>

    <footer>
      Auto-updated daily by GitHub Actions · Sources: Google News RSS · Generated <code>{generated_at.strftime('%Y-%m-%d %H:%M UTC')}</code>
    </footer>
  </div>

<script>
  // Tab switching — scoped per card
  document.querySelectorAll('.card').forEach(card => {{
    const buttons = card.querySelectorAll('.tab-btn');
    const panels = card.querySelectorAll('.tab-panel');
    buttons.forEach(btn => {{
      btn.addEventListener('click', () => {{
        const target = btn.dataset.target;
        buttons.forEach(b => b.classList.remove('active'));
        panels.forEach(p => p.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById(target).classList.add('active');
      }});
    }});
  }});

  // Live search filter
  const searchInput = document.getElementById('search');
  searchInput.addEventListener('input', e => {{
    const term = e.target.value.toLowerCase().trim();
    document.querySelectorAll('.card').forEach(card => {{
      const company = card.dataset.company;
      card.style.display = (!term || company.includes(term)) ? '' : 'none';
    }});
  }});
</script>
</body>
</html>"""
    return html


def main():
    generated_at = datetime.now(timezone.utc)
    briefings = []

    for company in COMPANIES:
        print(f"\n=== {company} ===")
        tabs_data = {}

        for tab in TABS:
            print(f"  Tab: {tab['label']}...")
            headlines = fetch_news(company, tab["query_suffix"])
            summary, sources = summarize(company, headlines, tab["prompt"])
            tabs_data[tab["id"]] = (summary, sources)
            time.sleep(15)  # respect Gemini's free-tier rate limit (5/min)

        briefings.append((company, tabs_data))

    html = build_html(briefings, generated_at)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("\n✓ Done. index.html written.")


if __name__ == "__main__":
    main()
