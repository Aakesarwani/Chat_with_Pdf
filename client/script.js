let currentCollection = null;
let isProcessing = false;

// DOM Elements
const uploadArea = document.getElementById('upload-area');
const fileInput = document.getElementById('file-input');
const uploadSection = document.getElementById('upload-section');
const uploadProgress = document.getElementById('upload-progress');
const progressFill = document.getElementById('progress-fill');
const progressText = document.getElementById('progress-text');
const chatSection = document.getElementById('chat-section');
const chatMessages = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');

// File upload handling
uploadArea.addEventListener('click', () => {
    fileInput.click();
});

uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('dragover');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('dragover');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFileUpload(files[0]);
    }
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFileUpload(e.target.files[0]);
    }
});

// Chat input handling
chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

chatInput.addEventListener('input', () => {
    sendBtn.disabled = !chatInput.value.trim() || isProcessing;
});

// File upload function
async function handleFileUpload(file) {
    if (file.type !== 'application/pdf') {
        showError('Please upload a PDF file only.');
        return;
    }

    if (file.size > 16 * 1024 * 1024) {
        showError('File size must be less than 16MB.');
        return;
    }

    // Start progress polling (loader will show when backend starts processing)
    startProgressPolling();

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (response.ok) {
            showSuccess(`Document indexed successfully! ${result.chunks_count} chunks processed.`);
            if (result.note) {
                showNotification(result.note, 'info');
            }
            // Show chat interface immediately after success
            showChatInterface();
            currentCollection = result.collection_name;
        } else {
            if (result.quota_error) {
                showError('API quota exceeded. Please try again later or upgrade your API plan.');
            } else {
                showError(result.error || 'Upload failed');
            }
        }
    } catch (error) {
        showError('Network error. Please try again.');
        console.error('Upload error:', error);
    } finally {
        hideProgress();
        stopProgressPolling();
    }
}

// Progress tracking
let progressInterval;
let lastProgress = null;

function startProgressPolling() {
    progressInterval = setInterval(async () => {
        try {
            const response = await fetch('/api/progress');
            const progress = await response.json();
            
            // Show loader when we get first progress update
            if (progress.status && progress.status !== 'idle') {
                const uploadProgress = document.getElementById('upload-progress');
                if (uploadProgress && !uploadProgress.classList.contains('show')) {
                    uploadProgress.classList.add('show');
                }
            }
            
            // Only update UI if progress actually changed
            if (JSON.stringify(progress) !== JSON.stringify(lastProgress)) {
                updateProgressUI(progress);
                lastProgress = progress;
            }
        } catch (error) {
            console.error('Progress polling error:', error);
        }
    }, 500); // Poll every 500ms
}

function stopProgressPolling() {
    if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
    }
}

function updateProgressUI(progress) {
    console.log('Progress update:', progress);
    
    if (progress.status === 'error') {
        showError(progress.message);
        hideProgress();
        stopProgressPolling();
        return;
    }
    
    if (progress.status === 'completed') {
        showSuccess(progress.message);
        // Mark all stages as completed
        updateStages(['upload', 'process', 'index', 'complete']);
        // Don't hide progress or stop polling here - let the main upload handler do it
        return;
    }
    
    // Update progress bar and text
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    const progressSubtext = document.getElementById('progress-subtext');
    
    if (progressFill && progressText && progressSubtext) {
        progressFill.style.width = `${progress.progress}%`;
        progressText.textContent = progress.message || `Processing... ${progress.progress}%`;
        
        // Update subtext based on progress
        if (progress.progress < 25) {
            progressSubtext.textContent = 'Uploading your document...';
            updateStages(['upload']);
        } else if (progress.progress < 50) {
            progressSubtext.textContent = 'Extracting text from PDF...';
            updateStages(['upload', 'process']);
        } else if (progress.progress < 80) {
            progressSubtext.textContent = 'Creating vector embeddings...';
            updateStages(['upload', 'process', 'index']);
        } else if (progress.progress < 100) {
            progressSubtext.textContent = 'Finalizing and indexing...';
            updateStages(['upload', 'process', 'index']);
        }
    }
}

function updateStages(activeStages) {
    const allStages = ['upload', 'process', 'index', 'complete'];
    
    allStages.forEach((stage, index) => {
        const stageElement = document.getElementById(`stage-${stage}`);
        if (stageElement) {
            stageElement.classList.remove('active', 'completed');
            
            if (activeStages.includes(stage)) {
                if (stage === 'complete' && activeStages.length === 4) {
                    stageElement.classList.add('completed');
                } else {
                    stageElement.classList.add('active');
                }
            } else if (index < activeStages.length) {
                stageElement.classList.add('completed');
            }
        }
    });
}

