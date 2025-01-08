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
import google.generativeai as genai
import os
from dotenv import load_dotenv
import math

# Load environment variables
load_dotenv()

# Configure Gemini API
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash-exp')

# Download required NLTK data
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)

app = Flask(__name__)
CORS(app)

# Initialize SBERT model and ChromaDB
model_name = 'sentence-transformers/multi-qa-MiniLM-L6-cos-v1'
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=model_name)
max_sequence_length = 512

# Initialize ChromaDB
chroma_client = chromadb.PersistentClient(path="./chroma_db")
try:
    collection = chroma_client.get_collection("webpage_chunks")
except:
    collection = chroma_client.create_collection(
        name="webpage_chunks",
        embedding_function=sentence_transformer_ef
    )

def clean_html(html_content):
    """Clean and prepare HTML content for LLM processing."""
    if not html_content or not html_content.strip():
        return ""
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove unwanted elements
        for element in soup.find_all(['script', 'style', 'nav', 'footer', 'iframe', 'header', 
                                    'aside', 'form', 'noscript', 'img']):
            element.decompose()
        
        # Extract title
        title = ""
        if soup.title:
            title = soup.title.string
        
        # Extract meta description
        meta_desc = ""
        meta_tag = soup.find('meta', attrs={'name': 'description'})
        if meta_tag and meta_tag.get('content'):
            meta_desc = meta_tag['content']
        
        # Get main content elements
        main_elements = soup.find_all(['article', 'main', 'div', 'section', 'p', 'h1', 'h2', 'h3'])
        
        # Prepare structured content
        structured_content = {
            'title': title.strip() if title else "",
            'meta_description': meta_desc.strip(),
            'main_content': ' '.join(elem.get_text().strip() for elem in main_elements if elem.get_text().strip())
        }
        
        return structured_content
        
    except Exception as e:
        print(f"Error cleaning HTML: {str(e)}")
        return ""

def extract_main_content(html_content, main_text):
    """Extract main content using hybrid approach with BeautifulSoup and Gemini."""
    try:
        # First clean and structure the HTML
        cleaned_content = clean_html(html_content)
        if not cleaned_content:
            return ""
        
        # Prepare prompt for Gemini
        prompt = f"""
        Analyze this webpage content and extract the most meaningful and relevant information.
        You only need to select the most relavant content. For example, if the webpage contains a table of content or a sidebar then skip those.
        Similarly, we do not need things like recommendations of other videos when we are talking about youtube pages. These things are irrelevant to the context of the current webpage.
        Focus on the main content while excluding any navigational elements, ads, or boilerplate text.
        
        Title: {cleaned_content['title']}
        Meta Description: {cleaned_content['meta_description']}
        
        Content: {cleaned_content['main_content']}
        
        Return only the essential information that best represents what this page is about.
        Format your response as clean text without any markdown or special formatting.
        Return only the content from within the main content area. Do not write or create anything by yourself.
        """
        
        # Get response from Gemini
        response = model.generate_content(prompt)
        
        if response.text:
            # Clean the extracted content
            extracted_content = response.text
            
            # Combine with title and meta description if they're meaningful
            content_parts = []
            if cleaned_content['title']:
                content_parts.append(cleaned_content['title'])
            if cleaned_content['meta_description']:
                content_parts.append(cleaned_content['meta_description'])
            content_parts.append(extracted_content)
            
            return ' '.join(content_parts)
        
        return ""
        
    except Exception as e:
        print(f"Error in content extraction: {str(e)}")
        return ""

def clean_text(text):
    """Clean and normalize text content."""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Remove URLs
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
    
    # Remove email addresses
    text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '', text)
    
    # Remove special characters but keep punctuation
    text = re.sub(r'[^\w\s.,!?-]', '', text)
    
    # Remove multiple punctuation
    text = re.sub(r'([.,!?])\1+', r'\1', text)
    
    return text.strip()

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
        print(f"Created final chunk {len(chunks)} (length: {len(chunk_text)}) \nChunk: {chunk_text}")
    
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
        
        # Extract main content using hybrid approach
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
            n_results=100  # Get more results initially for grouping
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
                    'avg_similarity': 0,
                    'matching_chunks': 0
                }
            
            try:
                # Ensure distance is a valid float and handle potential NaN values
                similarity = float(distance)
                if not isinstance(similarity, (int, float)) or math.isnan(similarity):
                    similarity = 0.0
                
                grouped_results[url]['chunks'].append({
                    'content': search_results['documents'][0][i],
                    'similarity': similarity
                })
                grouped_results[url]['matching_chunks'] += 1
                
                # Calculate average similarity with error handling
                chunk_similarities = [c['similarity'] for c in grouped_results[url]['chunks']]
                if chunk_similarities:
                    avg_similarity = sum(chunk_similarities) / len(chunk_similarities)
                    grouped_results[url]['avg_similarity'] = avg_similarity if not math.isnan(avg_similarity) else 0.0
                else:
                    grouped_results[url]['avg_similarity'] = 0.0
                    
            except (ValueError, TypeError) as e:
                print(f"Error processing similarity for chunk: {e}")
                continue
        
        # Convert to list and sort by relevance
        results = list(grouped_results.values())
        results.sort(key=lambda x: (x['matching_chunks'], x['avg_similarity']), reverse=True)
        
        # Format top 10 results
        top_results = []
        for result in results[:10]:
            try:
                # Get the most relevant chunk as preview
                best_chunk = max(result['chunks'], key=lambda x: x['similarity'])
                similarity_percentage = max(min(result['avg_similarity'] * 100, 100), 0)  # Clamp between 0-100
                
                top_results.append({
                    'url': result['url'],
                    'title': result['title'],
                    'timestamp': result['timestamp'],
                    'similarity': f"{similarity_percentage:.1f}%" if not math.isnan(similarity_percentage) else "0.0%",
                    'preview': best_chunk['content'][:200] + '...',
                    'matching_chunks': result['matching_chunks']
                })
            except (ValueError, TypeError, KeyError) as e:
                print(f"Error formatting result: {e}")
                continue
        
        return jsonify({
            'results': top_results,
            'query': query
        })
        
    except Exception as e:
        print(f"Error in semantic search: {str(e)}")
        return jsonify({
            'error': str(e),
            'results': [],
            'query': query
        })

if __name__ == '__main__':
    app.run(port=5000, debug=True) 
