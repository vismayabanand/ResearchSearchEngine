# edu_indexer.py

import os
import sys
import lucene
from java.io import File
from java.nio.file import Paths
from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.document import Document, Field, StringField, TextField
from org.apache.lucene.index import IndexWriter, IndexWriterConfig
from org.apache.lucene.store import SimpleFSDirectory
from bs4 import BeautifulSoup

"""
Usage:
    python edu_indexer.py <html_dir> <index_dir>

    <html_dir> : path to the folder containing all your .edu HTML files
    <index_dir>: path to an (empty or non-existent) directory where the Lucene index will be created.

Example:
    python edu_indexer.py ./data/html_pages ./data/edu_lucene_index
"""

def extract_title_and_body(html_content: bytes) -> (str, str):
    """
    Given raw bytes of an HTML file, return (title_text, body_text).
    - title_text: whatever was inside <title>…</title>, or "" if none.
    - body_text: all visible text after removing <script> and <style> tags.
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # 1) Extract the <title>
    title_tag = soup.find("title")
    title_text = title_tag.get_text(strip=True) if title_tag else ""

    # 2) Remove <script> and <style> entirely
    for script in soup(["script", "style"]):
        script.decompose()

    # 3) Grab everything left as plain text (concatenate with spaces)
    body_text = soup.get_text(separator=" ", strip=True)
    return title_text, body_text


def main(html_dir: str, index_dir: str):
    # 1) Initialize the Lucene VM (headless, no AWT)
    lucene.initVM(vmargs=['-Djava.awt.headless=true'])

    # 2) Open or create the index directory on disk
    index_path = SimpleFSDirectory(Paths.get(os.path.abspath(index_dir)))

    # 3) Choose a StandardAnalyzer and set up IndexWriter in CREATE mode
    analyzer = StandardAnalyzer()
    config = IndexWriterConfig(analyzer)
    config.setOpenMode(IndexWriterConfig.OpenMode.CREATE)  # overwrite any existing index
    writer = IndexWriter(index_path, config)

    # 4) Walk through all .html files under html_dir
    doc_count = 0
    for root, _, files in os.walk(html_dir):
        for filename in files:
            if not filename.lower().endswith(".html"):
                continue

            file_path = os.path.join(root, filename)
            try:
                with open(file_path, "rb") as f:
                    raw = f.read()
            except Exception as e:
                print(f"⚠️  Could not read {file_path}: {e}")
                continue

            # 5) Extract title & visible body
            title_text, body_text = extract_title_and_body(raw)

            # 6) Build a Lucene Document
            doc = Document()
            # 6a) “path” field (stored, untokenized)
            doc.add(StringField("path", file_path, Field.Store.YES))
            # 6b) “title” field (tokenized + stored)
            doc.add(TextField("title", title_text, Field.Store.YES))
            # 6c) “body” field (tokenized, not stored)
            doc.add(TextField("body", body_text, Field.Store.NO))

            # 7) Add the document to the index
            writer.addDocument(doc)
            doc_count += 1
            if doc_count % 100 == 0:
                print(f"Indexed {doc_count} documents so far…")

    # 8) Commit & close
    writer.close()
    print(f"\n Finished indexing. Total HTML files indexed: {doc_count}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python edu_indexer.py <html_dir> <index_dir>")
        sys.exit(1)

    html_dir = sys.argv[1]
    index_dir = sys.argv[2]

    if not os.path.isdir(html_dir):
        print(f"Error: {html_dir} is not a directory or does not exist.")
        sys.exit(1)

    os.makedirs(index_dir, exist_ok=True)
    main(html_dir, index_dir)
