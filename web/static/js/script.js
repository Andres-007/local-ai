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
    const fileInput = document.getElementById('file-input');
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
    const conversationPaging = { limit: 30, offset: 0, hasMore: false, loading: false };
    const messagePaging = { limit: 50, offset: 0, hasMore: false, loading: false };
    
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

    conversationsList.addEventListener('click', (e) => {
        const deleteBtn = e.target.closest('.delete-btn');
        if (deleteBtn) {
            e.stopPropagation();
            conversationToDeleteId = deleteBtn.dataset.id;
            deleteModal.classList.add('show');
            return;
        }
        const item = e.target.closest('.conversation-item');
        if (item) {
            loadConversation(item.dataset.id);
        }
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

    async function loadConversations(reset = true) {
        if (conversationPaging.loading) return;
        conversationPaging.loading = true;
        try {
            if (reset) {
                conversationPaging.offset = 0;
                conversationsList.innerHTML = '';
            }
            const params = new URLSearchParams({
                limit: conversationPaging.limit,
                offset: conversationPaging.offset
            });
            const res = await fetchApi(`/api/conversations?${params.toString()}`);
            if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
            const data = await res.json();
            displayConversations(data.conversations || [], !reset);
            conversationPaging.hasMore = Boolean(data.has_more);
            updateConversationsLoadMore();
        } catch (err) {
            if (err.message !== 'No autorizado') {
                console.error('Error cargando conversaciones:', err);
            }
        } finally {
            conversationPaging.loading = false;
        }
    }

    function displayConversations(conversations, append = false) {
        const html = conversations.map(conv => `
            <div class="conversation-item" data-id="${conv._id}">
                <span class="conversation-title">${conv.title}</span>
                <button class="delete-btn" data-id="${conv._id}"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg></button>
            </div>`).join('');
        if (append) {
            conversationsList.insertAdjacentHTML('beforeend', html);
        } else {
            conversationsList.innerHTML = html;
        }
    }

    function updateConversationsLoadMore() {
        const existing = conversationsList.querySelector('.load-more-conversations');
        if (existing) existing.remove();
        if (!conversationPaging.hasMore) return;
        const btn = document.createElement('button');
        btn.className = 'load-more-conversations';
        btn.textContent = 'Cargar más';
        btn.addEventListener('click', async () => {
            if (conversationPaging.loading) return;
            conversationPaging.offset += conversationPaging.limit;
            await loadConversations(false);
        });
        conversationsList.appendChild(btn);
    }
    
    async function loadConversation(id, reset = true) {
        if (messagePaging.loading) return;
        messagePaging.loading = true;
        try {
            if (reset) {
                currentConversationId = id;
                messagePaging.offset = 0;
                chatContainer.innerHTML = '';
            }
            const params = new URLSearchParams({
                limit: messagePaging.limit,
                offset: messagePaging.offset
            });
            const res = await fetchApi(`/api/conversations/${id}?${params.toString()}`);
            if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
            const conv = await res.json();
            if (reset) {
                conv.messages.forEach(msg => appendMessage(msg.content, msg.role));
            } else {
                prependMessages(conv.messages || []);
            }
            messagePaging.hasMore = Boolean(conv.has_more_messages);
            updateMessagesLoadMore();
            document.querySelectorAll('.conversation-item').forEach(el => el.classList.toggle('active', el.dataset.id === id));
            if (window.innerWidth < 768) closeSidebar();
        } catch (err) {
            if (err.message !== 'No autorizado') console.error('Error cargando conversación:', err);
        } finally {
            messagePaging.loading = false;
        }
    }

    function updateMessagesLoadMore() {
        const existing = chatContainer.querySelector('.load-more-messages');
        if (existing) existing.remove();
        if (!messagePaging.hasMore) return;
        const btn = document.createElement('button');
        btn.className = 'load-more-messages';
        btn.textContent = 'Cargar mensajes anteriores';
        btn.addEventListener('click', async () => {
            if (messagePaging.loading || !currentConversationId) return;
            messagePaging.offset += messagePaging.limit;
            await loadConversation(currentConversationId, false);
        });
        chatContainer.insertAdjacentElement('afterbegin', btn);
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
    const file = fileInput.files[0];
    if (!message && !file) return;
    
    if (chatContainer.querySelector('.empty-state')) {
        chatContainer.innerHTML = '';
    }

    const displayMessage = message || `Archivo adjunto: ${file.name}`;
    appendMessage(displayMessage, 'user');
    const typingIndicator = appendMessage('<div class="typing-indicator"><span></span><span></span><span></span></div>', 'bot', true);
    chatInput.value = '';
    fileInput.value = '';
    autoResizeTextarea();
    sendBtn.disabled = true;

    try {
        const endpoint = currentConversationId ? '/api/generate-stream' : '/api/generate';
        let res;
        if (file) {
            const formData = new FormData();
            formData.append('prompt', message || `Archivo adjunto: ${file.name}`);
            if (currentConversationId) {
                formData.append('conversation_id', currentConversationId);
            }
            formData.append('file', file);
            res = await fetchApi(endpoint, {
                method: 'POST',
                body: formData
            });
        } else {
            res = await fetchApi(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    prompt: message, 
                    conversation_id: currentConversationId 
                })
            });
        }

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
            let renderTimeout = null;

            const scheduleRender = (final = false) => {
                if (final) {
                    if (renderTimeout) {
                        clearTimeout(renderTimeout);
                        renderTimeout = null;
                    }
                    content.innerHTML = md.render(fullResponse);
                    addPreviewButton(content);
                    chatContainer.scrollTop = chatContainer.scrollHeight;
                    return;
                }
                if (renderTimeout) return;
                renderTimeout = setTimeout(() => {
                    renderTimeout = null;
                    content.innerHTML = md.render(fullResponse);
                    chatContainer.scrollTop = chatContainer.scrollHeight;
                }, 120);
            };

            try {
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    
                    const chunk = decoder.decode(value, { stream: true });
                    fullResponse += chunk;
                    scheduleRender();
                }
                // Final decode to handle any remaining bytes
                const remaining = decoder.decode();
                if (remaining) {
                    fullResponse += remaining;
                }
                scheduleRender(true);
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


    function buildMessageElement(text, role, isTyping = false) {
        const msgGroup = document.createElement('div');
        msgGroup.className = `message-group ${role}-message`;
        msgGroup.innerHTML = `
            <div class="message-header">${role === 'user' ? 'Tú' : 'Web Dev AI'}</div>
            <div class="message-content">${isTyping ? text : (role === 'bot' ? md.render(text) : text.replace(/</g, "&lt;").replace(/>/g, "&gt;"))}</div>
        `;
        return msgGroup;
    }

    function appendMessage(text, role, isTyping = false) {
        const msgGroup = buildMessageElement(text, role, isTyping);
        chatContainer.appendChild(msgGroup);
        chatContainer.scrollTop = chatContainer.scrollHeight;
        if (role === 'bot' && !isTyping) addPreviewButton(msgGroup.querySelector('.message-content'));
        return msgGroup;
    }

    function prependMessages(messages) {
        if (!messages.length) return;
        const frag = document.createDocumentFragment();
        messages.forEach(msg => {
            frag.appendChild(buildMessageElement(msg.content, msg.role));
        });
        const loadMoreBtn = chatContainer.querySelector('.load-more-messages');
        const insertBefore = loadMoreBtn ? loadMoreBtn.nextSibling : chatContainer.firstChild;
        chatContainer.insertBefore(frag, insertBefore);
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
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!sendBtn.disabled) {
                chatForm.requestSubmit();
            }
        }
    });

    loadConversations();
});