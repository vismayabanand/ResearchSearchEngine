# Academic Research Search Engine  
*A focused .edu-domain crawler, Lucene indexer, and Flask search UI*

> CS 172 – Group 29 • UCR  
> Video demo: `https://drive.google.com/file/d/1jjd5EiegDYTAN0jiMLAWoNIiRuMdG036/view`

---

## 1 . Project Overview
This repository contains a two–stage pipeline that turns raw university research pages into a mini-search-engine:

1. **Focused Web Crawler** – collects HTML from `.edu` research sites using breadth-first search, depth/page limits, duplicate filtering, and domain gating. :contentReference[oaicite:0]{index=0}  
2. **PyLucene Indexer** – tokenises + indexes the pages (title boosted × 2) and stores a BM25-optimised inverted index. :contentReference[oaicite:1]{index=1}  
3. **Flask Web App** – provides a simple search box, ranks results with BM25, and shows custom, context-aware snippets. :contentReference[oaicite:2]{index=2}  

Data flow:  

`[HTML files] → edu_indexer.py → Lucene index → app.py → Browser`

---

## 2 . Key Features
### 2.1  Web Crawler
- **BFS traversal** with `collections.deque` (FIFO).  
- **Depth / page caps** (`max_depth`, `max_pages`).  
- **`.edu` filter** via `urlparse`, skipping external domains.  
- **Duplicate prevention** using SHA-256 of normalised URLs.  
- **Graceful error handling** for 4xx/5xx & time-outs.  
- **Raw HTML storage** in `data/html_pages/<sha256>.html`. :contentReference[oaicite:3]{index=3}  

### 2.2  Indexer
- **PyLucene** backend; StandardAnalyzer on *body*, boosted *title*.  
- **BM25 ranking** out of the box.  
- **Custom snippet extraction**: first sentence containing the query term. :contentReference[oaicite:4]{index=4}  

### 2.3  Web Interface
- **Instant search** over title + body.  
- **Top-N results (default 10)** with title, URL, and snippet.  
- Lightweight **Flask** app; no JS build step required. :contentReference[oaicite:5]{index=5}  

---

## 3 . Directory Layout
├── crawler/ # Part A
│ ├── crawler.py
│ ├── research_crawler.py
│ ├── crawler.bat / .sh
│ └── seed.txt
├── indexer/ # Part B
│ ├── edu_indexer.py
│ ├── indexer.sh
│ └── requirements.txt
├── app/ # Flask UI
│ ├── app.py
│ └── templates/index.html
├── data/
│ └── html_pages/ # raw crawl output
└── index/ # Lucene index (generated)
---

## 4 . Quick-Start Guide

### 4.1  Prerequisites
| Tool / Lib           | Version tested |
|----------------------|----------------|
| Python               | 3.10 +         |
| PyLucene             | 9.x            |
| Flask (+ Jinja2)     | 3.x            |
| BeautifulSoup4       | 4.x            |
| requests, tqdm, etc. | see `requirements.txt` |

> **Tip**: PyLucene on macOS/Linux often needs `JAVA_HOME` set and `pip install pylucene-*.whl`.

### 4.2  Crawl (optional – skip if you have HTML already)

# Windows
crawler.bat seed.txt 4 50000
# macOS / Linux
./crawler.sh seed.txt 4 50000

### 4.3  Build the index

chmod +x indexer/indexer.sh
./indexer/indexer.sh data/html_pages

### 4.4 Launch the search UI

cd app
python3 app.py
# open http://127.0.0.1:5000 in your browser

### 5 . Usage Examples

→ “quantum computing lab”
   • “Stanford Quantum Initiative” — stanford.edu/…
     …We present a scalable architecture for…
→ “machine learning in agriculture”
   • “SmartFarm Research Group” — ucr.edu/…
     …Our BM25-ranked study shows…