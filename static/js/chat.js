document.addEventListener('DOMContentLoaded', function() {
    // Connect to the Socket.IO server
    const socket = io();
    
    // DOM elements
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const chatMessages = document.getElementById('chat-messages');
    const sendButton = document.getElementById('send-button');
    const typingIndicator = document.getElementById('typing-indicator');
    
    // Variable to hold the current message being received
    let currentMessageElement = null;
    let isReceivingMessage = false;
    
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