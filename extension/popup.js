// OriginMark Extension - Popup Script
// Modern JavaScript with async/await patterns

'use strict';

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', async () => {
  await loadSettings();
  setupEventListeners();
});

/**
 * Load saved settings from storage
 */
async function loadSettings() {
  const settings = await chrome.storage.sync.get([
    'apiUrl', 'autoVerify', 'autoDetect', 'autoNotify', 'silentMode'
  ]);
  
  // Set API URL
  const apiUrlInput = document.getElementById('apiUrl');
  if (apiUrlInput && settings.apiUrl) {
    apiUrlInput.value = settings.apiUrl;
  }
  
  // Set checkbox states with defaults
  setCheckbox('autoDetect', settings.autoDetect !== false);
  setCheckbox('autoVerify', settings.autoVerify ?? false);
  setCheckbox('autoNotify', settings.autoNotify !== false);
  setCheckbox('silentMode', settings.silentMode ?? false);
}

/**
 * Set checkbox checked state
 * @param {string} id - Element ID
 * @param {boolean} checked - Checked state
 */
function setCheckbox(id, checked) {
  const element = document.getElementById(id);
  if (element) {
    element.checked = checked;
  }
}

// ============================================================================
// EVENT LISTENERS
// ============================================================================

/**
 * Setup all event listeners
 */
function setupEventListeners() {
  // Settings change handlers
  const settingsMap = {
    'apiUrl': 'apiUrl',
    'autoDetect': 'autoDetect',
    'autoVerify': 'autoVerify',
    'autoNotify': 'autoNotify',
    'silentMode': 'silentMode'
  };
  
  Object.entries(settingsMap).forEach(([elementId, storageKey]) => {
    const element = document.getElementById(elementId);
    if (element) {
      const eventType = element.type === 'checkbox' ? 'change' : 'change';
      element.addEventListener(eventType, async (e) => {
        const value = element.type === 'checkbox' ? e.target.checked : e.target.value;
        await chrome.storage.sync.set({ [storageKey]: value });
      });
    }
  });
  
  // Action buttons
  document.getElementById('verifyPage')?.addEventListener('click', handleVerifyPage);
  document.getElementById('verifySelection')?.addEventListener('click', handleVerifySelection);
  document.getElementById('verifyImage')?.addEventListener('click', handleVerifyImage);
  
  // Listen for verification results from background script
  chrome.runtime.onMessage.addListener((request) => {
    if (request.action === 'verificationResult') {
      displayVerificationResult(request.result);
    }
  });
}

// ============================================================================
// ACTION HANDLERS
// ============================================================================

/**
 * Handle verify page button click
 */
async function handleVerifyPage() {
  showStatus('loading', 'Analyzing page content...');
  
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    if (!tab?.id) {
      showStatus('error', 'Could not access current tab');
      return;
    }
    
    const response = await sendMessageToTab(tab.id, { action: 'getPageContent' });
    
    if (response?.content) {
      await verifyContent(response.content);
    } else {
      showStatus('error', 'No content found on page');
    }
  } catch (error) {
    showStatus('error', `Error: ${error.message}`);
  }
}

/**
 * Handle verify selection button click
 */
async function handleVerifySelection() {
  showStatus('loading', 'Getting selected text...');
  
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    if (!tab?.id) {
      showStatus('error', 'Could not access current tab');
      return;
    }
    
    const response = await sendMessageToTab(tab.id, { action: 'getSelection' });
    
    if (response?.selection) {
      await verifyContent(response.selection);
    } else {
      showStatus('error', 'No text selected');
    }
  } catch (error) {
    showStatus('error', `Error: ${error.message}`);
  }
}

/**
 * Handle verify image button click
 */
function handleVerifyImage() {
  showStatus('info', 'Right-click on any image and select "Verify with OriginMark" from the context menu');
}

/**
 * Send message to content script in tab
 * @param {number} tabId - Tab ID
 * @param {Object} message - Message to send
 * @returns {Promise<Object>} Response from content script
 */
