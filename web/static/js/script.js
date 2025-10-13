        document.addEventListener('DOMContentLoaded', () => {
            // Elements
            const sidebar = document.getElementById('sidebar');
            const toggleBtn = document.getElementById('toggle-sidebar');
            const newChatBtn = document.getElementById('new-chat-btn');
            const conversationsList = document.getElementById('conversations-list');
            const chatContainer = document.getElementById('chat-container');
            const chatForm = document.getElementById('chat-form');
            const chatInput = document.getElementById('chat-input');
            const sendBtn = document.getElementById('send-btn');
            const modal = document.getElementById('preview-modal');
            const closeModal = document.getElementById('close-modal');
            const runnerFrame = document.getElementById('runner-frame');

            let currentConversationId = null;

            // Markdown
            const md = window.markdownit({
                highlight: (str, lang) => {
                    if (lang && hljs.getLanguage(lang)) {
                        try {
                            return hljs.highlight(str, { language: lang }).value;
                        } catch (__) {}
                    }
                    return md.utils.escapeHtml(str);
                }
            });

            // Toggle sidebar
            toggleBtn.addEventListener('click', () => {
                sidebar.classList.toggle('collapsed');
            });

            // New chat
            newChatBtn.addEventListener('click', () => {
                currentConversationId = null;
                chatContainer.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">💬</div>
                        <h2>Nueva conversación</h2>
                        <p>Escribe tu primer mensaje</p>
                    </div>
                `;
                document.querySelectorAll('.conversation-item').forEach(el => {
                    el.classList.remove('active');
                });
            });

            // Load conversations
            async function loadConversations() {
                try {
                    const res = await fetch('/api/conversations');
                    const data = await res.json();
                    displayConversations(data.conversations);
                } catch (err) {
                    console.error('Error cargando conversaciones:', err);
                }
            }

            function displayConversations(conversations) {
                conversationsList.innerHTML = conversations.map(conv => `
                    <div class="conversation-item" data-id="${conv._id}">
                        <span class="conversation-title">${conv.title}</span>
                        <button class="delete-btn" data-id="${conv._id}">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <polyline points="3 6 5 6 21 6"></polyline>
                                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                            </svg>
                        </button>
                    </div>
                `).join('');

                // Event listeners
                document.querySelectorAll('.conversation-item').forEach(item => {
                    item.addEventListener('click', (e) => {
                        if (!e.target.closest('.delete-btn')) {
                            loadConversation(item.dataset.id);
                        }
                    });
                });

                document.querySelectorAll('.delete-btn').forEach(btn => {
                    btn.addEventListener('click', async (e) => {
                        e.stopPropagation();
                        if (confirm('¿Eliminar esta conversación?')) {
                            await deleteConversation(btn.dataset.id);
                        }
                    });
                });
            }

            async function loadConversation(id) {
                try {
                    const res = await fetch(`/api/conversations/${id}`);
                    const conv = await res.json();
                    
                    currentConversationId = id;
                    chatContainer.innerHTML = '';

                    conv.messages.forEach(msg => {
                        appendMessage(msg.content, msg.role);
                    });

                    document.querySelectorAll('.conversation-item').forEach(el => {
                        el.classList.toggle('active', el.dataset.id === id);
                    });
                } catch (err) {
                    console.error('Error cargando conversación:', err);
                }
            }

            async function deleteConversation(id) {
                try {
                    await fetch(`/api/conversations/${id}`, { method: 'DELETE' });
                    if (currentConversationId === id) {
                        newChatBtn.click();
                    }
                    loadConversations();
                } catch (err) {
                    console.error('Error eliminando:', err);
                }
            }

            // Send message
            chatForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const message = chatInput.value.trim();
                if (!message) return;

                chatInput.value = '';
                sendBtn.disabled = true;

                // Clear empty state
                if (chatContainer.querySelector('.empty-state')) {
                    chatContainer.innerHTML = '';
                }

                appendMessage(message, 'user');
                appendMessage('<div class="typing-indicator"><span></span><span></span><span></span></div>', 'bot', true);

                try {
                    const res = await fetch('/api/generate', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            prompt: message,
                            conversation_id: currentConversationId
                        })
                    });

                    const data = await res.json();
                    
                    if (!currentConversationId) {
                        currentConversationId = data.conversation_id;
                        loadConversations();
                    }

                    updateLastBotMessage(data.response);
                } catch (err) {
                    updateLastBotMessage('Error: No se pudo obtener respuesta.');
                    console.error(err);
                } finally {
                    sendBtn.disabled = false;
                    chatInput.focus();
                }
            });

            function appendMessage(text, role, isTyping = false) {
                const msgGroup = document.createElement('div');
                msgGroup.className = `message-group ${role}-message`;
                
                const header = document.createElement('div');
                header.className = 'message-header';
                header.textContent = role === 'user' ? 'Tú' : 'Web Dev AI';
                
                const content = document.createElement('div');
                content.className = 'message-content';
                
                if (isTyping) {
                    content.innerHTML = text;
                    msgGroup.id = 'typing-msg';
                } else if (role === 'bot') {
                    content.innerHTML = md.render(text);
                } else {
                    content.textContent = text;
                }
                
                msgGroup.appendChild(header);
                msgGroup.appendChild(content);
                chatContainer.appendChild(msgGroup);
                chatContainer.scrollTop = chatContainer.scrollHeight;

                if (role === 'bot' && !isTyping) {
                    addPreviewButton(content);
                }
            }

            function updateLastBotMessage(text) {
                const typing = document.getElementById('typing-msg');
                if (typing) {
                    const content = typing.querySelector('.message-content');
                    content.innerHTML = md.render(text);
                    typing.removeAttribute('id');
                    addPreviewButton(content);
                }
            }

            function addPreviewButton(content) {
                const codeBlock = content.querySelector('code.language-html, code.html');
                if (codeBlock) {
                    const btn = document.createElement('button');
                    btn.className = 'preview-btn';
                    btn.innerHTML = `
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polygon points="23 7 16 12 23 17 23 7"></polygon>
                            <polygon points="14 7 7 12 14 17 14 7"></polygon>
                        </svg>
                        Ver vista previa
                    `;
                    btn.onclick = () => {
                        runnerFrame.srcdoc = codeBlock.textContent;
                        modal.classList.add('show');
                    };
                    content.appendChild(btn);
                }
            }

            // Modal
            closeModal.addEventListener('click', () => {
                modal.classList.remove('show');
                runnerFrame.srcdoc = '';
            });

            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    closeModal.click();
                }
            });

            // Init
            loadConversations();
        });