function showProgress() {
    uploadSection.style.display = 'none';
    uploadProgress.style.display = 'block';
    
    // Reset all stages
    updateStages([]);
    
    // Set initial text
    const progressText = document.getElementById('progress-text');
    const progressSubtext = document.getElementById('progress-subtext');
    const progressFill = document.getElementById('progress-fill');
    
    if (progressText) progressText.textContent = 'Preparing to upload...';
    if (progressSubtext) progressSubtext.textContent = 'Please wait while we process your document';
    if (progressFill) progressFill.style.width = '0%';
}

function hideProgress() {
    if (window.progressInterval) {
        clearInterval(window.progressInterval);
    }
    const uploadProgress = document.getElementById('upload-progress');
    if (uploadProgress) {
        uploadProgress.classList.remove('show');
    }
    const progressFill = document.getElementById('progress-fill');
    if (progressFill) progressFill.style.width = '0%';
}

// Chat interface
function showChatInterface() {
    console.log('Showing chat interface...');
    hideProgress();
    stopProgressPolling();
    
    // Hide upload section completely
    uploadSection.style.display = 'none';
    
    // Show chat section
    chatSection.style.display = 'flex';
    chatSection.classList.add('active');
    
    // Enable chat input
    chatInput.disabled = false;
    sendBtn.disabled = false;
    chatInput.focus();
    
    console.log('Chat interface shown successfully');
    console.log('Chat section display:', chatSection.style.display);
    console.log('Upload section display:', uploadSection.style.display);
}

function resetChat() {
    currentCollection = null;
    chatMessages.innerHTML = `
        <div class="welcome-message">
            <p>👋 Hello! Ask me anything about the document you just uploaded.</p>
        </div>
    `;
    chatSection.style.display = 'none';
    chatSection.classList.remove('active');
    uploadSection.style.display = 'block';
    chatInput.value = '';
    fileInput.value = '';
    chatInput.disabled = true;
    sendBtn.disabled = true;
}

// Message handling
async function sendMessage() {
    const query = chatInput.value.trim();
    if (!query || !currentCollection || isProcessing) return;

    isProcessing = true;
    sendBtn.disabled = true;
    chatInput.disabled = true;

    // Add user message
    addMessage(query, 'user');
    chatInput.value = '';

    // Add loading indicator
    const loadingId = addMessage('Thinking...', 'assistant', true);

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                collection_name: currentCollection
            })
        });

        const result = await response.json();

        // Remove loading indicator
        removeMessage(loadingId);

        if (response.ok) {
            addMessage(result.answer, 'assistant', false, result.sources);
        } else {
            addMessage(`Error: ${result.error}`, 'assistant');
        }
    } catch (error) {
        removeMessage(loadingId);
        addMessage('Network error. Please try again.', 'assistant');
        console.error('Chat error:', error);
    } finally {
        isProcessing = false;
        sendBtn.disabled = false;
        chatInput.disabled = false;
        chatInput.focus();
    }
}

function addMessage(content, sender, isLoading = false, sources = null) {
    const messageId = 'msg-' + Date.now();
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    messageDiv.id = messageId;
    
    let messageHTML = `<div class="message-content">`;
    
    if (isLoading) {
        messageHTML += '<div class="loading"></div> Thinking...';
    } else {
        messageHTML += content;
    }
    
    messageHTML += '</div>';
    
    if (sources && sources.length > 0) {
        messageHTML += `
            <div class="message-sources">
                <strong>Sources:</strong>
                ${sources.map(source => `
                    <div class="source-item">
                        📄 Page ${source.page}: ${source.content}
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    messageDiv.innerHTML = messageHTML;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    return messageId;
}

function removeMessage(messageId) {
    const message = document.getElementById(messageId);
    if (message) {
        message.remove();
    }
}

// Notification functions
function showError(message) {
    hideProgress();
    stopProgressPolling();
    showNotification('❌ Error: ' + message, 'error');
}

function showSuccess(message) {
    showNotification('✅ ' + message, 'success');
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    // Add styles
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        border-radius: 8px;
        color: white;
        font-weight: 500;
        z-index: 1000;
        max-width: 400px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        transform: translateX(100%);
        transition: transform 0.3s ease;
    `;
    
    // Set background color based on type
    if (type === 'error') {
        notification.style.backgroundColor = '#e74c3c';
    } else if (type === 'success') {
        notification.style.backgroundColor = '#27ae60';
    } else {
        notification.style.backgroundColor = '#3498db';
    }
    
    // Add to page
    document.body.appendChild(notification);
    
    // Animate in
    setTimeout(() => {
        notification.style.transform = 'translateX(0)';
    }, 100);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 3000);
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Check if there's an existing session
    chatInput.disabled = true;
    sendBtn.disabled = true;
});
