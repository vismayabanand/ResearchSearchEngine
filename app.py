# app.py

import os
import subprocess
import json
from flask import Flask, request, render_template_string, send_from_directory
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

# ─── CONFIG: Adjust these paths if your folder structure differs ────────────────

# 1) This file’s folder (where LuceneSearch.class lives, alongside dependencies/)
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

# 2) Folder where your Lucene JARs live (relative to PROJECT_ROOT)
DEPENDENCIES_DIR = os.path.join(PROJECT_ROOT, "dependencies")

# 3) Name of the Java class (LuceneSearch.class) to run
LUCENE_CLASS = "LuceneSearch"

# 4) Java classpath string: “PROJECT_ROOT;dependencies/*” on Windows
#    os.pathsep is ";" on Windows, ":" on Unix.
JAVA_CLASSPATH = os.pathsep.join([
    PROJECT_ROOT,
    os.path.join(DEPENDENCIES_DIR, "*")
])

# 5) Folder where your raw HTML pages (the ones you indexed) live:
HTML_PAGES_DIR = os.path.join(PROJECT_ROOT, "data", "html_pages")

# ────────────────────────────────────────────────────────────────────────────────

HTML_TEMPLATE = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Search Engine</title>
    <style>
      body {
        font-family: Arial, sans-serif;
        margin: 40px;
        background-color: #f0f2f5; /* light grey-blue background */
      }

      h1 {
        color: #2c3e50; /* dark blue-gray */
        text-align: center;
        margin-bottom: 30px;
      }

      .search-box {
        text-align: center;
        margin-bottom: 20px;
      }

      input[type="text"], input[type="number"] {
        width: 300px;
        padding: 8px;
        font-size: 1em;
        margin-right: 10px;
        border: 1px solid #ccc;
        border-radius: 4px;
      }

      button {
        padding: 8px 12px;
        font-size: 1em;
        background-color: #007bff; /* bootstrap-primary blue */
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
      }
      button:hover {
        background-color: #0056b3; /* darker blue on hover */
      }

      .result {
        margin-bottom: 24px;
        background-color: white;
        padding: 15px;
        border-radius: 6px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
      }

      .title {
        font-weight: bold;
        font-size: 1.2em;
        color: #2c3e50; /* dark blue-gray */
        margin-bottom: 6px;
      }

      .path a {
        font-size: 0.9em;
        color: #007bff;
        text-decoration: none;
      }
      .path a:hover {
        text-decoration: underline;
      }

      .score {
        font-size: 0.9em;
        color: #007bff; /* same blue as links */
        margin-bottom: 6px;
      }

      .snippet {
        font-size: 0.9em;
        color: #555;
        margin-top: 8px;
      }

      hr {
        border: none;
        border-top: 1px solid #ddd;
        margin: 24px 0;
      }

      .error {
        color: #c0392b; /* dark red */
        text-align: center;
        margin-bottom: 20px;
      }
    </style>
  </head>
  <body>
    <h1>Search Engine </h1>

    <form method="POST" action="/" class="search-box">
      <input
        type="text"
        name="query"
        placeholder="Enter query…"
        required
        value="{{ request.form.get('query', '') }}"
      />
      <input
        type="number"
        name="top_k"
        min="1"
        max="50"
        value="{{ request.form.get('top_k', 10) }}"
      />
      <button type="submit">Search</button>
    </form>

    {% if error %}
      <div class="error">{{ error }}</div>
    {% endif %}

    {% if results %}
      <p style="text-align:center; color: #555;">
        Showing top {{ results|length }} hits for “<em>{{ query }}</em>”.
      </p>
      {% for hit in results %}
        <div class="result">
          <div class="score">Score: {{ "%.2f"|format(hit["score"]) }}</div>
          <div class="title">{{ hit["title"] or "(no title)" }}</div>
          <div class="path">
            <a href="/pages/{{ hit["basename"] }}" target="_blank">
              {{ hit["basename"] }}
            </a>
          </div>
          <!-- Extra‐Credit Snippet -->
          {% if hit["snippet"] %}
            <div class="snippet">…{{ hit["snippet"] }}…</div>
          {% endif %}
        </div>
        <hr/>
      {% endfor %}
    {% elif request.method == 'POST' %}
      <p style="text-align:center; color: #555;">
        No results found for “<em>{{ query }}</em>”.
      </p>
    {% endif %}
  </body>
