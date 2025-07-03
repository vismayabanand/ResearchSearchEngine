# crawler.py
import sys
from research_crawler import ResearchPaperCrawler

# Validate argument count
if len(sys.argv) != 4:
    print("Usage: python crawler.py <seed-urls-file> <max-depth> <time-limit-in-seconds>")
    sys.exit(1)

# Read command-line arguments
seed_file = sys.argv[1]
max_depth = int(sys.argv[2])
time_limit = int(sys.argv[3])

# Load seed URLs from the given file
try:
    with open(seed_file, 'r', encoding='utf-8') as f:
        seed_urls = [line.strip() for line in f if line.strip()]
except Exception as e:
    print(f"Error reading seed file '{seed_file}': {e}")
    sys.exit(1)

# Initialize and run the crawler
crawler = ResearchPaperCrawler(
    seed_urls=seed_urls,
    max_depth=max_depth,
    time_limit=time_limit,
    visited_file="visited_urls.json",
    batch_dir="./data/batches"
)

crawler.start_crawl()
