// Load saved settings
document.addEventListener('DOMContentLoaded', async () => {
  const settings = await chrome.storage.sync.get([
    'apiUrl', 'autoVerify', 'autoDetect', 'autoNotify', 'silentMode'
  ]);
  
  if (settings.apiUrl) {
    document.getElementById('apiUrl').value = settings.apiUrl;
  }
  
  // Set default values and load settings
  document.getElementById('autoDetect').checked = settings.autoDetect !== false; // Default true
  document.getElementById('autoVerify').checked = settings.autoVerify || false;
  document.getElementById('autoNotify').checked = settings.autoNotify !== false; // Default true
  document.getElementById('silentMode').checked = settings.silentMode || false;
});

// Save settings
document.getElementById('apiUrl').addEventListener('change', async (e) => {
  await chrome.storage.sync.set({ apiUrl: e.target.value });
});

document.getElementById('autoDetect').addEventListener('change', async (e) => {
  await chrome.storage.sync.set({ autoDetect: e.target.checked });
});

document.getElementById('autoVerify').addEventListener('change', async (e) => {
  await chrome.storage.sync.set({ autoVerify: e.target.checked });
});

document.getElementById('autoNotify').addEventListener('change', async (e) => {
  await chrome.storage.sync.set({ autoNotify: e.target.checked });
});

document.getElementById('silentMode').addEventListener('change', async (e) => {
  await chrome.storage.sync.set({ silentMode: e.target.checked });
});

// Verify current page
document.getElementById('verifyPage').addEventListener('click', async () => {
  showStatus('loading', 'Analyzing page content...');
  
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    chrome.tabs.sendMessage(tab.id, { action: 'getPageContent' }, async (response) => {
      if (chrome.runtime.lastError) {
        showStatus('error', 'Failed to get page content');
        return;
      }
      
      if (response && response.content) {
        await verifyContent(response.content, 'text');
      } else {
        showStatus('error', 'No content found on page');
      }
    });
  } catch (error) {
    showStatus('error', `Error: ${error.message}`);
  }
});

// Verify selected text
document.getElementById('verifySelection').addEventListener('click', async () => {
  showStatus('loading', 'Getting selected text...');
  
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    chrome.tabs.sendMessage(tab.id, { action: 'getSelection' }, async (response) => {
      if (chrome.runtime.lastError) {
        showStatus('error', 'Failed to get selection');
        return;
      }
      
      if (response && response.selection) {
        await verifyContent(response.selection, 'text');
      } else {
        showStatus('error', 'No text selected');
      }
    });
  } catch (error) {
    showStatus('error', `Error: ${error.message}`);
  }
});

// Verify image instruction
document.getElementById('verifyImage').addEventListener('click', () => {
  showStatus('info', 'Right-click on any image and select "Verify with OriginMark" from the context menu');
});

// Listen for verification results from background script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'verificationResult') {
    displayVerificationResult(request.result);
  }
});

// Verify content function
async function verifyContent(content, type) {
  const apiUrl = document.getElementById('apiUrl').value;
  
  try {
    // For demo purposes, we'll check if content has embedded signature
    const signatureMatch = content.match(/\[ORIGINMARK:([^\]]+)\]/);
    
    if (signatureMatch) {
      const signatureId = signatureMatch[1];
      
      // Verify with API
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
    } else {
      showStatus('info', 'No OriginMark signature found in content');
    }
  } catch (error) {
    showStatus('error', `Verification failed: ${error.message}`);
  }
}

// Display verification result
function displayVerificationResult(result) {
  const statusSection = document.getElementById('statusSection');
  const statusContent = document.getElementById('statusContent');
  
  statusSection.style.display = 'block';
  
  if (result.valid) {
    let html = `
      <div class="status status-success">
        ✓ Verified AI Content
      </div>
    `;
    
    if (result.metadata) {
      html += '<div class="metadata">';
      
      if (result.metadata.author) {
        html += `
          <div class="metadata-item">
            <span class="metadata-label">Author:</span>
            <span>${result.metadata.author}</span>
          </div>
        `;
      }
      
      if (result.metadata.model_used) {
        html += `
          <div class="metadata-item">
            <span class="metadata-label">Model:</span>
            <span>${result.metadata.model_used}</span>
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
        <div class="hash">${result.content_hash}</div>
      `;
    }
    
    statusContent.innerHTML = html;
  } else {
    statusContent.innerHTML = `
      <div class="status status-error">
        ✗ ${result.message || 'Verification failed'}
      </div>
    `;
  }
}

// Show status message
function showStatus(type, message) {
  const statusSection = document.getElementById('statusSection');
  const statusContent = document.getElementById('statusContent');
  
  statusSection.style.display = 'block';
  
  if (type === 'loading') {
    statusContent.innerHTML = `<div class="loading">${message}</div>`;
  } else {
    statusContent.innerHTML = `
      <div class="status status-${type}">
        ${message}
      </div>
    `;
  }
} 