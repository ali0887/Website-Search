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

                // Store the data
                chrome.storage.local.get(['history'], (result) => {
                    const history = result.history || [];
                    history.push(visitData);
                    chrome.storage.local.set({ history: history });
                });

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
    // Get text content while removing excess whitespace
    return document.body.innerText
        .replace(/\s+/g, ' ')
        .trim()
        .substring(0, 1000); // Limit content length
}
