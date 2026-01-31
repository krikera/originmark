// OriginMark Browser Extension - Background Service Worker
// Modern ES Module with async/await patterns

'use strict';

// Constants
const DEFAULT_API_URL = 'http://localhost:8000';
const NOTIFICATION_TIMEOUT = 5000;
const MAX_STORED_EVENTS = 100;
const PAGE_SCAN_DELAY = 2000;

// State management
const pageSignatures = new Map();

// ============================================================================
// INITIALIZATION
// ============================================================================

chrome.runtime.onInstalled.addListener(() => {
  // Create context menus
  chrome.contextMenus.create({
    id: 'verifyImage',
    title: 'Verify with OriginMark',
    contexts: ['image']
  });
  
  chrome.contextMenus.create({
    id: 'verifyText',
    title: 'Verify selected text with OriginMark',
    contexts: ['selection']
  });
  
  // Set default settings
  chrome.storage.sync.get(['apiUrl', 'autoDetect', 'autoNotify'], (settings) => {
    const defaults = {
      apiUrl: settings.apiUrl ?? DEFAULT_API_URL,
      autoDetect: settings.autoDetect ?? true,
      autoNotify: settings.autoNotify ?? true
    };
    chrome.storage.sync.set(defaults);
  });
});

// ============================================================================
// CONTEXT MENU HANDLERS
// ============================================================================

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  try {
    if (info.menuItemId === 'verifyImage') {
      await verifyImage(info.srcUrl, tab);
    } else if (info.menuItemId === 'verifyText') {
      await verifyText(info.selectionText, tab);
    }
  } catch (error) {
    console.error('Context menu action failed:', error);
    showNotification({
      valid: false,
      message: `Action failed: ${error.message}`
    });
  }
});

// ============================================================================
// VERIFICATION FUNCTIONS
// ============================================================================

/**
 * Get API URL from storage
 * @returns {Promise<string>} API URL
 */
async function getApiUrl() {
  const { apiUrl } = await chrome.storage.sync.get(['apiUrl']);
  return apiUrl || DEFAULT_API_URL;
}

/**
 * Verify an image from URL
 * @param {string} imageUrl - URL of the image to verify
 * @param {chrome.tabs.Tab} tab - Current tab
 */
async function verifyImage(imageUrl, tab) {
  const apiUrl = await getApiUrl();
  
  // Fetch image
  const response = await fetch(imageUrl);
  if (!response.ok) {
    throw new Error('Failed to fetch image');
  }
  
  const blob = await response.blob();
  
  // Create form data
  const formData = new FormData();
  formData.append('file', blob, 'image.png');
  
  // Check for signature ID in URL
  const signatureId = extractSignatureId(imageUrl);
  if (signatureId) {
    formData.append('signature_id', signatureId);
  }
  
  // Verify with API
  const verifyResponse = await fetch(`${apiUrl}/verify`, {
    method: 'POST',
    body: formData
  });
  
  const result = await verifyResponse.json();
  
  // Broadcast result and show notification
  chrome.runtime.sendMessage({
    action: 'verificationResult',
    result
  }).catch(() => {}); // Ignore if popup is closed
  
  showNotification(result);
}

/**
 * Verify selected text
 * @param {string} text - Text to verify
 * @param {chrome.tabs.Tab} tab - Current tab
 */
async function verifyText(text, tab) {
  const apiUrl = await getApiUrl();
  
  // Check for embedded signature
  const signatureMatch = text.match(/\[ORIGINMARK:([^\]]+)\]/);
  
  if (!signatureMatch) {
    showNotification({
      valid: false,
      message: 'No OriginMark signature found in text'
    });
    return;
  }
  
  const signatureId = signatureMatch[1];
  
  // Get signature details from API
  const response = await fetch(`${apiUrl}/signatures/${signatureId}`);
  
  if (!response.ok) {
    showNotification({
      valid: false,
      message: 'Signature not found in database'
    });
    return;
  }
  
  const data = await response.json();
  
  // Create text blob for verification
  const blob = new Blob([text], { type: 'text/plain' });
  const formData = new FormData();
  formData.append('file', blob, 'text.txt');
  formData.append('signature_id', signatureId);
  
  // Verify
  const verifyResponse = await fetch(`${apiUrl}/verify`, {
    method: 'POST',
    body: formData
  });
  
  const result = await verifyResponse.json();
  
  // Broadcast result and show notification
  chrome.runtime.sendMessage({
    action: 'verificationResult',
    result
  }).catch(() => {});
  
  showNotification(result);
}

/**
 * Extract signature ID from URL
 * @param {string} url - URL to parse
 * @returns {string|null} Signature ID or null
 */
function extractSignatureId(url) {
  try {
    const urlParams = new URL(url).searchParams;
    return urlParams.get('originmark_id');
  } catch {
    return null;
  }
}

// ============================================================================
// NOTIFICATION SYSTEM
// ============================================================================

/**
 * Show browser notification
 * @param {Object} result - Verification result
 * @param {Object} options - Notification options
 */
function showNotification(result, options = {}) {
  const title = result.valid ? '✓ Verified AI Content' : '✗ Verification Failed';
  let message = result.valid 
    ? `Verified by ${result.metadata?.author || 'Unknown'}`
    : result.message || 'Content could not be verified';
  
  // Add model information if available
  if (result.valid && result.metadata?.model_used) {
    message += ` • ${result.metadata.model_used}`;
  }
  
  const notificationId = `originmark_${Date.now()}`;
  
  chrome.notifications.create(notificationId, {
    type: 'basic',
    iconUrl: 'icons/icon48.png',
    title,
    message,
    priority: result.valid ? 1 : 2,
    requireInteraction: options.requireInteraction || false
  });
  
  // Auto-clear notification after timeout
  if (!options.requireInteraction) {
    setTimeout(() => {
      chrome.notifications.clear(notificationId);
    }, NOTIFICATION_TIMEOUT);
  }
  
  // Store notification event for analytics
  storeNotificationEvent(result, options);
}

