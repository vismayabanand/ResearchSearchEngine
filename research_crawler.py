# research_crawler.py
import hashlib
import json
import requests
import time
import os
from bs4 import BeautifulSoup
from collections import deque
from urllib.parse import urlparse, urlunparse, urljoin


class ResearchPaperCrawler:
    def __init__(self, seed_urls, max_depth=4, time_limit=50000,
                 visited_file="./visited_urls.json", batch_dir="./data/batches"):
        self.existing_visited = self.load_json(visited_file)
        self.current_session_visited = set()
        self.scraped_data = {}
        self.url_queue = deque([(url, 0) for url in seed_urls])
        self.visited_file = visited_file
        self.batch_dir = batch_dir
        self.max_depth = max_depth
        self.time_limit = time_limit
        self.start_time = time.time()

        os.makedirs(self.batch_dir, exist_ok=True)

    @staticmethod
    def load_json(file):
        try:
            with open(file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_json(self, data, file):
        with open(file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    @staticmethod
    def generate_url_hash(url):
        return hashlib.sha256(url.encode('utf-8')).hexdigest()

    @staticmethod
    def normalize_url(url):
        parsed_url = urlparse(url)
        return urlunparse(parsed_url._replace(fragment='', query=''))

    @staticmethod
    def extract_text_content(soup):
        paragraphs = soup.find_all('p')
        return "\n".join([p.get_text(strip=True) for p in paragraphs])

    @staticmethod
    def extract_links(soup, base_url):
        links = set()
        for tag in soup.find_all('a', href=True):
            href = tag['href']
            full_url = urljoin(base_url, href)
            if full_url.startswith("http") and ".edu" in urlparse(full_url).netloc:
                links.add(full_url)
        return links

    def crawl(self, url, depth):
        normalized_url = self.normalize_url(url)
        url_hash = self.generate_url_hash(normalized_url)

        if url_hash in self.existing_visited or url_hash in self.current_session_visited:
            return

        # Skip common non-HTML file extensions
        path = urlparse(normalized_url).path.lower()
        non_html_exts = (".pdf", ".docx", ".pptx", ".zip", ".jpg", ".jpeg", ".png", ".gif", ".svg")
        if any(path.endswith(ext) for ext in non_html_exts):
            print(f"  → Skipping non-HTML URL (by extension): {normalized_url}")
            return

        print(f"Crawling: {normalized_url} (Depth: {depth})")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36"
        }

        try:
            response = requests.get(normalized_url, headers=headers, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Error fetching {normalized_url}: {e}")
            return

        content_type = response.headers.get("Content-Type", "").lower()
        if "text/html" not in content_type:
            print(f"  → Skipping non-HTML content (Content-Type: {content_type}): {normalized_url}")
            return

        soup = BeautifulSoup(response.content, 'html.parser')
        text_content = self.extract_text_content(soup)

        self.current_session_visited.add(url_hash)
        self.scraped_data[url_hash] = {
            "url": normalized_url,
            "content": text_content
        }
        print(f"  → Scraped {len(text_content)} chars from {normalized_url}")

        if depth >= self.max_depth:
            return

        new_links = self.extract_links(soup, normalized_url)
        for new_url in new_links:
            new_normalized = self.normalize_url(new_url)
            new_hash = self.generate_url_hash(new_normalized)
            if new_hash not in self.existing_visited and new_hash not in self.current_session_visited:
                self.url_queue.append((new_normalized, depth + 1))

    def start_crawl(self):
        batch_threshold_bytes = 10 * 1024 * 1024  # 10 MB in bytes
        batch_data = {}
        batch_index = 1
        current_batch_bytes = 0

        os.makedirs(self.batch_dir, exist_ok=True)
        print(f"Batch directory is: {os.path.abspath(self.batch_dir)}")

        def write_batch():
            nonlocal batch_data, batch_index, current_batch_bytes
            if not batch_data:
                return
            batch_filename = os.path.join(self.batch_dir, f"edu_batch_{batch_index}.json")
            with open(batch_filename, "w", encoding="utf-8") as f:
                json.dump(batch_data, f, ensure_ascii=False, indent=2)
            size_mb = os.path.getsize(batch_filename) / (1024 * 1024)
            print(f"Wrote batch #{batch_index} ({size_mb:.2f} MB, {len(batch_data)} pages)")
            batch_data.clear()
            batch_index += 1
            current_batch_bytes = 0

        while self.url_queue:
            if time.time() - self.start_time > self.time_limit:
                print(" Time limit reached. Stopping crawl.")
                break

            current_url, current_depth = self.url_queue.popleft()
            self.crawl(current_url, current_depth)

            url_hash = self.generate_url_hash(self.normalize_url(current_url))
            if url_hash in self.scraped_data and url_hash not in batch_data:
                content = self.scraped_data[url_hash]
                content_str = json.dumps(content)
                size = len(content_str.encode("utf-8"))

                # If adding this page would exceed 10 MB, write out the current batch first
                if current_batch_bytes + size >= batch_threshold_bytes:
                    write_batch()

                # Add the new page to batch_data
                batch_data[url_hash] = content
                current_batch_bytes += size
                print(f"  → Added {url_hash[:8]}… (size {size} bytes), running total: {current_batch_bytes} bytes")

                # If this page alone crosses 10 MB, write it immediately
                if current_batch_bytes >= batch_threshold_bytes:
                    write_batch()

        # Final write for any remaining pages
        print(f"Final batch_data has {len(batch_data)} entries; total_bytes={current_batch_bytes}")
        write_batch()

        # Update visited_urls.json
        self.existing_visited.update({
            k: self.scraped_data[k]["url"]
            for k in self.current_session_visited
            if k not in self.existing_visited
        })
        self.save_json(self.existing_visited, self.visited_file)

        total_size = sum(
            os.path.getsize(os.path.join(self.batch_dir, f))
            for f in os.listdir(self.batch_dir)
            if f.endswith(".json")
        )

        print(f"\nCompleted crawl. {len(self.current_session_visited)} new pages saved.")
        print(f"Batches saved in: {self.batch_dir}")
        print(f"Total data collected: {round(total_size / (1024 * 1024), 2)} MB")
        print(f"Visited log: {self.visited_file}")
