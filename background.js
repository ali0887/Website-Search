// Keep track of tabs to prevent duplicate logging
let tabsState = {};

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    // Only log when the page is completely loaded
    if (changeInfo.status === 'complete' && tab.url && !tab.url.startsWith('chrome://') && !tab.url.startsWith('edge://')) {
        // Check if we've already logged this tab's current URL
        if (tabsState[tabId]?.url !== tab.url) {
            chrome.scripting.executeScript({
                target: { tabId: tabId },
                function: getPageContent,
            }).then((results) => {
                const pageContent = results[0].result;
                const visitData = {
                    url: tab.url,
                    title: tab.title,
                    content: pageContent,
                    timestamp: new Date().toISOString(),
                };

                // Store the data locally
                chrome.storage.local.get(['history'], (result) => {
                    const history = result.history || [];
                    history.push(visitData);
                    chrome.storage.local.set({ history: history });
                });

                // Send to Python backend for processing
                fetch('http://localhost:5000/process_content', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(visitData)
                }).catch(error => console.error('Error sending data to backend:', error));

                // Update tabsState
                tabsState[tabId] = {
                    url: tab.url,
                    timestamp: new Date().toISOString()
                };
            });
        }
    }
});

// Clean up tabsState when a tab is closed
chrome.tabs.onRemoved.addListener((tabId) => {
    delete tabsState[tabId];
});

// Function to get page content
function getPageContent() {
    // Get full page content including text and basic structure
    const content = [];
    
    // Get title and headers for context
    content.push(document.title);
    document.querySelectorAll('h1, h2, h3').forEach(header => {
        content.push(header.textContent);
    });
    
    // Get main content
    const mainContent = document.body.innerText;
    content.push(mainContent);
    
    // Join all content with spaces
    return content.join(' ').replace(/\s+/g, ' ').trim();
}
