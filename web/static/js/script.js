document.addEventListener('DOMContentLoaded', () => {
    // --- FIX: Robust solution for mobile viewport height issue ---
    const setRealViewportHeight = () => {
        const vh = window.innerHeight * 0.01;
        document.documentElement.style.setProperty('--vh', `${vh}px`);
    };
    window.addEventListener('resize', setRealViewportHeight);
    setRealViewportHeight();

    // --- Elements ---
    const sidebar = document.getElementById('sidebar');
    const toggleBtn = document.getElementById('toggle-sidebar');
    const newChatBtn = document.getElementById('new-chat-btn');
    const conversationsList = document.getElementById('conversations-list');
    const chatContainer = document.getElementById('chat-container');
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const sidebarOverlay = document.getElementById('sidebar-overlay');

    // Modals
    const previewModal = document.getElementById('preview-modal');
    const closeModalBtn = document.getElementById('close-modal');
    const runnerFrame = document.getElementById('runner-frame');
    const deleteModal = document.getElementById('delete-confirm-modal');
    const cancelDeleteBtn = document.getElementById('cancel-delete-btn');
    const confirmDeleteBtn = document.getElementById('confirm-delete-btn');
    const copyCodeBtn = document.getElementById('copy-code-btn');
    const downloadCodeBtn = document.getElementById('download-code-btn');

    let currentConversationId = null;
    let conversationToDeleteId = null;
    let currentPreviewCode = '';
    
    // --- Markdown Initializer ---
    const md = window.markdownit({
        highlight: (str, lang) => {
            if (lang && hljs.getLanguage(lang)) {
                try {
                    return `<pre class="hljs"><code>${hljs.highlight(str, { language: lang, ignoreIllegals: true }).value}</code></pre>`;
                } catch (__) {}
            }
            return `<pre class="hljs"><code>${md.utils.escapeHtml(str)}</code></pre>`;
        }
    });

    // --- Sidebar Logic ---
    const openSidebar = () => {
        sidebar.classList.add('open');
        sidebarOverlay.classList.add('active');
    };
    const closeSidebar = () => {
        sidebar.classList.remove('open');
        sidebarOverlay.classList.remove('active');
    };

    toggleBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        if (window.innerWidth < 768) {
            sidebar.classList.contains('open') ? closeSidebar() : openSidebar();
        } else {
            sidebar.classList.toggle('collapsed');
        }
    });
    sidebarOverlay.addEventListener('click', closeSidebar);

    // --- New Chat ---
    newChatBtn.addEventListener('click', () => {
        currentConversationId = null;
        chatContainer.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">💬</div>
                <h2>¿En qué puedo ayudarte hoy?</h2>
                <p>Puedo ayudarte a crear, depurar y mejorar tu código web</p>
            </div>`;
        document.querySelectorAll('.conversation-item').forEach(el => el.classList.remove('active'));
        if (window.innerWidth < 768) closeSidebar();
    });

    // --- Conversation Management ---
    async function loadConversations() {
        try {
            const res = await fetch('/api/conversations');
            if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
            const data = await res.json();
            displayConversations(data.conversations || []);
        } catch (err) {
            console.error('Error cargando conversaciones:', err);
        }
    }

    function displayConversations(conversations) {
        conversationsList.innerHTML = conversations.map(conv => `
            <div class="conversation-item" data-id="${conv._id}">
                <span class="conversation-title">${conv.title}</span>
                <button class="delete-btn" data-id="${conv._id}" aria-label="Eliminar conversación">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                </button>
            </div>`).join('');
        
        document.querySelectorAll('.conversation-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (!e.target.closest('.delete-btn')) loadConversation(item.dataset.id);
            });
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
            const res = await fetch(`/api/conversations/${id}`);
            if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
            const conv = await res.json();
            
            currentConversationId = id;
            chatContainer.innerHTML = '';

            conv.messages.forEach(msg => {
                appendMessage(msg.content, msg.role);
            });

            document.querySelectorAll('.conversation-item').forEach(el => {
                el.classList.toggle('active', el.dataset.id === id);
            });

            if (window.innerWidth < 768 && sidebar.classList.contains('open')) {
                closeSidebar();
            }
        } catch (err) {
            console.error('Error cargando conversación:', err);
        }
    }
    
    // --- Delete Confirmation Logic ---
    cancelDeleteBtn.addEventListener('click', () => deleteModal.classList.remove('show'));
    confirmDeleteBtn.addEventListener('click', async () => {
        if (!conversationToDeleteId) return;
        try {
            await fetch(`/api/conversations/${conversationToDeleteId}`, { method: 'DELETE' });
            if (currentConversationId === conversationToDeleteId) {
                newChatBtn.click();
            }
            loadConversations();
        } catch (err) {
            console.error('Error eliminando:', err);
        } finally {
            deleteModal.classList.remove('show');
            conversationToDeleteId = null;
        }
    });

    // --- Message Sending Logic (with Streaming Support) ---
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const message = chatInput.value.trim();
        if (!message) return;

        if (chatContainer.querySelector('.empty-state')) chatContainer.innerHTML = '';
        
        appendMessage(message, 'user');
        const typingIndicator = appendMessage('<div class="typing-indicator"><span></span><span></span><span></span></div>', 'bot', true);
        
        chatInput.value = '';
        autoResizeTextarea();
        sendBtn.disabled = true;

        try {
            // Si es un chat nuevo, usar el endpoint normal para obtener conversation_id
            if (!currentConversationId) {
                const res = await fetch('/api/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt: message, conversation_id: currentConversationId })
                });

                if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
                
                const data = await res.json();
                currentConversationId = data.conversation_id;
                loadConversations();
                updateLastBotMessage(data.response, typingIndicator);
            } else {
                // Si es un chat existente, usar streaming
                const res = await fetch('/api/generate-stream', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt: message, conversation_id: currentConversationId })
                });

                if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
                
                // Procesar el stream
                const reader = res.body.getReader();
                const decoder = new TextDecoder();
                let fullResponse = '';

                // Reemplazar el typing indicator con un mensaje vacío
                const content = typingIndicator.querySelector('.message-content');
                content.innerHTML = '';

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    
                    const chunk = decoder.decode(value, { stream: true });
                    fullResponse += chunk;
                    
                    // Re-renderizar el markdown completo en tiempo real
                    content.innerHTML = md.render(fullResponse);
                    addPreviewButton(content);
                    
                    // Auto-scroll
                    chatContainer.scrollTop = chatContainer.scrollHeight;
                }
            }
        } catch (err) {
            updateLastBotMessage('Error: No se pudo obtener respuesta del servidor.', typingIndicator);
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
        return msgGroup;
    }

    function updateLastBotMessage(text, elementToUpdate) {
        if (elementToUpdate) {
            const content = elementToUpdate.querySelector('.message-content');
            content.innerHTML = md.render(text);
            addPreviewButton(content);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    }
    
    // --- Code Preview Modal (MEJORADO) ---
    function addPreviewButton(content) {
        const codeBlocks = content.querySelectorAll('pre > code');
        
        codeBlocks.forEach(codeBlock => {
            const preElement = codeBlock.parentElement;
            if (preElement.querySelector('.code-header')) return; // Evitar duplicados

            const lang = (codeBlock.className.match(/language-(\S+)/) || [, ''])[1];
            const codeContent = codeBlock.textContent;

            const isHtmlContent = /^\s*<!DOCTYPE html|<html/i.test(codeContent);
            
            const header = document.createElement('div');
            header.className = 'code-header';

            const langName = document.createElement('span');
            langName.className = 'lang-name';
            langName.textContent = lang || (isHtmlContent ? 'html' : 'código');

            const actions = document.createElement('div');
            actions.className = 'code-actions';
            
            const copyBtn = document.createElement('button');
            copyBtn.className = 'code-action-btn';
            copyBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg> Copiar`;
            copyBtn.onclick = async () => {
                try {
                    await navigator.clipboard.writeText(codeBlock.textContent);
                    const originalText = copyBtn.innerHTML;
                    copyBtn.innerHTML = `¡Copiado!`;
                    setTimeout(() => { copyBtn.innerHTML = originalText; }, 2000);
                } catch(err) { console.error('Error al copiar'); }
            };
            actions.appendChild(copyBtn);

            if (lang === 'html' || isHtmlContent) {
                const btn = document.createElement('button');
                btn.className = 'code-action-btn preview-btn';
                btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg> Vista Previa`;
                
                btn.onclick = () => {
                    currentPreviewCode = codeBlock.textContent;
                    
                    // --- SOLUCIÓN DEFINITIVA: Inyectar script para prevenir navegación ---
                    const scriptToInject = `
                        <script>
                            document.addEventListener('DOMContentLoaded', () => {
                                const preventAction = (e) => {
                                    e.preventDefault();
                                    console.log('Acción prevenida en vista previa:', e.type, e.target);
                                    alert('La navegación y el envío de formularios están desactivados en esta vista previa.');
                                };
                                document.querySelectorAll('a, form, button[type="submit"]').forEach(el => {
                                    const eventType = el.tagName === 'FORM' ? 'submit' : 'click';
                                    el.addEventListener(eventType, preventAction);
                                });
                            });
                        <\/script>
                    `;
                    
                    // Añadir el script al final del body o del html
                    let modifiedCode = currentPreviewCode;
                    if (modifiedCode.includes('</body>')) {
                        modifiedCode = modifiedCode.replace('</body>', scriptToInject + '</body>');
                    } else {
                        modifiedCode += scriptToInject;
                    }

                    runnerFrame.srcdoc = modifiedCode;
                    previewModal.classList.add('show');
                };
                actions.appendChild(btn);
            }
            
            header.appendChild(langName);
            header.appendChild(actions);
            preElement.parentNode.insertBefore(header, preElement);
        });
    }

    // --- Modal Controls ---
    closeModalBtn.addEventListener('click', () => {
        previewModal.classList.remove('show');
        runnerFrame.srcdoc = '';
        currentPreviewCode = '';
    });

    copyCodeBtn.addEventListener('click', async () => {
        if (!currentPreviewCode) return;
        try {
            await navigator.clipboard.writeText(currentPreviewCode);
            const originalText = copyCodeBtn.innerHTML;
            copyCodeBtn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg> ¡Copiado!`;
            copyCodeBtn.style.background = 'var(--user-msg)';
            setTimeout(() => {
                copyCodeBtn.innerHTML = originalText;
                copyCodeBtn.style.background = '';
            }, 2000);
        } catch (err) {
            console.error('Error copiando código:', err);
            alert('No se pudo copiar el código.');
        }
    });

    downloadCodeBtn.addEventListener('click', () => {
        if (!currentPreviewCode) return;
        const blob = new Blob([currentPreviewCode], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `web-dev-ai-${Date.now()}.html`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
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

    // --- Textarea Auto-Resize Logic ---
    const autoResizeTextarea = () => {
        chatInput.style.height = 'auto';
        chatInput.style.height = `${chatInput.scrollHeight}px`;
    };
    chatInput.addEventListener('input', autoResizeTextarea);

    // --- Initial Load ---
    loadConversations();
});

