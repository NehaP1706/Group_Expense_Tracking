class ChatbotWidget {
    constructor(userId) {
        this.userId = userId;
        this.isSending = false;
        
        // distinct check to ensure we don't render twice
        if (document.getElementById('chatbotWidget')) return;
        
        this.init();
    }

    init() {
        this.renderWidget();
        this.attachEvents();
        // explicit timeout to ensure DOM is painted before we try to scroll or add messages
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
                            <h3 class="chatbot-title">Expense Assistant</h3>
                        </div>
                        <button class="chatbot-close" id="chatbotClose">
                            <svg viewBox="0 0 24 24" width="18" height="18" fill="white"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
                        </button>
                    </div>
                    
                    <div class="chatbot-messages" id="chatbotMessages">
                        </div>

                    <div class="chatbot-input-area">
                        <div class="chatbot-input-container">
                            <textarea class="chatbot-input" id="chatbotInput" placeholder="Type here..." rows="1"></textarea>
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
        
        if(input) input.onkeydown = (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        };
    }

    async loadHistory() {
        const container = document.getElementById('chatbotMessages');
        if (!container) return;

        try {
            const res = await fetch(`/api/chatbot/history?userId=${this.userId}`);
            const data = await res.json();
            
            container.innerHTML = '';
            
            // If API returns array, reverse it so oldest is top
            const history = Array.isArray(data) ? data.reverse() : [];
            
            if (history.length === 0) {
                this.addMessage('bot', "Hi! I'm your Expense Assistant. I can help you create groups or split bills.");
            } else {
                history.forEach(msg => this.addMessage(msg.sender, msg.message));
            }
        } catch (err) {
            console.error(err);
            container.innerHTML = '<div style="padding:20px; text-align:center; color:#999;">Welcome! Start a conversation.</div>';
        }
    }

    async sendMessage() {
        const input = document.getElementById('chatbotInput');
        if (!input || this.isSending) return;

        const text = input.value.trim();
        if (!text) return;

        this.isSending = true;
        input.value = '';
        this.addMessage('user', text);
        
        // Show typing indicator
        this.toggleTyping(true);

        try {
            const res = await fetch('/api/chatbot/send', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ userId: this.userId, message: text })
            });
            const data = await res.json();
            
            this.toggleTyping(false); // Hide typing
            
            if (data.error) {
                this.addMessage('bot', "Error: " + data.error);
            } else {
                this.addMessage('bot', data.reply);
            }
        } catch (err) {
            this.toggleTyping(false);
            this.addMessage('bot', "Sorry, I couldn't reach the server.");
        } finally {
            this.isSending = false;
        }
    }

    addMessage(sender, text) {
        const container = document.getElementById('chatbotMessages');
        if (!container) return;

        const div = document.createElement('div');
        div.className = `chatbot-message ${sender}`;
        
        // Simple avatar logic
        const avatarHtml = sender === 'bot' 
            ? '<div class="message-avatar bot"><svg viewBox="0 0 24 24" width="16" height="16" fill="white"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-5-9h10v2H7z"/></svg></div>'
            : '<div class="message-avatar user"><svg viewBox="0 0 24 24" width="16" height="16" fill="#666"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg></div>';

        div.innerHTML = `
            ${sender === 'user' ? '' : avatarHtml}
            <div class="message-content">
                <div class="message-bubble">${this.escapeHtml(text)}</div>
            </div>
            ${sender === 'user' ? avatarHtml : ''}
        `;
        
        container.appendChild(div);
        this.scrollToBottom();
    }

    // Fixed: Logic to safely add/remove typing indicator without crashing
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
                    <div class="message-bubble" style="color: #aaa;">...</div>
                </div>
            `;
            container.appendChild(div);
            this.scrollToBottom();
        }
    }

    scrollToBottom() {
        const container = document.getElementById('chatbotMessages');
        if (container) container.scrollTop = container.scrollHeight;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Auto-init on page load
document.addEventListener('DOMContentLoaded', () => {
    // 1. Try to get userId from URL
    const params = new URLSearchParams(window.location.search);
    let userId = params.get('userId');

    // 2. Fallback: If not in URL, check localStorage (persistence fix)
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