</html>
"""

def extract_snippet_from_html(basename: str, query: str, window: int = 150) -> str:
    """
    Given the HTML filename (basename) and the original query, return a short
    snippet from the visible text that includes the first occurrence of 'query'.
    If the query string is not found, returns the first ~100 characters of text.
    
    'window' is the number of characters to show before/after the match.
    """
    html_path = os.path.join(HTML_PAGES_DIR, basename)
    if not os.path.isfile(html_path):
        return ""

    try:
        with open(html_path, "rb") as f:
            content = f.read()
    except Exception:
        return ""

    # Parse the HTML and extract visible text
    soup = BeautifulSoup(content, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    full_text = soup.get_text(separator=" ", strip=True)

    # Normalize whitespace
    full_text = re.sub(r"\s+", " ", full_text)

    # Case-insensitive search for the first occurrence of the query
    idx = full_text.lower().find(query.lower())
    if idx != -1:
        # Show window chars before and after
        start = max(0, idx - window)
        end = min(len(full_text), idx + len(query) + window)
        snippet = full_text[start:end].strip()
        # If we cut off mid‐word, trim to nearest space
        snippet = snippet.lstrip().rstrip()
        return snippet

    # If query not found, just return first 100 characters
    return full_text[:200].rstrip()

def run_java_search(query: str, top_k: int = 10):
    """
    Runs:
      java -cp "<PROJECT_ROOT>;<DEPENDENCIES_DIR>\*" LuceneSearch <top_k> <query>
    Returns the parsed JSON object, or raises RuntimeError on error.
    """
    cmd = [
        "java",
        "-cp", JAVA_CLASSPATH,
        LUCENE_CLASS,
        str(top_k),
        query
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT
        )
        if proc.returncode != 0:
            raise RuntimeError(f"Java error: {proc.stderr.strip()}")

        return json.loads(proc.stdout.strip())

    except FileNotFoundError:
        raise RuntimeError("‘java’ executable not found. Make sure Java is on your PATH.")
    except json.JSONDecodeError:
        raise RuntimeError(f"Could not parse JSON from Java: {proc.stdout.strip()}")

@app.route("/", methods=["GET", "POST"])
def index():
    error = None
    results = []
    query = ""
    top_k = 10

    if request.method == "POST":
        query = request.form.get("query", "").strip()
        top_k = int(request.form.get("top_k", 10))

        if not query:
            error = "Please enter a non‐empty query."
        else:
            try:
                data = run_java_search(query, top_k)
                if "error" in data:
                    error = data["error"]
                else:
                    # Java’s JSON: { "totalHits": N, "results": [ {score, title, path}, … ] }
                    for obj in data.get("results", []):
                        full_path = obj.get("path", "")
                        basename = os.path.basename(full_path)
                        snippet = extract_snippet_from_html(basename, query, window=50)
                        results.append({
                            "score": obj.get("score", 0.0),
                            "title": obj.get("title", ""),
                            "path": full_path,
                            "basename": basename,
                            "snippet": snippet
                        })
            except RuntimeError as e:
                error = str(e)

    return render_template_string(
        HTML_TEMPLATE,
        error=error,
        results=results,
        query=query
    )

@app.route("/pages/<path:filename>")
def serve_page(filename):
    """
    Serve raw HTML pages from data/html_pages/<filename>.
    E.g.: /pages/3f58f741fb0c5c621ba4fdb7697a76d54e9e259ca01f85c7dd39a9c9f15058212.html
    """
    return send_from_directory(HTML_PAGES_DIR, filename)

if __name__ == "__main__":
    app.run(debug=True)
