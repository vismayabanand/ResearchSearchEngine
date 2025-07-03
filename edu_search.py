# edu_searcher.py

import os
import lucene
from java.nio.file import Paths
from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.index import DirectoryReader
from org.apache.lucene.queryparser.classic import QueryParser
from org.apache.lucene.search import IndexSearcher
from org.apache.lucene.store import SimpleFSDirectory

def search_index(index_dir: str, query_str: str, top_k: int = 10):
    """
    Run a Lucene search against the given index folder, return up to top_k hits.
    Returns a Python list of dicts: [{ "score": float, "title": str, "path": str }, …].
    """
    # 1) Initialize Lucene VM if not already done
    #    If you call this multiple times in the same process, you only need to init once.
    if not lucene.getVMEnv().isCurrentThreadAttached():
        lucene.initVM(vmargs=['-Djava.awt.headless=true'])

    # 2) Open the existing index on disk
    directory = SimpleFSDirectory(Paths.get(os.path.abspath(index_dir)))
    reader = DirectoryReader.open(directory)
    searcher = IndexSearcher(reader)
    analyzer = StandardAnalyzer()

    # 3) Parse the query against the "body" field
    parser = QueryParser("body", analyzer)
    query = parser.parse(query_str)

    # 4) Run the search (top_k hits)
    top_docs = searcher.search(query, top_k)
    hits = top_docs.scoreDocs  # an array of ScoreDoc objects

    # 5) Build a Python list of dicts from hits
    results = []
    for hit in hits:
        doc = searcher.doc(hit.doc)
        title = doc.get("title") or ""
        path = doc.get("path") or ""
        score = float(hit.score)
        results.append({
            "score": score,
            "title": title,
            "path": path
        })

    reader.close()
    return results


if __name__ == "__main__":
    # Keep backward compatibility if someone calls this directly:
    import sys
    if len(sys.argv) != 3:
        print('Usage: python edu_searcher.py <index_dir> "<query_string>"')
        sys.exit(1)

    index_dir = sys.argv[1]
    query_str = sys.argv[2]

    # Validate index_dir
    if not os.path.isdir(index_dir):
        print(f"Error: index_dir \"{index_dir}\" does not exist or is not a directory.")
        sys.exit(1)

    hits = search_index(index_dir, query_str, top_k=10)
    # Print results on separate lines
    if not hits:
        print(f"No results found for \"{query_str}\".")
    else:
        for r in hits:
            print(f"Score: {r['score']:.2f}")
            print(f"Title: {r['title']}")
            print(f"Path:  {r['path']}")
            print("-" * 40)
