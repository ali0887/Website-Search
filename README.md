# Website History Logger Extension

A powerful browser extension that helps you keep track of and search through your browsing history with enhanced capabilities.

## Features

- **Automatic Background Logging**: Automatically logs every webpage you visit without any manual intervention
- **Comprehensive Data Collection**:
  - Complete webpage URL
  - Page title
  - Page content (for searchability)
  - Precise timestamp of visits

- **Smart Duplicate Prevention**: Intelligently prevents duplicate entries for streaming sites and single-page applications

- **Flexible Search Options**:
  - Search by URL: Find all websites containing specific domains or URL patterns
  - Search by Title: Locate pages based on their title content
  - Real-time search results with clean, organized display

## Use Cases

1. **Research Tracking**:
   - Keep track of all research materials you've read
   - Easily find that article you remember reading but forgot to bookmark

2. **Professional Work**:
   - Track client websites visited
   - Document research for projects
   - Find previously visited documentation pages

3. **Personal Use**:
   - Find that recipe website you visited last week
   - Track your learning progress through various tutorials
   - Maintain a comprehensive history of your web activities

## Installation

1. Download or clone this repository
2. Open Chrome/Edge browser
3. Navigate to extensions page:
   - Chrome: chrome://extensions
   - Edge: edge://extensions
4. Enable "Developer mode" (toggle in top right)
5. Click "Load unpacked"
6. Select the extension directory

## How to Use

1. **Automatic Logging**:
   - The extension automatically starts logging as soon as it's installed
   - No manual intervention needed
   - Works in background while you browse

2. **Searching History**:
   - Click the extension icon in your browser toolbar
   - Enter your search term in the search box
   - Select search type (URL or Title)
   - Click Search or press Enter
   - View results in a clean, organized format

## Privacy & Storage

- All data is stored locally on your machine
- No external servers or data transmission
- You have complete control over your browsing history data

## Technical Details

- Built using Manifest V3
- Uses modern browser APIs for efficient data handling
- Implements tab state tracking to prevent duplicate entries
- Responsive and modern UI design
- Efficient search algorithms for quick results

## Limitations

- Cannot log chrome:// or edge:// pages (browser restriction)
- Content storage is limited to prevent excessive memory usage
- Local storage capacity depends on your browser's limits