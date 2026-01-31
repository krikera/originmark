// Content script for OriginMark extension

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getPageContent') {
    // Get main content of the page
    const content = getPageContent();
    sendResponse({ content: content });
  } else if (request.action === 'getSelection') {
    // Get selected text
    const selection = window.getSelection().toString();
    sendResponse({ selection: selection });
  }
});

// Extract main content from page
function getPageContent() {
  // Try to find main content areas
  const contentSelectors = [
    'main',
    'article',
    '[role="main"]',
    '.content',
    '#content',
    '.post-content',
    '.entry-content'
  ];
  
  for (const selector of contentSelectors) {
    const element = document.querySelector(selector);
    if (element) {
      return element.innerText;
    }
  }
  
  // Fallback to body text
  return document.body.innerText;
}

// Auto-detect OriginMark badges and signatures
function detectOriginMarkContent() {
  // Look for OriginMark signature patterns
  const signaturePattern = /\[ORIGINMARK:([a-f0-9-]+)\]/g;
  
  // Check all text nodes
  const walker = document.createTreeWalker(
    document.body,
    NodeFilter.SHOW_TEXT,
    null,
    false
  );
  
  const signatures = [];
  let node;
  
  while (node = walker.nextNode()) {
    const matches = node.textContent.matchAll(signaturePattern);
    for (const match of matches) {
      signatures.push({
        id: match[1],
        node: node,
        text: match[0]
      });
    }
  }
  
  // Add visual indicators for found signatures
  signatures.forEach(sig => {
    const badge = createVerificationBadge(sig.id);
    insertBadgeNearText(sig.node, sig.text, badge);
  });
  
  // Also look for OriginMark badge iframes
  const iframes = document.querySelectorAll('iframe[src*="/badge"]');
  iframes.forEach(iframe => {
    const url = new URL(iframe.src);
    const id = url.searchParams.get('id');
    if (id) {
      addVerificationIndicator(iframe, id);
    }
  });
}

// Create enhanced verification badge element with inline details
function createVerificationBadge(signatureId) {
  const container = document.createElement('div');
  container.className = 'originmark-badge-container';
  container.style.cssText = `
    display: inline-block;
    position: relative;
    margin-left: 8px;
    vertical-align: middle;
  `;

  const badge = document.createElement('span');
  badge.className = 'originmark-badge';
  badge.style.cssText = `
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: #22c55e;
    color: white;
    padding: 4px 12px;
    border-radius: 16px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
    box-shadow: 0 2px 6px rgba(34, 197, 94, 0.3);
  `;
  badge.innerHTML = '✓ Verified AI';
  badge.title = 'Click to view verification details';
  
  // Enhanced hover tooltip
  const tooltip = document.createElement('div');
  tooltip.className = 'originmark-tooltip';
  tooltip.style.cssText = `
    position: absolute;
    top: 100%;
    left: 50%;
    transform: translateX(-50%);
    background: #1f2937;
    color: white;
    padding: 12px;
    border-radius: 8px;
    font-size: 12px;
    min-width: 250px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    z-index: 10000;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.2s ease;
    line-height: 1.4;
  `;
  tooltip.innerHTML = `
    <div style="font-weight: 600; margin-bottom: 8px;"> OriginMark Verification</div>
    <div style="color: #9ca3af; margin-bottom: 6px;">Signature ID: ${signatureId.substring(0, 8)}...</div>
    <div style="margin-bottom: 6px;">
      <span style="color: #22c55e;">✓</span> Cryptographically verified content
    </div>
    <div style="color: #9ca3af; font-size: 11px;">Click to view full details</div>
  `;

  // Enhanced click handler with loading state
  badge.addEventListener('click', async (e) => {
    e.preventDefault();
    badge.innerHTML = '⏳ Verifying...';
    badge.style.background = '#f59e0b';
    
    try {
      await verifySignatureWithDetails(signatureId, badge, tooltip);
    } catch (error) {
      badge.innerHTML = ' Error';
      badge.style.background = '#ef4444';
      console.error('Verification error:', error);
    }
  });

  // Hover effects
  badge.addEventListener('mouseenter', () => {
    badge.style.transform = 'scale(1.05)';
    tooltip.style.opacity = '1';
  });

  badge.addEventListener('mouseleave', () => {
    badge.style.transform = 'scale(1)';
    tooltip.style.opacity = '0';
  });

  container.appendChild(badge);
  container.appendChild(tooltip);
  
  return container;
}

