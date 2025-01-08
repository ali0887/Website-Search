from flask import Flask, request, jsonify
from flask_cors import CORS
from sentence_transformers import SentenceTransformer, util
import numpy as np
import json
from datetime import datetime
import torch

app = Flask(__name__)
CORS(app)

# Initialize SBERT model
model = SentenceTransformer('all-MiniLM-L6-v2')  # Lightweight but effective model
embeddings_cache = {}

def compute_embedding(text):
    """Compute embedding for given text."""
    try:
        embedding = model.encode(text, convert_to_tensor=True)
        return embedding
    except Exception as e:
        print(f"Error computing embedding: {str(e)}")
        return None

@app.route('/process_content', methods=['POST'])
def process_content():
    """Process new webpage content and store its embedding."""
    data = request.json
    content = data.get('content', '')
    url = data.get('url', '')
    
    try:
        # Compute embedding for the content
        embedding = compute_embedding(content)
        if embedding is None:
            return jsonify({'status': 'error', 'message': 'Failed to compute embedding'}), 500
            
        # Convert embedding to numpy and then to list for storage
        embedding_np = embedding.cpu().numpy()
        
        # Store embedding with metadata
        embeddings_cache[url] = {
            'embedding': embedding_np,  # Store as numpy array
            'content': content,
            'title': data.get('title', ''),
            'timestamp': data.get('timestamp', datetime.now().isoformat())
        }
        
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error in process_content: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/semantic_search', methods=['POST'])
def semantic_search():
    """Perform semantic search using query."""
    data = request.json
    query = data.get('query', '')
    
    try:
        # Compute query embedding
        query_embedding = compute_embedding(query)
        if query_embedding is None:
            return jsonify({'status': 'error', 'message': 'Failed to compute query embedding'}), 500
        
        # Calculate similarities with all stored embeddings
        results = []
        for url, data in embeddings_cache.items():
            try:
                # Convert stored numpy array to tensor
                page_embedding = torch.from_numpy(data['embedding']).to(query_embedding.device)
                
                # Calculate similarity
                similarity = util.pytorch_cos_sim(query_embedding, page_embedding)[0][0].item()
                
                results.append({
                    'url': url,
                    'title': data['title'],
                    'timestamp': data['timestamp'],
                    'similarity': float(similarity),  # Ensure it's a native Python float
                    'preview': data['content'][:200] + '...' if len(data['content']) > 200 else data['content']
                })
            except Exception as e:
                print(f"Error processing result for {url}: {str(e)}")
                continue
        
        # Sort by similarity and get top 10
        results.sort(key=lambda x: x['similarity'], reverse=True)
        top_results = results[:10]
        
        return jsonify({'results': top_results})
    except Exception as e:
        print(f"Error in semantic_search: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)
