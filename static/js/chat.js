document.addEventListener('DOMContentLoaded', function() {
    // Connect to the Socket.IO server
    const socket = io();
    
    // DOM elements
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const chatMessages = document.getElementById('chat-messages');
    const sendButton = document.getElementById('send-button');
    const typingIndicator = document.getElementById('typing-indicator');
    const threadSelector = document.getElementById('thread-selector');
    
    // Variable to hold the current message being received
    let currentMessageElement = null;
    let isReceivingMessage = false;
    
    // Fetch available threads
    function fetchThreads() {
        fetch('/api/threads')
            .then(response => response.json())
            .then(data => {
                if (data.threads && data.threads.length > 0) {
                    // Clear existing options except the first one (current thread)
                    while (threadSelector.options.length > 1) {
                        threadSelector.remove(1);
                    }
                    
                    // Add thread options
                    data.threads.forEach(thread => {
                        // Skip the current thread as it's already in the dropdown
                        if (!thread.is_current) {
                            const option = document.createElement('option');
                            option.value = thread.id;
                            const truncatedId = thread.id.substring(0, 8);
                            const formattedDate = thread.timestamp ? new Date(thread.timestamp).toLocaleString() : 'Unknown';
                            option.textContent = `Thread ${truncatedId}... (${thread.message_count} msgs, ${formattedDate})`;
                            threadSelector.appendChild(option);
                        }
                    });
                }
            })
            .catch(error => console.error('Error fetching threads:', error));
    }
    
    // Handle thread selection
    threadSelector.addEventListener('change', function() {
        const selectedThreadId = this.value;
        if (selectedThreadId) {
            window.location.href = `/switch_thread/${selectedThreadId}`;
        }
    });
    
    // Fetch threads when the page loads
    fetchThreads();
    
    // Handle form submission
    chatForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const message = userInput.value.trim();
        if (message === '') return;
        
        // Disable the input and button while processing
        userInput.disabled = true;
        sendButton.disabled = true;
        
        // Add the user's message to the chat
        addMessageToChat('user', message);
        
        // Clear the input field
        userInput.value = '';
        
        // Show typing indicator
        typingIndicator.style.display = 'flex';
        
        // Send the message to the server
        socket.emit('send_message', { message: message });
    });
    
    // Listen for the start of a response
    socket.on('response_start', function() {
        // Create a new message element for the assistant's response
        currentMessageElement = document.createElement('div');
        currentMessageElement.className = 'message assistant';
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        const paragraph = document.createElement('p');
        messageContent.appendChild(paragraph);
        
        currentMessageElement.appendChild(messageContent);
        chatMessages.appendChild(currentMessageElement);
        
        isReceivingMessage = true;
        
        // Hide typing indicator
        typingIndicator.style.display = 'none';
    });
    
    // Listen for message chunks
    socket.on('response_chunk', function(data) {
        if (currentMessageElement) {
            const paragraph = currentMessageElement.querySelector('p');
            
            // Append the text chunk
            paragraph.innerHTML = paragraph.innerHTML + data.chunk;
            
            // Scroll to the bottom
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    });
    
    // Listen for the end of a response
    socket.on('response_end', function() {
        // Re-enable the input and button
        userInput.disabled = false;
        sendButton.disabled = false;
        
        isReceivingMessage = false;
        currentMessageElement = null;
        
        // Focus on the input field
        userInput.focus();
        
        // Refresh thread list after a completed conversation
        fetchThreads();
    });
    
    // Function to add a message to the chat
    function addMessageToChat(role, text) {
        const messageElement = document.createElement('div');
        messageElement.className = `message ${role}`;
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        const paragraph = document.createElement('p');
        paragraph.textContent = text;
        messageContent.appendChild(paragraph);
        
        messageElement.appendChild(messageContent);
        chatMessages.appendChild(messageElement);
        
        // Scroll to the bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Enable pressing Enter to send a message
    userInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            chatForm.dispatchEvent(new Event('submit'));
        }
    });
    
    // Auto-resize the textarea as the user types
    userInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });
}); 