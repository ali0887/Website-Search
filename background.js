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
                const pageData = results[0].result;
                const visitData = {
                    url: tab.url,
                    title: tab.title,
                    content: pageData.content,
                    mainText: pageData.mainText,
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
    // Get both HTML and text content
    const content = {
        // Get the HTML content of the main content areas
        content: document.documentElement.outerHTML,
        // Get the main text content as backup
        mainText: (() => {
            const mainContent = [];
            
            // Get title
            const title = document.title;
            if (title) mainContent.push(title);
            
            // Get meta description
            const metaDesc = document.querySelector('meta[name="description"]');
            if (metaDesc) mainContent.push(metaDesc.content);
            
            // Get main content areas
            const mainElements = document.querySelectorAll('main, article, [role="main"]');
            if (mainElements.length > 0) {
                mainElements.forEach(elem => mainContent.push(elem.innerText));
            } else {
                // If no main content areas found, get content from body
                const bodyText = Array.from(document.body.children)
                    .filter(elem => {
                        const tag = elem.tagName.toLowerCase();
                        // Exclude common non-content elements
                        return !['script', 'style', 'nav', 'header', 'footer'].includes(tag);
                    })
                    .map(elem => elem.innerText)
                    .join('\n');
                mainContent.push(bodyText);
            }
            
            // Get headers
            const headers = document.querySelectorAll('h1, h2, h3');
            headers.forEach(header => mainContent.push(header.innerText));
            
            return mainContent.join('\n').trim();
        })()
    };
    
    return content;
}
