document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('searchInput');
    const searchType = document.getElementById('searchType');
    const searchButton = document.getElementById('searchButton');
    const resultsDiv = document.getElementById('results');
    const searchTips = document.getElementById('searchTips');

    // Show/hide search tips based on search type
    searchType.addEventListener('change', () => {
        searchTips.style.display = searchType.value === 'semantic' ? 'block' : 'none';
    });

    searchButton.addEventListener('click', performSearch);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            performSearch();
        }
    });

    function performSearch() {
        const searchTerm = searchInput.value.toLowerCase();
        const type = searchType.value;

        if (type === 'semantic') {
            performSemanticSearch(searchTerm);
        } else {
            performLocalSearch(searchTerm, type);
        }
    }

    function performSemanticSearch(query) {
        resultsDiv.innerHTML = '<p class="loading">Searching...</p>';

        fetch('http://localhost:5000/semantic_search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query: query })
        })
        .then(response => response.json())
        .then(data => {
            displayResults(data.results, true);
        })
        .catch(error => {
            console.error('Error:', error);
            resultsDiv.innerHTML = '<p class="error">Error performing semantic search. Make sure the backend server is running.</p>';
        });
    }

    function performLocalSearch(searchTerm, type) {
        chrome.storage.local.get(['history'], (result) => {
            const history = result.history || [];
            let filteredResults = [];

            if (type === 'url') {
                filteredResults = history.filter(item => 
                    item.url.toLowerCase().includes(searchTerm)
                );
            } else if (type === 'title') {
                filteredResults = history.filter(item => 
                    item.title.toLowerCase().includes(searchTerm)
                );
            }

            displayResults(filteredResults, false);
        });
    }

    function displayResults(results, isSemanticSearch) {
        resultsDiv.innerHTML = '';

        if (results.length === 0) {
            resultsDiv.innerHTML = '<p class="result-item">No results found.</p>';
            return;
        }

        results.forEach(item => {
            const resultItem = document.createElement('div');
            resultItem.className = 'result-item';
            
            const date = new Date(item.timestamp);
            const formattedDate = date.toLocaleString();

            let content = `
                <h3>${item.title}</h3>
                <p><a href="${item.url}" target="_blank">${item.url}</a></p>
                <p class="timestamp">Visited: ${formattedDate}</p>
            `;

            if (isSemanticSearch) {
                const similarity = (item.similarity * 100).toFixed(1);
                content += `
                    <p class="similarity">Relevance: ${similarity}%</p>
                    <p class="preview">${item.preview}</p>
                `;
            }

            resultItem.innerHTML = content;
            resultsDiv.appendChild(resultItem);
        });
    }
});
