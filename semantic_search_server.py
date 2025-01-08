from flask import Flask, request, jsonify
from flask_cors import CORS
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.utils import embedding_functions
import numpy as np
from bs4 import BeautifulSoup
import nltk
from nltk.tokenize import sent_tokenize
import json
from datetime import datetime
import re
import hashlib

# Download required NLTK data
nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)

app = Flask(__name__)
CORS(app)

# Initialize SBERT model and ChromaDB
model_name = 'all-MiniLM-L6-v2'
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=model_name)
max_sequence_length = 256 

# Initialize ChromaDB
chroma_client = chromadb.PersistentClient(path="./chroma_db")
try:
    collection = chroma_client.get_collection("webpage_chunks")
except:
    collection = chroma_client.create_collection(
        name="webpage_chunks",
        embedding_function=sentence_transformer_ef
    )

def clean_text(text):
    """Clean and normalize text content."""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    # Remove special characters but keep punctuation
    text = re.sub(r'[^\w\s.,!?-]', '', text)
    return text

def extract_main_content(html_content, main_text):
    """Extract main content using both HTML and pre-extracted text."""
    content_parts = []
    
    # First, try to use the pre-extracted main text
    if main_text and main_text.strip():
        print("Using pre-extracted main text")
        content_parts.append(clean_text(main_text))
    
    # Then try to extract from HTML as backup
    if html_content and html_content.strip():
        print("Processing HTML content")
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove unwanted elements
            for element in soup.find_all(['script', 'style', 'nav', 'footer', 'iframe', 'header']):
                element.decompose()
            
            # Get title
            if soup.title:
                content_parts.append(clean_text(soup.title.string))
            
            # Get meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc and meta_desc.get('content'):
                content_parts.append(clean_text(meta_desc['content']))
            
            # Try to get main content
            main_elements = soup.find_all(['main', 'article'], role='main')
            if main_elements:
                for elem in main_elements:
                    content_parts.append(clean_text(elem.get_text()))
            
            # Get headers as they're usually important
            headers = []
            for tag in ['h1', 'h2', 'h3']:
                headers.extend([h.get_text() for h in soup.find_all(tag)])
            if headers:
                content_parts.append(clean_text(' '.join(headers)))
            
        except Exception as e:
            print(f"Error processing HTML: {str(e)}")
    
    # Combine all content parts
    combined_content = ' '.join(filter(None, content_parts))
    print(f"Extracted content length: {len(combined_content)}")
    return combined_content

def chunk_content(content, max_length=max_sequence_length):
    """Split content into semantic chunks."""
    if not content:
        print("Warning: Empty content provided for chunking")
        return []
        
    print(f"Starting chunking of content (length: {len(content)})")
    sentences = sent_tokenize(content)
    print(f"Split into {len(sentences)} sentences")
    
    chunks = []
    current_chunk = []
    current_length = 0
    
    for sentence in sentences:
        sentence_length = len(sentence.split())
        if current_length + sentence_length <= max_length:
            current_chunk.append(sentence)
            current_length += sentence_length
        else:
            if current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunks.append(chunk_text)
                print(f"Created chunk {len(chunks)} (length: {len(chunk_text)}) \nChunk: {chunk_text}")
            current_chunk = [sentence]
            current_length = sentence_length
    
    if current_chunk:
        chunk_text = ' '.join(current_chunk)
        chunks.append(chunk_text)
        print(f"Created final chunk {len(chunks)} (length: {len(chunk_text)})")
    
    print(f"Created {len(chunks)} total chunks")
    return chunks

@app.route('/process_content', methods=['POST'])
def process_content():
    """Process webpage content and store in ChromaDB."""
    data = request.json
    url = data.get('url', '')
    title = data.get('title', '')
    html_content = data.get('content', '')
    main_text = data.get('mainText', '')
    timestamp = data.get('timestamp', datetime.now().isoformat())
    
    try:
        print(f"Processing content for URL: {url}")
        
        # Extract main content using both HTML and pre-extracted text
        main_content = extract_main_content(html_content, main_text)
        
        if not main_content:
            return jsonify({'status': 'error', 'message': 'No content could be extracted'}), 400
        
        # Create chunks
        chunks = chunk_content(main_content)
        
        if not chunks:
            return jsonify({'status': 'error', 'message': 'No chunks could be created'}), 400
        
        # Generate unique IDs for chunks
        chunk_ids = []
        chunk_texts = []
        metadatas = []
        
        for i, chunk in enumerate(chunks):
            # Create unique ID for chunk
            chunk_hash = hashlib.md5(f"{url}_{i}".encode()).hexdigest()
            chunk_ids.append(chunk_hash)
            chunk_texts.append(chunk)
            
            # Store metadata
            metadata = {
                "url": url,
                "title": title,
                "chunk_number": i,
                "total_chunks": len(chunks),
                "timestamp": timestamp
            }
            metadatas.append(metadata)
        
        # Add to ChromaDB
        collection.add(
            ids=chunk_ids,
            documents=chunk_texts,
            metadatas=metadatas
        )
        
        print(f"Successfully processed {len(chunks)} chunks for {url}")
        return jsonify({'status': 'success', 'chunks_processed': len(chunks)})
    except Exception as e:
        print(f"Error processing content: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/semantic_search', methods=['POST'])
def semantic_search():
    """Perform semantic search using ChromaDB."""
    data = request.json
    query = data.get('query', '')
    
    try:
        # Search in ChromaDB
        search_results = collection.query(
            query_texts=[query],
            n_results=20  # Get more results initially for grouping
        )
        
        # Group results by URL and calculate combined relevance
        grouped_results = {}
        for i, (metadata, distance) in enumerate(zip(search_results['metadatas'][0], search_results['distances'][0])):
            url = metadata['url']
            if url not in grouped_results:
                grouped_results[url] = {
                    'url': url,
                    'title': metadata['title'],
                    'timestamp': metadata['timestamp'],
                    'chunks': [],
                    'avg_distance': 0,
                    'matching_chunks': 0
                }
            
            grouped_results[url]['chunks'].append({
                'content': search_results['documents'][0][i],
                'distance': distance
            })
            grouped_results[url]['matching_chunks'] += 1
            grouped_results[url]['avg_distance'] = (
                sum(c['distance'] for c in grouped_results[url]['chunks']) / 
                len(grouped_results[url]['chunks'])
            )
        
        # Convert to list and sort by relevance
        results = list(grouped_results.values())
        results.sort(key=lambda x: (x['matching_chunks'], -x['avg_distance']), reverse=True)
        
        # Format top 10 results
        top_results = []
        for result in results[:10]:
            # Get the most relevant chunk as preview
            best_chunk = min(result['chunks'], key=lambda x: x['distance'])
            top_results.append({
                'url': result['url'],
                'title': result['title'],
                'timestamp': result['timestamp'],
                'similarity': 1 - result['avg_distance'],  # Convert distance to similarity
                'preview': best_chunk['content'][:200] + '...',
                'matching_chunks': result['matching_chunks']
            })
        
        return jsonify({'results': top_results})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)
