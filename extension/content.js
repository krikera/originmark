// OriginMark Extension - Content Script
// Modern JavaScript for page content scanning and verification

'use strict';

// ============================================================================
// CONSTANTS
// ============================================================================

const SIGNATURE_PATTERN = /\[ORIGINMARK:([a-f0-9-]+)\]/g;
const DEBOUNCE_DELAY = 500;
const DEFAULT_API_URL = 'http://localhost:8000';

// ============================================================================
// MESSAGE HANDLING
// ============================================================================

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  switch (request.action) {
    case 'getPageContent':
      sendResponse({ content: getPageContent() });
      break;
      
    case 'getSelection':
      sendResponse({ selection: window.getSelection().toString() });
      break;
      
    case 'scanForSignatures':
      sendResponse({ signatures: scanForSignatures() });
      break;
      
    default:
      sendResponse({ error: 'Unknown action' });
  }
  
  return false; // Synchronous response
});

// ============================================================================
// CONTENT EXTRACTION
// ============================================================================

/**
 * Extract main content from page
 * @returns {string} Page content text
 */
function getPageContent() {
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
  
  return document.body.innerText;
}

/**
 * Scan page for OriginMark signatures
 * @returns {string[]} Array of signature IDs
 */
function scanForSignatures() {
  const signatures = [];
  const walker = document.createTreeWalker(
    document.body,
    NodeFilter.SHOW_TEXT,
    null
  );
  
  let node;
  while ((node = walker.nextNode())) {
    const matches = node.textContent.matchAll(SIGNATURE_PATTERN);
    for (const match of matches) {
      signatures.push(match[1]);
    }
  }
  
  return [...new Set(signatures)]; // Deduplicate
}

// ============================================================================
// SIGNATURE DETECTION & BADGE CREATION
// ============================================================================

/**
 * Detect and mark OriginMark signatures on page
 */
function detectOriginMarkContent() {
  const walker = document.createTreeWalker(
    document.body,
    NodeFilter.SHOW_TEXT,
    null
  );
  
  const nodesToProcess = [];
  let node;
  
  while ((node = walker.nextNode())) {
    const matches = [...node.textContent.matchAll(SIGNATURE_PATTERN)];
    if (matches.length > 0) {
      nodesToProcess.push({ node, matches });
    }
  }
  
  // Process nodes after walking to avoid DOM modification issues
  nodesToProcess.forEach(({ node, matches }) => {
    matches.forEach(match => {
      const badge = createVerificationBadge(match[1]);
      insertBadgeNearText(node, match[0], badge);
    });
  });
  
  // Also detect badge iframes
  detectBadgeIframes();
}

/**
 * Detect OriginMark badge iframes
 */
function detectBadgeIframes() {
  const iframes = document.querySelectorAll('iframe[src*="/badge"]');
  
  iframes.forEach(iframe => {
    try {
      const url = new URL(iframe.src);
      const id = url.searchParams.get('id');
      if (id) {
        addVerificationIndicator(iframe, id);
      }
    } catch {
      // Invalid URL, skip
    }
  });
}

/**
 * Create verification badge element
 * @param {string} signatureId - Signature ID
 * @returns {HTMLElement} Badge container element
 */
