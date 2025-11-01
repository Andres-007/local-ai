document.addEventListener('DOMContentLoaded', () => {
    const setRealViewportHeight = () => {
        document.documentElement.style.setProperty('--vh', `${window.innerHeight * 0.01}px`);
    };
    window.addEventListener('resize', setRealViewportHeight);
    setRealViewportHeight();

    const sidebar = document.getElementById('sidebar');
    const toggleBtn = document.getElementById('toggle-sidebar');
    const newChatBtn = document.getElementById('new-chat-btn');
    const conversationsList = document.getElementById('conversations-list');
    const chatContainer = document.getElementById('chat-container');
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const sidebarOverlay = document.getElementById('sidebar-overlay');
    const previewModal = document.getElementById('preview-modal');
    const closeModalBtn = document.getElementById('close-modal');
    const runnerFrame = document.getElementById('runner-frame');
    const deleteModal = document.getElementById('delete-confirm-modal');
    const cancelDeleteBtn = document.getElementById('cancel-delete-btn');
    const confirmDeleteBtn = document.getElementById('confirm-delete-btn');

    let currentConversationId = null;
    let conversationToDeleteId = null;
    let currentPreviewCode = '';
    
    // Se ha modificado el inicializador de markdown-it
    const md = window.markdownit({
        highlight: (str, lang) => {
            if (lang && hljs.getLanguage(lang)) {
                try {
                    const result = hljs.highlight(str, { language: lang, ignoreIllegals: true });
                    // Se añade la clase del lenguaje al tag <code> para que el selector funcione
                    return `<pre class="hljs"><code class="language-${lang}">${result.value}</code></pre>`;
                } catch (__) {
                    // Fallback en caso de error
                    return `<pre class="hljs"><code class="language-${lang}">${md.utils.escapeHtml(str)}</code></pre>`;
                }
            }
            // Si no hay lenguaje, se devuelve como antes
            return `<pre class="hljs"><code>${md.utils.escapeHtml(str)}</code></pre>`;
        }
    });
    // --- FIN DE LA CORRECCIÓN ---

    const openSidebar = () => { sidebar.classList.add('open'); sidebarOverlay.classList.add('active'); };
    const closeSidebar = () => { sidebar.classList.remove('open'); sidebarOverlay.classList.remove('active'); };

    toggleBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        if (window.innerWidth < 768) {
            sidebar.classList.contains('open') ? closeSidebar() : openSidebar();
        } else {
            sidebar.classList.toggle('collapsed');
        }
    });
    sidebarOverlay.addEventListener('click', closeSidebar);

    newChatBtn.addEventListener('click', () => {
        currentConversationId = null;
        chatContainer.innerHTML = `<div class="empty-state"><div class="empty-state-icon">💬</div><h2>¿En qué puedo ayudarte hoy?</h2><p>Puedo ayudarte a crear, depurar y mejorar tu código web</p></div>`;
        document.querySelectorAll('.conversation-item').forEach(el => el.classList.remove('active'));
        if (window.innerWidth < 768) closeSidebar();
    });

    // Helper para fetch que maneja errores de autenticación
    async function fetchApi(url, options = {}) {
        const res = await fetch(url, options);
        if (res.status === 401) {
            window.location.href = '/'; // Redirigir al login
            throw new Error('No autorizado');
        }
        return res;
    }

    async function loadConversations() {
        try {
            const res = await fetchApi('/api/conversations');
            if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
            const data = await res.json();
            displayConversations(data.conversations || []);
        } catch (err) {
            if (err.message !== 'No autorizado') {
                console.error('Error cargando conversaciones:', err);
            }
        }
    }

    function displayConversations(conversations) {
        conversationsList.innerHTML = conversations.map(conv => `
            <div class="conversation-item" data-id="${conv._id}">
                <span class="conversation-title">${conv.title}</span>
                <button class="delete-btn" data-id="${conv._id}"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg></button>
            </div>`).join('');
        
        document.querySelectorAll('.conversation-item').forEach(item => {
            item.addEventListener('click', (e) => !e.target.closest('.delete-btn') && loadConversation(item.dataset.id));
        });
        document.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                conversationToDeleteId = btn.dataset.id;
                deleteModal.classList.add('show');
            });
        });
    }
    
    async function loadConversation(id) {
        try {
            const res = await fetchApi(`/api/conversations/${id}`);
            if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
            const conv = await res.json();
            currentConversationId = id;
            chatContainer.innerHTML = '';
            conv.messages.forEach(msg => appendMessage(msg.content, msg.role));
            document.querySelectorAll('.conversation-item').forEach(el => el.classList.toggle('active', el.dataset.id === id));
            if (window.innerWidth < 768) closeSidebar();
        } catch (err) {
            if (err.message !== 'No autorizado') console.error('Error cargando conversación:', err);
        }
    }
    
    cancelDeleteBtn.addEventListener('click', () => deleteModal.classList.remove('show'));
    confirmDeleteBtn.addEventListener('click', async () => {
        if (!conversationToDeleteId) return;
        try {
            await fetchApi(`/api/conversations/${conversationToDeleteId}`, { method: 'DELETE' });
            if (currentConversationId === conversationToDeleteId) newChatBtn.click();
            loadConversations();
        } catch (err) {
            if (err.message !== 'No autorizado') console.error('Error eliminando:', err);
        } finally {
            deleteModal.classList.remove('show');
            conversationToDeleteId = null;
        }
    });

    chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const message = chatInput.value.trim();
    if (!message) return;
    
    if (chatContainer.querySelector('.empty-state')) {
        chatContainer.innerHTML = '';
    }

    appendMessage(message, 'user');
    const typingIndicator = appendMessage('<div class="typing-indicator"><span></span><span></span><span></span></div>', 'bot', true);
    chatInput.value = '';
    autoResizeTextarea();
    sendBtn.disabled = true;

    try {
        const endpoint = currentConversationId ? '/api/generate-stream' : '/api/generate';
        const res = await fetchApi(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                prompt: message, 
                conversation_id: currentConversationId 
            })
        });

        if (!res.ok) {
            throw new Error(`HTTP error! status: ${res.status}`);
        }

        if (res.headers.get("content-type")?.includes("text/plain")) {
            // Streaming response handling
            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let fullResponse = '';
            const content = typingIndicator.querySelector('.message-content');
            content.innerHTML = '';

            try {
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    
                    const chunk = decoder.decode(value, { stream: true });
                    fullResponse += chunk;
                    
                    // Safely update content and scroll
                    requestAnimationFrame(() => {
                        content.innerHTML = md.render(fullResponse);
                        addPreviewButton(content);
                        chatContainer.scrollTop = chatContainer.scrollHeight;
                    });
                }
                // Final decode to handle any remaining bytes
                const remaining = decoder.decode();
                if (remaining) {
                    fullResponse += remaining;
                    content.innerHTML = md.render(fullResponse);
                    addPreviewButton(content);
                }
            } catch (streamError) {
                console.error('Stream reading error:', streamError);
                throw new Error('Error reading stream response');
            }
        } else {
            // Full JSON response handling
            const data = await res.json();
            if (!currentConversationId && data.conversation_id) {
                currentConversationId = data.conversation_id;
                await loadConversations();
            }
            updateLastBotMessage(data.response, typingIndicator);
        }
    } catch (err) {
        if (err.message !== 'No autorizado') {
            const errorMessage = 'Error: No se pudo obtener respuesta del servidor. Por favor, intente nuevamente.';
            updateLastBotMessage(errorMessage, typingIndicator);
            console.error('Chat error:', err);
        }
    } finally {
        sendBtn.disabled = false;
        chatInput.focus();
    }
});


    function appendMessage(text, role, isTyping = false) {
        const msgGroup = document.createElement('div');
        msgGroup.className = `message-group ${role}-message`;
        msgGroup.innerHTML = `
            <div class="message-header">${role === 'user' ? 'Tú' : 'Web Dev AI'}</div>
            <div class="message-content">${isTyping ? text : (role === 'bot' ? md.render(text) : text.replace(/</g, "&lt;").replace(/>/g, "&gt;"))}</div>
        `;
        chatContainer.appendChild(msgGroup);
        chatContainer.scrollTop = chatContainer.scrollHeight;
        if (role === 'bot' && !isTyping) addPreviewButton(msgGroup.querySelector('.message-content'));
        return msgGroup;
    }

    function updateLastBotMessage(text, element) {
        const content = element.querySelector('.message-content');
        content.innerHTML = md.render(text);
        addPreviewButton(content);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
    
    function addPreviewButton(content) {
        content.querySelectorAll('pre > code').forEach(codeBlock => {
            const preElement = codeBlock.parentElement;
            const container = preElement.parentElement;

            if (container.querySelector('.code-actions')) return;

            const className = codeBlock.className || '';
            const isHTML = className.includes('language-html') || className.includes('html');
            const code = codeBlock.textContent;

            const btnContainer = document.createElement('div');
            btnContainer.className = 'code-actions';

            const copyBtn = document.createElement('button');
            copyBtn.className = 'code-action-btn';
            copyBtn.innerHTML = `
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align: -2px;">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
                Copiar
            `;

            copyBtn.onclick = async () => {
                try {
                    await navigator.clipboard.writeText(code);
                    const oldText = copyBtn.innerHTML;
                    copyBtn.innerHTML = '¡Copiado!';
                    copyBtn.style.opacity = '0.7';
                    setTimeout(() => {
                        copyBtn.innerHTML = oldText;
                        copyBtn.style.opacity = '1';
                    }, 2000);
                } catch (err) {
                    console.error('Error al copiar:', err);
                }
            };
            btnContainer.appendChild(copyBtn);

            if (isHTML) {
                const downloadBtn = document.createElement('button');
                downloadBtn.className = 'code-action-btn';
                downloadBtn.innerHTML = `
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align: -2px;">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                        <polyline points="7 10 12 15 17 10"></polyline>
                        <line x1="12" y1="15" x2="12" y2="3"></line>
                    </svg>
                    Descargar
                `;
                downloadBtn.onclick = () => {
                    try {
                        const blob = new Blob([code], { type: 'text/html' });
                        const a = document.createElement('a');
                        a.href = URL.createObjectURL(blob);
                        a.download = `web-dev-ai-${Date.now()}.html`;
                        a.click();
                        URL.revokeObjectURL(a.href);
                    } catch (err) {
                        console.error('Error al descargar:', err);
                    }
                };
                btnContainer.appendChild(downloadBtn);

                const previewBtn = document.createElement('button');
                previewBtn.className = 'preview-btn';
                previewBtn.innerHTML = `
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align: -3px;">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                        <circle cx="12" cy="12" r="3"></circle>
                    </svg> 
                    Ver vista previa
                `;
                previewBtn.onclick = () => {
                    currentPreviewCode = code;
                    const navigationInterceptorScript = `
                        <script>
                            document.addEventListener('DOMContentLoaded', function() {
                                document.querySelectorAll('a').forEach(link => {
                                    link.addEventListener('click', function(event) {
                                        event.preventDefault(); 
                                        console.log('Navegación de enlace bloqueada en previsualización.');
                                    });
                                });
                                document.querySelectorAll('form').forEach(form => {
                                    form.addEventListener('submit', function(event) {
                                        event.preventDefault();
                                        console.log('Envío de formulario bloqueado en previsualización.');
                                    });
                                });
                            });
                        <\/script>
                    `;

                    if (currentPreviewCode.includes('</body>')) {
                        runnerFrame.srcdoc = currentPreviewCode.replace('</body>', navigationInterceptorScript + '</body>');
                    } else if (currentPreviewCode.includes('</html>')) {
                        runnerFrame.srcdoc = currentPreviewCode.replace('</html>', navigationInterceptorScript + '</html>');
                    } else {
                        runnerFrame.srcdoc = currentPreviewCode + navigationInterceptorScript;
                    }
                    previewModal.classList.add('show');
                };
                btnContainer.appendChild(previewBtn);
            }
            
            container.insertBefore(btnContainer, preElement.nextSibling);
        });
    }

        closeModalBtn.addEventListener('click', () => { 
        previewModal.classList.remove('show'); 
        runnerFrame.srcdoc = ''; 
        currentPreviewCode = ''; 
    });

    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('show');
                if (modal === previewModal) {
                    runnerFrame.srcdoc = '';
                    currentPreviewCode = '';
                }
            }
        });
    });

    const autoResizeTextarea = () => {
        chatInput.style.height = 'auto';
        chatInput.style.height = `${chatInput.scrollHeight}px`;
    };
    
    chatInput.addEventListener('input', autoResizeTextarea);

    loadConversations();
});