// LuceneSearch.java

import org.apache.lucene.analysis.standard.StandardAnalyzer;
import org.apache.lucene.document.Document;
import org.apache.lucene.index.DirectoryReader;
import org.apache.lucene.queryparser.classic.QueryParser;
import org.apache.lucene.search.IndexSearcher;
import org.apache.lucene.search.Query;
import org.apache.lucene.search.ScoreDoc;
import org.apache.lucene.search.TopDocs;
import org.apache.lucene.store.FSDirectory;

import java.nio.file.Paths;
import java.io.IOException;

import org.json.simple.JSONArray;
import org.json.simple.JSONObject;

// A simple Java class that takes two arguments: <topK> <query string>
// and prints JSON to stdout.

public class LuceneSearch {
    public static void main(String[] args) {
        if (args.length < 2) {
            System.err.println("{\"error\":\"Usage: java -cp .;dependencies/* LuceneSearch <topK> <query>\"}");
            System.exit(1);
        }

        int topK = Integer.parseInt(args[0]);
        // Build the query from args[1..]
        StringBuilder sb = new StringBuilder();
        for (int i = 1; i < args.length; i++) {
            sb.append(args[i]);
            if (i < args.length - 1) sb.append(" ");
        }
        String queryString = sb.toString();

        try {
            // 1) Open the edu_lucene_index (adjust path if needed)
            //    We assume the current working directory is the project root,
            //    so "edu_lucene_index" is a sibling to this .java file.
            FSDirectory directory = FSDirectory.open(Paths.get("edu_lucene_index"));
            DirectoryReader reader = DirectoryReader.open(directory);
            IndexSearcher searcher = new IndexSearcher(reader);

            // 2) Use StandardAnalyzer and parse the query on field "body"
            StandardAnalyzer analyzer = new StandardAnalyzer();
            QueryParser parser = new QueryParser("body", analyzer);
            Query query = parser.parse(queryString);

            // 3) Search top K
            TopDocs topDocs = searcher.search(query, topK);
            ScoreDoc[] hits = topDocs.scoreDocs;

            // 4) Build JSON output
            JSONObject output = new JSONObject();
            output.put("totalHits", topDocs.totalHits.value);

            JSONArray resultsArray = new JSONArray();
            for (ScoreDoc sd : hits) {
                Document doc = reader.document(sd.doc);
                JSONObject obj = new JSONObject();
                obj.put("score", sd.score);
                obj.put("title", doc.get("title"));
                obj.put("path", doc.get("path"));
                resultsArray.add(obj);
            }
            output.put("results", resultsArray);

            // 5) Print to stdout
            System.out.println(output.toJSONString());

            reader.close();
        } catch (Exception e) {
            // On error, print a JSON with error message
            JSONObject err = new JSONObject();
            err.put("error", e.toString());
            try {
                System.out.println(err.toJSONString());
            } catch (Exception ignore) {}
            System.exit(2);
        }
    }
}