/**
 * Show silent notification for auto-detected signatures
 * @param {Object} result - Verification result
 */
async function showSilentNotification(result) {
  const { autoNotify, silentMode } = await chrome.storage.sync.get(['autoNotify', 'silentMode']);
  
  if (autoNotify !== false && !silentMode) {
    showNotification(result, { requireInteraction: false });
  }
}

/**
 * Show summary notification for page scan
 * @param {number} detectedCount - Number of detected signatures
 * @param {number} verifiedCount - Number of verified signatures
 */
function showSummaryNotification(detectedCount, verifiedCount) {
  if (detectedCount === 0) return;
  
  chrome.notifications.create(`summary_${Date.now()}`, {
    type: 'basic',
    iconUrl: 'icons/icon48.png',
    title: 'OriginMark Summary',
    message: `Found ${detectedCount} signatures on this page • ${verifiedCount} verified`,
    priority: 0
  });
}

/**
 * Show detection notification
 * @param {number} count - Number of detected signatures
 * @param {string} url - Page URL
 */
function showDetectionNotification(count, url) {
  const domain = new URL(url).hostname;
  
  chrome.notifications.create(`detection_${Date.now()}`, {
    type: 'basic',
    iconUrl: 'icons/icon48.png',
    title: '🔍 OriginMark Signatures Detected',
    message: `Found ${count} signature${count > 1 ? 's' : ''} on ${domain}`,
    priority: 1
  });
}

/**
 * Store notification events for analytics
 * @param {Object} result - Verification result
 * @param {Object} options - Notification options
 */
async function storeNotificationEvent(result, options) {
  const event = {
    timestamp: Date.now(),
    type: result.valid ? 'verified' : 'failed',
    auto: options.auto || false,
    author: result.metadata?.author,
    model: result.metadata?.model_used
  };
  
  const { notificationEvents = [] } = await chrome.storage.local.get(['notificationEvents']);
  
  notificationEvents.push(event);
  
  // Keep only last N events
  if (notificationEvents.length > MAX_STORED_EVENTS) {
    notificationEvents.splice(0, notificationEvents.length - MAX_STORED_EVENTS);
  }
  
  await chrome.storage.local.set({ notificationEvents });
}

// ============================================================================
// PAGE MONITORING
// ============================================================================

chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
  if (changeInfo.status !== 'complete' || !tab.url) return;
  
  // Check if auto-detection is enabled
  const { autoDetect } = await chrome.storage.sync.get(['autoDetect']);
  
  if (autoDetect !== false) {
    setTimeout(() => {
      checkPageForSignatures(tabId, tab);
    }, PAGE_SCAN_DELAY);
  }
});

/**
 * Check page for OriginMark signatures
 * @param {number} tabId - Tab ID
 * @param {chrome.tabs.Tab} tab - Tab object
 */
async function checkPageForSignatures(tabId, tab) {
  try {
    const results = await chrome.tabs.sendMessage(tabId, { action: 'scanForSignatures' });
    
    if (!results?.signatures?.length) return;
    
    pageSignatures.set(tabId, results.signatures);
    
    // Check if auto-verify is enabled
    const { autoVerify } = await chrome.storage.sync.get(['autoVerify']);
    
    if (autoVerify) {
      let verifiedCount = 0;
      
      for (const signature of results.signatures) {
        try {
          await verifySignatureAutomatic(signature, tabId);
          verifiedCount++;
        } catch (error) {
          console.log('Auto-verification failed for signature:', signature);
        }
      }
      
      setTimeout(() => {
        showSummaryNotification(results.signatures.length, verifiedCount);
      }, 1000);
    } else {
      showDetectionNotification(results.signatures.length, tab.url);
    }
  } catch (error) {
    // Content script not available or page doesn't support it
    console.log('Could not scan page for signatures:', error.message);
  }
}

/**
 * Auto-verify signature without user interaction
 * @param {string} signatureId - Signature ID
 * @param {number} tabId - Tab ID
 */
async function verifySignatureAutomatic(signatureId, tabId) {
  const apiUrl = await getApiUrl();
  
  const response = await fetch(`${apiUrl}/signatures/${signatureId}`);
  
  if (!response.ok) {
    throw new Error('Signature not found');
  }
  
  const data = await response.json();
  
  showSilentNotification({
    valid: true,
    metadata: data.metadata,
    signature_id: signatureId
  });
  
  return data;
}

// ============================================================================
// MESSAGE HANDLING
// ============================================================================

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  // Handle async responses
  const handleAsync = async () => {
    try {
      switch (request.action) {
        case 'verifyContent':
          await verifyText(request.content, sender.tab);
          return { success: true };
          
        case 'signatureDetected': {
          const { signatureId } = request;
          const { autoNotify } = await chrome.storage.sync.get(['autoNotify']);
          
          if (autoNotify !== false) {
            try {
              const data = await verifySignatureAutomatic(signatureId, sender.tab?.id);
              showSilentNotification({
                valid: true,
                metadata: data.metadata,
                signature_id: signatureId
              });
            } catch (error) {
              console.log('Auto-verification failed:', error);
            }
          }
          return { received: true };
        }
        
        default:
          return { error: 'Unknown action' };
      }
    } catch (error) {
      return { success: false, error: error.message };
    }
  };
  
  handleAsync().then(sendResponse);
  return true; // Keep message channel open for async response
});