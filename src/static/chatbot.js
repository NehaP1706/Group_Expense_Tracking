class ChatbotWidget {
    constructor(userId) {
        this.userId = userId;
        this.isSending = false;
        
        // Prevent duplicate rendering
        if (document.getElementById('chatbotWidget')) return;
        
        this.init();
    }

    init() {
        this.renderWidget();
        this.attachEvents();
        setTimeout(() => this.loadHistory(), 100);
    }

    renderWidget() {
        const html = `
            <div class="chatbot-widget" id="chatbotWidget">
                <button class="chatbot-button" id="chatbotButton">
                    <svg viewBox="0 0 24 24" width="28" height="28" fill="white">
                        <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/>
                    </svg>
                </button>

                <div class="chatbot-window" id="chatbotWindow">
                    <div class="chatbot-header">
                        <div class="chatbot-header-content">
                            <div class="chatbot-avatar">
                                <svg viewBox="0 0 24 24" width="20" height="20" fill="white"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-5-9h10v2H7z"/></svg>
                            </div>
                            <div>
                                <h3 class="chatbot-title">Personal Assistant</h3>
                                <p class="chatbot-status">Online</p>
                            </div>
                        </div>
                        <button class="chatbot-close" id="chatbotClose">
                            <svg viewBox="0 0 24 24" width="18" height="18" fill="white"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
                        </button>
                    </div>
                    
                    <div class="chatbot-messages" id="chatbotMessages"></div>

                    <div class="chatbot-input-area">
                        <div class="chatbot-input-container">
                            <textarea class="chatbot-input" id="chatbotInput" placeholder="Type 'menu' to start..." rows="1"></textarea>
                            <button class="chatbot-send" id="chatbotSend">
                                <svg viewBox="0 0 24 24" width="20" height="20" fill="white"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', html);
    }

    attachEvents() {
        const btn = document.getElementById('chatbotButton');
        const close = document.getElementById('chatbotClose');
        const send = document.getElementById('chatbotSend');
        const input = document.getElementById('chatbotInput');
        const win = document.getElementById('chatbotWindow');

        if(btn) btn.onclick = () => {
            win.classList.add('show');
            btn.classList.add('hidden');
            this.scrollToBottom();
        };

        if(close) close.onclick = () => {
            win.classList.remove('show');
            btn.classList.remove('hidden');
        };

        if(send) send.onclick = () => this.sendMessage();
        
        if(input) {
            input.onkeydown = (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            };
            
            // Auto-resize textarea
            input.oninput = () => {
                input.style.height = 'auto';
                input.style.height = Math.min(input.scrollHeight, 100) + 'px';
            };
        }
    }

    async loadHistory() {
        const container = document.getElementById('chatbotMessages');
        if (!container) return;

        try {
            const res = await fetch(`/api/chatbot/history?userId=${this.userId}`);
            const data = await res.json();
            
            container.innerHTML = '';
            
            // Reverse so oldest is at top
            const history = Array.isArray(data) ? data.reverse() : [];
            
            if (history.length === 0) {
                this.addMessage('bot', "Hello! I'm your Personal Assistant. I can help you around if you so wish for it.\n\nHow may I help you? Choose between one of the below:\n\n1️⃣ General - Chat with me about anything\n2️⃣ Task - Get things done (create groups, plan trips, etc.)");
            } else {
                history.forEach(msg => this.addMessage(msg.sender, msg.message));
            }
        } catch (err) {
            console.error('Error loading history:', err);
            this.addMessage('bot', "Hello! I'm your Personal Assistant. Type 'menu' to get started.");
        }
    }

    async sendMessage() {
        const input = document.getElementById('chatbotInput');
        if (!input || this.isSending) return;

        const text = input.value.trim();
        if (!text) return;

        this.isSending = true;
        input.value = '';
        input.style.height = 'auto';
        this.addMessage('user', text);
        
        this.toggleTyping(true);

        try {
            const res = await fetch('/api/chatbot/send', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ userId: this.userId, message: text })
            });
            const data = await res.json();
            
            this.toggleTyping(false);
            
            if (data.error) {
                this.addMessage('bot', "Error: " + data.error);
            } else {
                this.addMessage('bot', data.reply);
                
                // Handle actions
                if (data.action) {
                    this.handleAction(data.action, data.action_data || data.data);
                }
            }
        } catch (err) {
            console.error('Error sending message:', err);
            this.toggleTyping(false);
            this.addMessage('bot', "Sorry, I couldn't reach the server. Please try again.");
        } finally {
            this.isSending = false;
        }
    }

    handleAction(action, data) {
        switch(action) {
            case 'redirect_trip_planning':
                // Add clickable link in the chat
                setTimeout(() => {
                    if (data.isSolo) {
                        this.addActionButton('Open Trip Planner', () => {
                            window.location.href = `/plan-solo-trip?userId=${data.userId}`;
                        });
                    } else {
                        this.addActionButton('Open Trip Planner', () => {
                            window.location.href = `/plan-group-trip?userId=${data.userId}&groupName=${encodeURIComponent(data.groupName)}`;
                        });
                    }
                }, 500);
                break;
                
            case 'open_receipt_upload':
                setTimeout(() => {
                    this.addActionButton('Upload Receipt', () => {
                        window.open(data.url, '_blank', 'width=500,height=600');
                    });
                }, 500);
                break;
                
            case 'create_trip':
                // This would trigger the actual trip creation API call
                console.log('Create trip:', data);
                break;
        }
    }

    addActionButton(text, onclick) {
        const container = document.getElementById('chatbotMessages');
        if (!container) return;

        const div = document.createElement('div');
        div.className = 'chatbot-message bot';
        div.innerHTML = `
            <div class="message-avatar bot">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="white">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-5-9h10v2H7z"/>
                </svg>
            </div>
            <div class="message-content">
                <button style="
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 20px;
                    cursor: pointer;
                    font-weight: 600;
                    font-size: 14px;
                    box-shadow: 0 2px 8px rgba(102, 126, 234, 0.4);
                    transition: all 0.2s;
                " onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                    ${this.escapeHtml(text)} →
                </button>
            </div>
        `;
        
        const button = div.querySelector('button');
        if (button) button.onclick = onclick;
        
        container.appendChild(div);
        this.scrollToBottom();
    }

    addMessage(sender, text) {
        const container = document.getElementById('chatbotMessages');
        if (!container) return;

        const div = document.createElement('div');
        div.className = `chatbot-message ${sender}`;
        
        const avatarHtml = sender === 'bot' 
            ? '<div class="message-avatar bot"><svg viewBox="0 0 24 24" width="16" height="16" fill="white"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-5-9h10v2H7z"/></svg></div>'
            : '<div class="message-avatar user"><svg viewBox="0 0 24 24" width="16" height="16" fill="#666"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg></div>';

        // Format text with line breaks
        const formattedText = this.formatMessage(text);

        div.innerHTML = `
            ${sender === 'user' ? '' : avatarHtml}
            <div class="message-content">
                <div class="message-bubble">${formattedText}</div>
            </div>
            ${sender === 'user' ? avatarHtml : ''}
        `;
        
        container.appendChild(div);
        this.scrollToBottom();
    }

    formatMessage(text) {
        // Convert newlines to <br> and preserve formatting
        return this.escapeHtml(text)
            .replace(/\n/g, '<br>')
            .replace(/•/g, '•')
            .replace(/(\d+)️⃣/g, '$1️⃣')
            .replace(/✅/g, '<span style="color: #28a745;">✅</span>')
            .replace(/❌/g, '<span style="color: #e74c3c;">❌</span>')
            .replace(/📋/g, '<span style="font-size: 1.1em;">📋</span>')
            .replace(/✈️/g, '<span style="font-size: 1.1em;">✈️</span>');
    }

    toggleTyping(show) {
        const container = document.getElementById('chatbotMessages');
        if (!container) return;

        const existing = document.getElementById('typing-indicator');
        if (existing) existing.remove();

        if (show) {
            const div = document.createElement('div');
            div.id = 'typing-indicator';
            div.className = 'chatbot-message bot';
            div.innerHTML = `
                <div class="message-avatar bot"><svg viewBox="0 0 24 24" width="16" height="16" fill="white"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-5-9h10v2H7z"/></svg></div>
                <div class="message-content">
                    <div class="typing-indicator show">
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                    </div>
                </div>
            `;
            container.appendChild(div);
            this.scrollToBottom();
        }
    }

    scrollToBottom() {
        const container = document.getElementById('chatbotMessages');
        if (container) {
            setTimeout(() => {
                container.scrollTop = container.scrollHeight;
            }, 100);
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Auto-init on page load
document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    let userId = params.get('userId');

    if (userId) {
        localStorage.setItem('expense_userId', userId);
    } else {
        userId = localStorage.getItem('expense_userId');
    }

    if (userId) {
        new ChatbotWidget(userId);
    } else {
        console.log("Chatbot: No User ID found.");
    }
});