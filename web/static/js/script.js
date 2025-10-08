        document.addEventListener('DOMContentLoaded', function () {
            const chatForm = document.getElementById('chat-form');
            const chatInput = document.getElementById('chat-input');
            const chatMessages = document.getElementById('chat-messages');
            const sendBtn = document.getElementById('send-btn');
            const modal = document.getElementById('preview-modal');
            const closeModalBtn = document.getElementById('close-modal');
            const runnerFrame = document.getElementById('runner-frame');

            // Verificar que markdown-it se haya cargado correctamente
            if (typeof window.markdownit !== 'function') {
                console.error("Error Crítico: La librería markdown-it no se ha cargado.");
                appendMessage('Error: No se pudo cargar un componente esencial. Por favor, recarga la página.', 'bot');
                return;
            }

            // Inicializa markdown-it con highlight.js
            const md = window.markdownit({
                highlight: function (str, lang) {
                    if (lang && hljs.getLanguage(lang)) {
                        try {
                            return '<pre><code class="hljs ' + lang + '">' +
                                   hljs.highlight(str, { language: lang, ignoreIllegals: true }).value +
                                   '</code></pre>';
                        } catch (__) {}
                    }
                    return '<pre><code class="hljs">' + md.utils.escapeHtml(str) + '</code></pre>';
                }
            });

            // Manejo del formulario de chat
            chatForm.addEventListener('submit', async function(event) {
                event.preventDefault();

                const userMessage = chatInput.value.trim();
                if (!userMessage) return;

                chatInput.value = '';
                sendBtn.disabled = true;

                appendMessage(userMessage, 'user');
                appendMessage('<div class="typing-indicator"><span></span><span></span><span></span></div>', 'bot', true);

                try {
                    const response = await fetch('/api/generate', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ prompt: userMessage }),
                    });

                    if (!response.ok) {
                        const errorData = await response.json();
                        throw new Error(errorData.error || 'Error en la respuesta del servidor.');
                    }

                    const data = await response.json();
                    updateLastBotMessage(data.response);

                } catch (error) {
                    console.error('Error al contactar la API:', error);
                    updateLastBotMessage(`Lo siento, ocurrió un error: ${error.message}`);
                } finally {
                    sendBtn.disabled = false;
                    chatInput.focus();
                }
            });

            // Funciones auxiliares
            function appendMessage(text, sender, isTyping = false) {
                const messageElement = document.createElement('div');
                messageElement.classList.add('message', `${sender}-message`);
                
                if (isTyping) {
                    messageElement.innerHTML = text;
                    messageElement.id = 'typing-indicator-msg';
                } else if (sender === 'bot') {
                    messageElement.innerHTML = md.render(text);
                } else {
                    messageElement.textContent = text;
                }
                
                chatMessages.appendChild(messageElement);
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }

            function updateLastBotMessage(text) {
                let typingIndicator = document.getElementById('typing-indicator-msg');
                if (typingIndicator) {
                    typingIndicator.innerHTML = md.render(text);
                    addPreviewButtonIfNeeded(typingIndicator);
                    typingIndicator.removeAttribute('id');
                }
            }

            function addPreviewButtonIfNeeded(messageElement) {
                const codeBlock = messageElement.querySelector('code.html, code.language-html');
                if (codeBlock) {
                    const previewBtn = document.createElement('button');
                    previewBtn.textContent = 'Previsualizar Código';
                    previewBtn.className = 'preview-btn';
                    previewBtn.onclick = () => {
                        const codeToRun = codeBlock.innerText;
                        runnerFrame.srcdoc = codeToRun;
                        modal.style.display = 'flex';
                    };
                    messageElement.appendChild(previewBtn);
                }
            }

            // Manejo del modal
            closeModalBtn.addEventListener('click', () => {
                modal.style.display = 'none';
                runnerFrame.srcdoc = '';
            });

            window.addEventListener('click', (event) => {
                if (event.target == modal) {
                    modal.style.display = 'none';
                    runnerFrame.srcdoc = '';
                }
            });
        });