function createVerificationBadge(signatureId) {
  const container = document.createElement('div');
  container.className = 'originmark-badge-container';
  Object.assign(container.style, {
    display: 'inline-block',
    position: 'relative',
    marginLeft: '8px',
    verticalAlign: 'middle'
  });

  const badge = document.createElement('span');
  badge.className = 'originmark-badge';
  Object.assign(badge.style, {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    background: '#22c55e',
    color: 'white',
    padding: '4px 12px',
    borderRadius: '16px',
    fontSize: '12px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    boxShadow: '0 2px 6px rgba(34, 197, 94, 0.3)'
  });
  badge.textContent = '✓ Verified AI';
  badge.title = 'Click to view verification details';
  
  // Create tooltip
  const tooltip = createTooltip(signatureId);
  
  // Event handlers
  badge.addEventListener('click', async (e) => {
    e.preventDefault();
    await handleBadgeClick(signatureId, badge, tooltip);
  });

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

/**
 * Create tooltip element
 * @param {string} signatureId - Signature ID
 * @returns {HTMLElement} Tooltip element
 */
function createTooltip(signatureId) {
  const tooltip = document.createElement('div');
  tooltip.className = 'originmark-tooltip';
  Object.assign(tooltip.style, {
    position: 'absolute',
    top: '100%',
    left: '50%',
    transform: 'translateX(-50%)',
    background: '#1f2937',
    color: 'white',
    padding: '12px',
    borderRadius: '8px',
    fontSize: '12px',
    minWidth: '250px',
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
    zIndex: '10000',
    opacity: '0',
    pointerEvents: 'none',
    transition: 'opacity 0.2s ease',
    lineHeight: '1.4'
  });
  
  tooltip.innerHTML = `
    <div style="font-weight: 600; margin-bottom: 8px;"> OriginMark Verification</div>
    <div style="color: #9ca3af; margin-bottom: 6px;">Signature ID: ${signatureId.substring(0, 8)}...</div>
    <div style="margin-bottom: 6px;">
      <span style="color: #22c55e;">✓</span> Cryptographically verified content
    </div>
    <div style="color: #9ca3af; font-size: 11px;">Click to view full details</div>
  `;
  
  return tooltip;
}

/**
 * Handle badge click for verification
 * @param {string} signatureId - Signature ID
 * @param {HTMLElement} badge - Badge element
 * @param {HTMLElement} tooltip - Tooltip element
 */
async function handleBadgeClick(signatureId, badge, tooltip) {
  badge.textContent = '⏳ Verifying...';
  badge.style.background = '#f59e0b';
  
  try {
    await verifySignatureWithDetails(signatureId, badge, tooltip);
  } catch (error) {
    badge.textContent = ' Error';
    badge.style.background = '#ef4444';
    console.error('Verification error:', error);
  }
}

/**
 * Insert badge near signature text
 * @param {Node} textNode - Text node containing signature
 * @param {string} signatureText - Signature text to replace
 * @param {HTMLElement} badge - Badge element
 */
function insertBadgeNearText(textNode, signatureText, badge) {
  const parent = textNode.parentNode;
  if (!parent) return;
  
  const text = textNode.textContent;
  const index = text.indexOf(signatureText);
  
  if (index === -1) return;
  
  const before = text.substring(0, index);
  const after = text.substring(index + signatureText.length);
  
  const fragment = document.createDocumentFragment();
  fragment.appendChild(document.createTextNode(before));
  fragment.appendChild(badge);
  fragment.appendChild(document.createTextNode(after));
  
  parent.replaceChild(fragment, textNode);
}

/**
 * Add verification indicator to iframe
 * @param {HTMLIFrameElement} iframe - Iframe element
 * @param {string} signatureId - Signature ID
 */
function addVerificationIndicator(iframe, signatureId) {
  const wrapper = document.createElement('div');
  Object.assign(wrapper.style, {
    position: 'relative',
    display: 'inline-block'
  });
  
  const indicator = document.createElement('div');
  Object.assign(indicator.style, {
    position: 'absolute',
    top: '5px',
    right: '5px',
    background: '#22c55e',
    color: 'white',
    padding: '4px 8px',
    borderRadius: '4px',
    fontSize: '12px',
    fontWeight: '500',
    cursor: 'pointer',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
  });
  indicator.textContent = '✓ OriginMark';
  indicator.title = 'Click to verify';
  
  indicator.addEventListener('click', () => {
    verifySignature(signatureId);
  });
  
  iframe.parentNode?.insertBefore(wrapper, iframe);
  wrapper.appendChild(iframe);
  wrapper.appendChild(indicator);
}

// ============================================================================
// VERIFICATION API
// ============================================================================

/**
 * Verify signature with detailed inline display
 * @param {string} signatureId - Signature ID
 * @param {HTMLElement} badgeElement - Badge element
 * @param {HTMLElement} tooltipElement - Tooltip element
 */
async function verifySignatureWithDetails(signatureId, badgeElement, tooltipElement) {
  const settings = await chrome.storage.sync.get(['apiUrl']);
  const apiUrl = settings.apiUrl || DEFAULT_API_URL;
  
  const response = await fetch(`${apiUrl}/signatures/${signatureId}`);
  
  if (!response.ok) {
    throw new Error('Signature not found');
  }
  
  const data = await response.json();
  
  // Update badge with success state
  badgeElement.textContent = ' Verified';
  badgeElement.style.background = '#22c55e';
  
  // Update tooltip with detailed information
  if (tooltipElement) {
    const metadata = data.metadata || {};
    tooltipElement.innerHTML = `
      <div style="font-weight: 600; margin-bottom: 8px; color: #22c55e;"> Verified AI Content</div>
      <div style="border-bottom: 1px solid #374151; margin-bottom: 8px; padding-bottom: 8px;">
        <div style="margin-bottom: 4px;">
          <strong>Author:</strong> ${escapeHTML(metadata.author || 'Unknown')}
        </div>
        <div style="margin-bottom: 4px;">
          <strong>Model:</strong> ${escapeHTML(metadata.model_used || 'Not specified')}
        </div>
        <div style="margin-bottom: 4px;">
          <strong>Created:</strong> ${metadata.timestamp ? new Date(metadata.timestamp).toLocaleDateString() : 'Unknown'}
        </div>
        <div>
          <strong>Type:</strong> ${escapeHTML(metadata.content_type || 'Unknown')}
        </div>
      </div>
      <div style="color: #9ca3af; font-size: 11px;">
        <div>ID: ${data.id?.substring(0, 16) || 'Unknown'}...</div>
        <div>Hash: ${data.content_hash?.substring(0, 16) || 'Unknown'}...</div>
      </div>
    `;
  }
  
  // Send success message to background
  chrome.runtime.sendMessage({
    action: 'verificationResult',
    result: { valid: true, metadata: data.metadata, signature_id: signatureId }
  }).catch(() => {}); // Ignore if background is unavailable
}

/**
 * Verify signature (legacy function for backward compatibility)
 * @param {string} signatureId - Signature ID
 */
function verifySignature(signatureId) {
  chrome.runtime.sendMessage({
    action: 'verifyContent',
    content: `[ORIGINMARK:${signatureId}]`
  }).catch(() => {});
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

// ============================================================================
// INITIALIZATION
// ============================================================================

// Run detection when page loads
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', detectOriginMarkContent);
} else {
  detectOriginMarkContent();
}

// Monitor for dynamically added content
const observer = new MutationObserver(debounce(detectOriginMarkContent, DEBOUNCE_DELAY));

observer.observe(document.body, {
  childList: true,
  subtree: true
});

/**
 * Debounce function to limit execution frequency
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} Debounced function
 */
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(this, args), wait);
  };
}