// Insert badge near text
function insertBadgeNearText(textNode, signatureText, badge) {
  const parent = textNode.parentNode;
  const text = textNode.textContent;
  const index = text.indexOf(signatureText);
  
  if (index !== -1) {
    const before = text.substring(0, index);
    const after = text.substring(index + signatureText.length);
    
    const beforeNode = document.createTextNode(before);
    const afterNode = document.createTextNode(after);
    
    parent.insertBefore(beforeNode, textNode);
    parent.insertBefore(badge, textNode);
    parent.insertBefore(afterNode, textNode);
    parent.removeChild(textNode);
  }
}

// Add verification indicator to iframe
function addVerificationIndicator(iframe, signatureId) {
  const wrapper = document.createElement('div');
  wrapper.style.cssText = `
    position: relative;
    display: inline-block;
  `;
  
  const indicator = document.createElement('div');
  indicator.style.cssText = `
    position: absolute;
    top: 5px;
    right: 5px;
    background: #22c55e;
    color: white;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  `;
  indicator.innerHTML = '✓ OriginMark';
  indicator.title = 'Click to verify';
  
  indicator.addEventListener('click', () => {
    verifySignature(signatureId);
  });
  
  iframe.parentNode.insertBefore(wrapper, iframe);
  wrapper.appendChild(iframe);
  wrapper.appendChild(indicator);
}

// Enhanced verification with detailed inline display
async function verifySignatureWithDetails(signatureId, badgeElement, tooltipElement = null) {
  try {
    // Get settings
    const settings = await chrome.storage.sync.get(['apiUrl']);
    const apiUrl = settings.apiUrl || 'http://localhost:8000';
    
    // Fetch signature details
    const response = await fetch(`${apiUrl}/signatures/${signatureId}`);
    
    if (!response.ok) {
      throw new Error('Signature not found');
    }
    
    const data = await response.json();
    
    // Update badge with success state
    badgeElement.innerHTML = ' Verified';
    badgeElement.style.background = '#22c55e';
    
    // Update tooltip with detailed information
    if (tooltipElement) {
      const metadata = data.metadata || {};
      tooltipElement.innerHTML = `
        <div style="font-weight: 600; margin-bottom: 8px; color: #22c55e;"> Verified AI Content</div>
        <div style="border-bottom: 1px solid #374151; margin-bottom: 8px; padding-bottom: 8px;">
          <div style="margin-bottom: 4px;">
            <strong>Author:</strong> ${metadata.author || 'Unknown'}
          </div>
          <div style="margin-bottom: 4px;">
            <strong>Model:</strong> ${metadata.model_used || 'Not specified'}
          </div>
          <div style="margin-bottom: 4px;">
            <strong>Created:</strong> ${new Date(metadata.timestamp).toLocaleDateString()}
          </div>
          <div>
            <strong>Type:</strong> ${metadata.content_type || 'Unknown'}
          </div>
        </div>
        <div style="color: #9ca3af; font-size: 11px;">
          <div>ID: ${data.id.substring(0, 16)}...</div>
          <div>Hash: ${data.content_hash.substring(0, 16)}...</div>
        </div>
        <div style="color: #60a5fa; font-size: 11px; margin-top: 6px; cursor: pointer;" onclick="showExpandedView()">Click for full details →</div>
      `;
    }
    
    // Send success message to background
    chrome.runtime.sendMessage({
      action: 'verificationResult',
      result: { valid: true, metadata: data.metadata, signature_id: signatureId }
    });
    
  } catch (error) {
    badgeElement.innerHTML = ' Failed';
    badgeElement.style.background = '#ef4444';
    
    if (tooltipElement) {
      tooltipElement.innerHTML = `
        <div style="font-weight: 600; margin-bottom: 8px; color: #ef4444;"> Verification Failed</div>
        <div style="color: #fca5a5;">Could not verify signature</div>
        <div style="color: #9ca3af; font-size: 11px; margin-top: 6px;">${error.message}</div>
      `;
    }
    
    throw error;
  }
}

// Verify signature (legacy function for backward compatibility)
async function verifySignature(signatureId) {
  chrome.runtime.sendMessage({
    action: 'verifyContent',
    content: `[ORIGINMARK:${signatureId}]`
  });
}

// Run detection when page loads
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', detectOriginMarkContent);
} else {
  detectOriginMarkContent();
}

// Also run detection when new content is added
const observer = new MutationObserver((mutations) => {
  // Debounce to avoid running too frequently
  clearTimeout(observer.timeout);
  observer.timeout = setTimeout(detectOriginMarkContent, 500);
});

observer.observe(document.body, {
  childList: true,
  subtree: true
}); 