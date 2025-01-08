document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('searchInput');
    const searchType = document.getElementById('searchType');
    const searchButton = document.getElementById('searchButton');
    const resultsDiv = document.getElementById('results');

    searchButton.addEventListener('click', performSearch);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            performSearch();
        }
    });

    function performSearch() {
        const searchTerm = searchInput.value.toLowerCase();
        const type = searchType.value;

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

            displayResults(filteredResults);
        });
    }

    function displayResults(results) {
        resultsDiv.innerHTML = '';

        if (results.length === 0) {
            resultsDiv.innerHTML = '<p class="result-item">No results found.</p>';
            return;
        }

        results.reverse().forEach(item => {
            const resultItem = document.createElement('div');
            resultItem.className = 'result-item';
            
            const date = new Date(item.timestamp);
            const formattedDate = date.toLocaleString();

            resultItem.innerHTML = `
                <h3>${item.title}</h3>
                <p><a href="${item.url}" target="_blank">${item.url}</a></p>
                <p class="timestamp">Visited: ${formattedDate}</p>
            `;

            resultsDiv.appendChild(resultItem);
        });
    }
});