function sendMessageToTab(tabId, message) {
  return new Promise((resolve, reject) => {
    chrome.tabs.sendMessage(tabId, message, (response) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
      } else {
        resolve(response);
      }
    });
  });
}

// ============================================================================
// VERIFICATION
// ============================================================================

/**
 * Verify content against API
 * @param {string} content - Content to verify
 */
async function verifyContent(content) {
  const apiUrl = document.getElementById('apiUrl')?.value || 'http://localhost:8000';
  
  // Check for embedded signature
  const signatureMatch = content.match(/\[ORIGINMARK:([^\]]+)\]/);
  
  if (!signatureMatch) {
    showStatus('info', 'No OriginMark signature found in content');
    return;
  }
  
  const signatureId = signatureMatch[1];
  
  try {
    const response = await fetch(`${apiUrl}/signatures/${signatureId}`);
    
    if (response.ok) {
      const data = await response.json();
      displayVerificationResult({
        valid: true,
        signature_id: signatureId,
        metadata: data.metadata,
        content_hash: data.content_hash
      });
    } else {
      showStatus('error', 'Signature not found in database');
    }
  } catch (error) {
    showStatus('error', `Verification failed: ${error.message}`);
  }
}

// ============================================================================
// UI FUNCTIONS
// ============================================================================

/**
 * Display verification result
 * @param {Object} result - Verification result
 */
function displayVerificationResult(result) {
  const statusSection = document.getElementById('statusSection');
  const statusContent = document.getElementById('statusContent');
  
  if (!statusSection || !statusContent) return;
  
  statusSection.style.display = 'block';
  
  if (result.valid) {
    statusContent.innerHTML = buildSuccessHTML(result);
  } else {
    statusContent.innerHTML = `
      <div class="status status-error">
        ✗ ${escapeHTML(result.message || 'Verification failed')}
      </div>
    `;
  }
}

/**
 * Build HTML for successful verification
 * @param {Object} result - Verification result
 * @returns {string} HTML string
 */
function buildSuccessHTML(result) {
  let html = `<div class="status status-success">✓ Verified AI Content</div>`;
  
  if (result.metadata) {
    html += '<div class="metadata">';
    
    if (result.metadata.author) {
      html += `
        <div class="metadata-item">
          <span class="metadata-label">Author:</span>
          <span>${escapeHTML(result.metadata.author)}</span>
        </div>
      `;
    }
    
    if (result.metadata.model_used) {
      html += `
        <div class="metadata-item">
          <span class="metadata-label">Model:</span>
          <span>${escapeHTML(result.metadata.model_used)}</span>
        </div>
      `;
    }
    
    if (result.metadata.timestamp) {
      html += `
        <div class="metadata-item">
          <span class="metadata-label">Created:</span>
          <span>${new Date(result.metadata.timestamp).toLocaleString()}</span>
        </div>
      `;
    }
    
    html += '</div>';
  }
  
  if (result.content_hash) {
    html += `
      <div class="metadata-item" style="margin-top: 12px;">
        <span class="metadata-label">Hash:</span>
      </div>
      <div class="hash">${escapeHTML(result.content_hash)}</div>
    `;
  }
  
  return html;
}

/**
 * Show status message
 * @param {string} type - Status type (loading, error, info, success)
 * @param {string} message - Status message
 */
function showStatus(type, message) {
  const statusSection = document.getElementById('statusSection');
  const statusContent = document.getElementById('statusContent');
  
  if (!statusSection || !statusContent) return;
  
  statusSection.style.display = 'block';
  
  if (type === 'loading') {
    statusContent.innerHTML = `<div class="loading">${escapeHTML(message)}</div>`;
  } else {
    statusContent.innerHTML = `
      <div class="status status-${type}">
        ${escapeHTML(message)}
      </div>
    `;
  }
}

/**
 * Escape HTML to prevent XSS
 * @param {string} str - String to escape
 * @returns {string} Escaped string
 */
function escapeHTML(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}