// Firefox compatibility layer
const api = typeof browser !== 'undefined' ? browser : chrome;

// Create context menu on installation
api.runtime.onInstalled.addListener(() => {
  api.contextMenus.create({
    id: 'verifyImage',
    title: 'Verify with OriginMark',
    contexts: ['image']
  });
  
  api.contextMenus.create({
    id: 'verifyText',
    title: 'Verify selected text with OriginMark',
    contexts: ['selection']
  });
});

// Handle context menu clicks
api.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === 'verifyImage') {
    await verifyImage(info.srcUrl, tab);
  } else if (info.menuItemId === 'verifyText') {
    await verifyText(info.selectionText, tab);
  }
});

// Verify image
async function verifyImage(imageUrl, tab) {
  try {
    const settings = await api.storage.sync.get(['apiUrl']);
    const apiUrl = settings.apiUrl || 'http://localhost:8000';
    
    // Fetch image
    const response = await fetch(imageUrl);
    const blob = await response.blob();
    
    // Create form data
    const formData = new FormData();
    formData.append('file', blob, 'image.png');
    
    // Check for signature ID in URL or nearby text
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
    
    // Send result to popup if open
    api.runtime.sendMessage({
      action: 'verificationResult',
      result: result
    });
    
    // Show notification
    showNotification(result);
    
  } catch (error) {
    console.error('Verification error:', error);
    showNotification({
      valid: false,
      message: 'Verification failed: ' + error.message
    });
  }
}

// Verify text
async function verifyText(text, tab) {
  try {
    const settings = await api.storage.sync.get(['apiUrl']);
    const apiUrl = settings.apiUrl || 'http://localhost:8000';
    
    // Check for embedded signature
    const signatureMatch = text.match(/\[ORIGINMARK:([^\]]+)\]/);
    
    if (signatureMatch) {
      const signatureId = signatureMatch[1];
      
      // Get signature details from API
      const response = await fetch(`${apiUrl}/signatures/${signatureId}`);
      
      if (response.ok) {
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
        
        // Send result to popup if open
        api.runtime.sendMessage({
          action: 'verificationResult',
          result: result
        });
        
        // Show notification
        showNotification(result);
      } else {
        showNotification({
          valid: false,
          message: 'Signature not found in database'
        });
      }
    } else {
      showNotification({
        valid: false,
        message: 'No OriginMark signature found in text'
      });
    }
  } catch (error) {
    console.error('Verification error:', error);
    showNotification({
      valid: false,
      message: 'Verification failed: ' + error.message
    });
  }
}

// Extract signature ID from URL or text
function extractSignatureId(url) {
  // Check if URL contains signature ID parameter
  const urlParams = new URL(url).searchParams;
  const signatureId = urlParams.get('originmark_id');
  
  return signatureId;
}

// Enhanced notification system
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
  
  api.notifications.create(notificationId, {
    type: 'basic',
    iconUrl: result.valid ? 'icons/icon48.png' : 'icons/icon48.png',
    title: title,
    message: message
  });
  
  // Auto-clear notification after 5 seconds
  setTimeout(() => {
    api.notifications.clear(notificationId);
  }, 5000);
  
  // Store notification for analytics
  storeNotificationEvent(result, options);
}

// Show silent notification for auto-detected signatures
function showSilentNotification(result) {
  api.storage.sync.get(['autoNotify', 'silentMode']).then((settings) => {
    if (settings.autoNotify !== false && !settings.silentMode) {
      showNotification(result, { requireInteraction: false });
    }
  });
}

// Store notification events for analytics
function storeNotificationEvent(result, options) {
  const event = {
    timestamp: Date.now(),
    type: result.valid ? 'verified' : 'failed',
    auto: options.auto || false,
    author: result.metadata?.author,
    model: result.metadata?.model_used
  };
  
  api.storage.local.get(['notificationEvents']).then((data) => {
    const events = data.notificationEvents || [];
    events.push(event);
    
    // Keep only last 100 events
    if (events.length > 100) {
      events.splice(0, events.length - 100);
    }
    
    api.storage.local.set({ notificationEvents: events });
  });
}

// Page monitoring for automatic notifications
let pageSignatures = new Map();

// Monitor tab updates for automatic detection
api.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab.url) {
    const settings = await api.storage.sync.get(['autoDetect', 'autoNotify']);
    if (settings.autoDetect !== false) {
      setTimeout(() => {
        checkPageForSignatures(tabId, tab);
      }, 2000);
    }
  }
});

// Check page for OriginMark signatures
async function checkPageForSignatures(tabId, tab) {
  try {
    const results = await api.tabs.sendMessage(tabId, { action: 'scanForSignatures' });
    
    if (results && results.signatures && results.signatures.length > 0) {
      pageSignatures.set(tabId, results.signatures);
      
      const settings = await api.storage.sync.get(['autoVerify']);
      if (settings.autoVerify) {
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
    }
  } catch (error) {
    console.log('Could not scan page for signatures:', error.message);
  }
}

// Auto-verify signature without user interaction
async function verifySignatureAutomatic(signatureId, tabId) {
  const settings = await api.storage.sync.get(['apiUrl']);
  const apiUrl = settings.apiUrl || 'http://localhost:8000';
  
  const response = await fetch(`${apiUrl}/signatures/${signatureId}`);
  
  if (response.ok) {
    const data = await response.json();
    
    showSilentNotification({
      valid: true,
      metadata: data.metadata,
      signature_id: signatureId
    });
    
    return data;
  } else {
    throw new Error('Signature not found');
  }
}

// Show notification when signatures are detected
function showDetectionNotification(count, url) {
  const domain = new URL(url).hostname;
  
  api.notifications.create(`detection_${Date.now()}`, {
    type: 'basic',
    iconUrl: 'icons/icon48.png',
    title: '🔍 OriginMark Signatures Detected',
    message: `Found ${count} signature${count > 1 ? 's' : ''} on ${domain}`
  });
}

// Show periodic summary notification
function showSummaryNotification(detectedCount, verifiedCount) {
  if (detectedCount === 0) return;
  
  const title = `OriginMark Summary`;
  const message = `Found ${detectedCount} signatures on this page • ${verifiedCount} verified`;
  
  api.notifications.create(`summary_${Date.now()}`, {
    type: 'basic',
    iconUrl: 'icons/icon48.png',
    title: title,
    message: message
  });
}

// Listen for messages from content script
api.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'verifyContent') {
    verifyText(request.content, sender.tab).then(() => {
      sendResponse({ success: true });
    }).catch(error => {
      sendResponse({ success: false, error: error.message });
    });
    return true;
  }
  
  if (request.action === 'signatureDetected') {
    const { signatureId, auto } = request;
    
    api.storage.sync.get(['autoNotify']).then((settings) => {
      if (settings.autoNotify !== false) {
        verifySignatureAutomatic(signatureId, sender.tab.id)
          .then(data => {
            showSilentNotification({
              valid: true,
              metadata: data.metadata,
              signature_id: signatureId
            });
          })
          .catch(error => {
            console.log('Auto-verification failed:', error);
          });
      }
    });
    
    sendResponse({ received: true });
  }
}); 