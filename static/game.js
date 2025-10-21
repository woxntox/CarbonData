// Vantablack Game JavaScript
class VantablackGame {
    constructor() {
        this.gameState = {
            roomState: 'dark',
            position: 'center',
            devicePickedUp: false,
            doorUnlatched: false,
            patchUnreadCount: 0
        };
        this.hintTimeoutId = null;
        this.hintShown = false;
        this.photos = [];
        
        this.initializeElements();
        this.attachEventListeners();
        this.loadGameState();
    }
    
    initializeElements() {
        this.narrationFeed = document.getElementById('narrationFeed');
        this.roomStateDisplay = document.getElementById('roomState');
        this.positionDisplay = document.getElementById('position');
        this.commandInput = document.getElementById('commandInput');
        this.patchButton = document.getElementById('patchButton');
        this.patchBadge = document.getElementById('patchBadge');
        this.patchModal = document.getElementById('patchModal');
        this.patchMessages = document.getElementById('patchMessages');
        this.patchGallery = document.getElementById('patchGallery');
        this.patchChatTab = document.getElementById('patchChatTab');
        this.patchPhotosTab = document.getElementById('patchPhotosTab');
        this.patchTerminal = document.getElementById('patchTerminal');
        this.terminalContent = document.getElementById('terminalContent');
        this.patchInput = document.getElementById('patchInput');
        this.patchImage = document.getElementById('patchImage');
        this.patchCamera = document.getElementById('patchCamera');
        this.patchClose = document.getElementById('patchClose');
        this.patchTyping = document.getElementById('patchTyping');
        this.nameModal = document.getElementById('nameModal');
        this.nameInput = document.getElementById('nameInput');
        this.nameSubmit = document.getElementById('nameSubmit');
        this.pickupButtonContainer = document.getElementById('pickupButtonContainer');
        this.pickupDeviceButton = document.getElementById('pickupDeviceButton');
        this.cameraButtonContainer = document.getElementById('cameraButtonContainer');
        this.cameraButton = document.getElementById('cameraButton');
        // Mini-map removed
        this.vantablackOverlay = document.getElementById('vantablackOverlay');
    }
    
    attachEventListeners() {
        // Command button
        const commandButton = document.getElementById('commandButton');
        if (commandButton) {
            commandButton.addEventListener('click', () => this.handleCommand());
        }
        if (this.commandInput) {
            this.commandInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.handleCommand();
            });
        }
        
        // PATCH button
        if (this.patchButton) {
            this.patchButton.addEventListener('click', () => this.openPatchModal());
        }
        if (this.patchClose) {
            this.patchClose.addEventListener('click', () => this.closePatchModal());
        }
        
        // PATCH send
        const patchSend = document.getElementById('patchSend');
        if (patchSend) {
            patchSend.addEventListener('click', () => this.sendPatchMessage());
        }
        if (this.patchCamera) this.patchCamera.addEventListener('click', () => this.onCameraClick());
        if (this.patchImage) this.patchImage.addEventListener('change', (e) => this.uploadPatchImage(e));
        if (this.patchInput) {
            this.patchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.sendPatchMessage();
            });
        }
        
        // Name submit
        if (this.nameSubmit) {
            this.nameSubmit.addEventListener('click', () => this.submitName());
        }
        if (this.nameInput) {
            this.nameInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.submitName();
            });
        }
        if (this.pickupDeviceButton) {
            this.pickupDeviceButton.addEventListener('click', () => this.pickupDevice());
        }
        
        // Save Game button
        
        // Mini-map removed
        
        // Camera button
        if (this.cameraButton) {
            this.cameraButton.addEventListener('click', () => this.onCameraClick());
        }
        
        // Tabs
        if (this.patchChatTab) {
            this.patchChatTab.addEventListener('click', () => this.switchToChatTab());
        }
        if (this.patchPhotosTab) {
            this.patchPhotosTab.addEventListener('click', () => this.switchToPhotosTab());
        }

        // Close modals on outside click
        this.patchModal.addEventListener('click', (e) => {
            if (e.target === this.patchModal) this.closePatchModal();
        });
        this.nameModal.addEventListener('click', (e) => {
            if (e.target === this.nameModal) this.closeNameModal();
        });
    }
    
    async handleCommand() {
        const command = this.commandInput.value.trim();
        if (!command) return;
        
        // Check if it's a "say" command (handle variations)
        const lowerCommand = command.toLowerCase();
        if (lowerCommand.startsWith('say ') || lowerCommand.startsWith('say,')) {
            await this.handleSayCommand(command);
        } else {
            await this.handleDoCommand(command);
        }
        
        this.commandInput.value = '';
    }
    
    async handleDoCommand(command) {
        // Parse action and target
        const parts = command.split(' ');
        const actionType = parts[0];
        let target = parts.slice(1).join(' ');
        
        // Clean up common prepositions
        if (target.startsWith('to ')) {
            target = target.substring(3);
        }
        if (target.startsWith('the ')) {
            target = target.substring(4);
        }
        
        this.addNarration(`<strong>COMMAND:</strong> ${command}`, 'player-action');
        
        try {
            const response = await fetch('/action/do', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    action: actionType,
                    target: target
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Show AI narration if available
                if (data.narration && data.narration.trim()) {
                    this.addNarration(data.narration, 'narration');
                }
                
                // Show result message if available
                if (data.result && data.result.trim()) {
                    this.addNarration(data.result, 'result');
                }
                
                // If no narration was generated, show thinking message
                if (data.needs_ai_narration && (!data.narration || data.narration.trim() === '')) {
                    this.addNarration("The AI narrator considers your action...", 'ai-thinking');
                }
            } else {
                this.addNarration(data.result, 'error');
            }
            
            // Update game state (prefer unified envelope if present)
            if (data.envelope && data.envelope.state) {
                this.updateGameState({
                    room_state: data.envelope.state.light,
                    player_position: data.envelope.state.position,
                    device_picked_up: data.envelope.state.tutorial && data.envelope.state.tutorial.device_picked_up,
                    tutorial_photo_needed: data.envelope.state.tutorial && data.envelope.state.tutorial.tutorial_photo_needed,
                    photo_request_active: data.envelope.state.tutorial && data.envelope.state.tutorial.photo_request_active
                });
            } else {
                this.updateGameState(data.game_state);
            }
            
            // Handle Patch response (prefer unified envelope)
            if (data.envelope && data.envelope.patch) {
                const pr = data.envelope.patch;
                if (pr.messages && pr.messages.length) {
                    this.handlePatchResponse({
                        messages: pr.messages.map(m => ({ text: m.text, sender: m.sender || 'patch' })),
                        unread_count: pr.unread_delta,
                        stagger: pr.stagger
                    });
                }
            } else if (data.patch_response) {
                this.handlePatchResponse(data.patch_response);
            }
            
            // Handle name modal
            if (data.name_modal) {
                this.showNameModal();
            }
            
            // Handle Patch button appearance
            if (data.show_patch_button) {
                this.showPatchButton();
            }
            
            // Handle pickup button appearance
            if (data.show_pickup_button) {
                this.showPickupButton();
            }
            
            // Handle VANTABLACK overlay
            if (data.show_vantablack) {
                this.showVantablackOverlay();
            }
            
        } catch (error) {
            console.error('Command error:', error);
            this.addNarration('Something went wrong. Please try again.', 'error');
        }
    }
    
    async handleSayCommand(command) {
        // Remove "say " or "say," and clean up
        let sayText = command;
        if (command.toLowerCase().startsWith('say ')) {
            sayText = command.substring(4);
        } else if (command.toLowerCase().startsWith('say,')) {
            sayText = command.substring(4);
        }
        sayText = sayText.trim();
        
        this.addNarration(`<strong>SAY:</strong> "${sayText}"`, 'player-action');
        
        try {
            const response = await fetch('/action/say', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text: sayText
                })
            });
            
            const data = await response.json();
            
            if (data.environmental_response || (data.envelope && data.envelope.narration)) {
                this.addNarration(data.environmental_response || data.envelope.narration, 'environmental');
            }
            
            // Handle Patch response
            if (data.patch_response) {
                this.handlePatchResponse(data.patch_response);
            }
            
            // Update game state (prefer envelope)
            if (data.envelope && data.envelope.state) {
                this.updateGameState({
                    room_state: data.envelope.state.light,
                    player_position: data.envelope.state.position,
                    device_picked_up: data.envelope.state.tutorial && data.envelope.state.tutorial.device_picked_up,
                    tutorial_photo_needed: data.envelope.state.tutorial && data.envelope.state.tutorial.tutorial_photo_needed,
                    photo_request_active: data.envelope.state.tutorial && data.envelope.state.tutorial.photo_request_active
                });
            } else {
                this.updateGameState(data.game_state);
            }
            
        } catch (error) {
            console.error('SAY command error:', error);
            this.addNarration('Something went wrong. Please try again.', 'error');
        }
    }
    
    async submitName() {
        const name = this.nameInput.value.trim();
        if (!name) return;
        
        // Client-side validation
        if (name.length > 50) {
            this.addNarration('Name too long (max 50 characters)', 'error');
            return;
        }
        
        // Check for dangerous characters
        const dangerousChars = ['..', '/', '\\', '<', '>', ':', '"', '|', '?', '*'];
        for (const char of dangerousChars) {
            if (name.includes(char)) {
                this.addNarration('Invalid characters in name', 'error');
                return;
            }
        }
        
        // Check for suspicious patterns
        const suspiciousPatterns = ['<script', 'javascript:', 'data:', 'vbscript:', 'onload=', 'onerror='];
        const nameLower = name.toLowerCase();
        for (const pattern of suspiciousPatterns) {
            if (nameLower.includes(pattern)) {
                this.addNarration('Suspicious content detected in name', 'error');
                return;
            }
        }
        
        try {
            // Send name to server
            const response = await fetch('/game/set_name', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    name: name
                })
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                // Store the name in game state
                this.gameState.playerName = name;
                
                // Handle Patch response if present (tutorial messages)
                if (data.patch_response) {
                    this.handlePatchResponse(data.patch_response);
                }
                
                // Close name modal
                this.closeNameModal();
                
                // Show Patch button
                this.showPatchButton();
                
                // Auto-open Patch modal to show the message
                this.openPatchModal();
            } else {
                console.error('Name submission failed:', data.error);
            }
            
        } catch (error) {
            console.error('Name submission error:', error);
        }
    }
    
    closeNameModal() {
        this.nameModal.classList.add('hidden');
    }
    
    showPatchButton() {
        this.patchButton.classList.remove('hidden');
        this.patchButton.style.animation = 'fadeIn 0.5s ease-in';
    }
    
    showPickupButton() {
        this.pickupButtonContainer.classList.remove('hidden');
    }
    
    showVantablackOverlay() {
        this.vantablackOverlay.classList.remove('hidden');
    }
    
    async pickupDevice() {
        try {
            const response = await fetch('/action/do', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    action: 'pick_up',
                    target: 'device'
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.addNarration(data.narration, 'narration');
                this.addNarration(data.result, 'result');
                this.pickupButtonContainer.classList.add('hidden');
                
                // Show name modal after picking up device
                if (data.name_modal) {
                    this.showNameModal();
                }

                // Mini-map removed
            } else {
                this.addNarration(data.result, 'error');
            }
            
            // Update game state (with null check)
            if (data.game_state) {
                this.updateGameState(data.game_state);
            }
            
        } catch (error) {
            console.error('Pickup device error:', error);
            this.addNarration('Something went wrong. Please try again.', 'error');
        }
    }
    
    async sendPatchMessage() {
        const message = this.patchInput.value.trim();
        if (!message) return;
        
        // Prevent yes/no responses after gallery enabled
        if (this.gameState && this.gameState.gallery_enabled) {
            const msgLower = message.toLowerCase();
            if (['yes', 'no', 'yeah', 'nope', 'yep', 'nah'].includes(msgLower)) {
                // Don't send, just clear input
                this.patchInput.value = '';
                return;
            }
        }
        
        // Add player message to chat
        this.addPatchMessage(message, 'player');
        
        try {
            const response = await fetch('/patch/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message
                })
            });
            
            const data = await response.json();
            
            if (data.patch_response) {
                this.addPatchMessage(data.patch_response.message || data.patch_response, 'patch');
                
                // If Patch response should show in narration, add it there too
                if (data.patch_response.show_in_narration) {
                    this.addNarration(`<strong>PATCH:</strong> ${data.patch_response.message}`, 'patch-response');
                }
                
                // Check if coding sequence should start
                if (data.patch_response.coding_sequence) {
                    setTimeout(() => {
                        this.startCodingSequence();
                    }, 2000);
                }
            }
            
            // Update game state (with null check)
            if (data.game_state) {
                this.updateGameState(data.game_state);
            }
            
        } catch (error) {
            console.error('Patch chat error:', error);
            this.addPatchMessage('Sorry, I can\'t respond right now.', 'patch');
        }
        
        this.patchInput.value = '';
    }
    
    handlePatchResponse(patchResponse) {
        console.log('DEBUG: handlePatchResponse called with:', patchResponse);
        if (patchResponse.messages) {
            console.log('DEBUG: Processing', patchResponse.messages.length, 'messages');
            // Show typing indicator for multiple messages
            this.showTypingIndicator();
            
            // Handle multiple messages with staggered timing
            patchResponse.messages.forEach((msg, index) => {
                let delay;
                if (patchResponse.stagger === 'short') {
                    // Short stagger: ~1.5–2.5 seconds
                    delay = Math.random() * 1000 + 1500;
                } else {
                    // Default stagger: ~2–3 seconds
                    delay = Math.random() * 1000 + 2000;
                }
                
                setTimeout(() => {
                    this.hideTypingIndicator();
                    const messageText = msg.text || msg.message; // Support both envelope and legacy formats
                    this.addNarration(`<strong>PATCH:</strong> ${messageText}`, 'patch-response');
                    this.addPatchMessage(messageText, 'patch');
                    
                    // Check for gallery trigger line
                    if (messageText && messageText.trim() === "Ok, looks like you can see now" && !this.gameState.gallery_question_asked) {
                        setTimeout(() => {
                            this.addPatchMessage("Hey, you want me to hack this silly thing to create a photo gallery you can pull up to see these photos?", 'patch');
                            this.gameState.gallery_question_asked = true;
                        }, 2000);
                        
                        // Add follow-up message after gallery question
                        setTimeout(() => {
                            this.addPatchMessage("Hey, by the way. If you need some help or just want to chat about dope stuff. Me and D used to do that.", 'patch');
                        }, 4000);
                    }
                    
                    // Enable camera when IMPORTANT message is displayed
                    if (messageText && messageText.includes('IMPORTANT')) {
                        this.gameState.photo_request_active = true;
                        this.updateGameState(this.gameState);
                    }
                    
                    // Hide typing indicator after last message
                    if (index === patchResponse.messages.length - 1) {
                        this.hideTypingIndicator();
                    }
                }, index * delay);
            });
        } else if (patchResponse.message) {
            // Handle single message
            this.addNarration(`<strong>PATCH:</strong> ${patchResponse.message}`, 'patch-response');
            this.addPatchMessage(patchResponse.message, 'patch');
            
            // Check for gallery trigger line
            if (patchResponse.message && patchResponse.message.trim() === "Ok, looks like you can see now" && !this.gameState.gallery_question_asked) {
                setTimeout(() => {
                    this.addPatchMessage("Hey, you want me to hack this silly thing to create a photo gallery you can pull up to see these photos?", 'patch');
                    this.gameState.gallery_question_asked = true;
                }, 2000);
                
                // Add follow-up message after gallery question
                setTimeout(() => {
                    this.addPatchMessage("Hey, by the way. If you need some help or just want to chat about dope stuff. Me and D used to do that.", 'patch');
                }, 4000);
            }
        }

        // Update badge with unread delta (increment)
        if (patchResponse.unread_delta !== undefined) {
            const currentBadge = this.patchBadge.classList.contains('hidden')
                ? 0
                : (this.patchBadge.textContent === '9+' ? 9 : parseInt(this.patchBadge.textContent || '0', 10) || 0);
            const nextCount = currentBadge + patchResponse.unread_delta;
            this.updatePatchBadge(nextCount);
        } else if (patchResponse.unread_count !== undefined) {
            // Legacy fallback: use total count
            this.updatePatchBadge(patchResponse.unread_count);
        } else {
            // Final fallback: increment by one per new Patch reply
            const currentBadge = this.patchBadge.classList.contains('hidden')
                ? 0
                : (this.patchBadge.textContent === '9+' ? 9 : parseInt(this.patchBadge.textContent || '0', 10) || 0);
            const nextCount = currentBadge + 1;
            this.updatePatchBadge(nextCount);
        }

        // Check if name modal should be shown
        if (patchResponse.name_modal) {
            this.showNameModal();
        }
    }
    
    showNameModal() {
        this.nameModal.classList.remove('hidden');
        // If the game set a forced name (e.g., from taste/lick), lock the field
        const forced = this.gameState && this.gameState.forced_name;
        if (forced) {
            this.nameInput.value = forced;
            this.nameInput.setAttribute('disabled', 'disabled');
        } else {
            this.nameInput.removeAttribute('disabled');
            this.nameInput.value = '';
            this.nameInput.focus();
        }
    }
    
    addNarration(text, type = 'narration') {
        const messageDiv = document.createElement('div');
        messageDiv.className = `narration-message ${type}`;
        messageDiv.innerHTML = text;
        
        // Add event listener for clickable links
        const links = messageDiv.querySelectorAll('a[data-action="openPatchCamera"]');
        links.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                // Check if this link has a script attribute
                const script = link.getAttribute('data-script');
                if (script) {
                    // Set the photo script in game state
                    this.setPhotoScript(script);
                }
                this.openPatchModal();
            });
        });
        
        this.narrationFeed.appendChild(messageDiv);
        this.narrationFeed.scrollTop = this.narrationFeed.scrollHeight;
    }
    
    addPatchMessage(message, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `patch-message patch-message-${sender}`;
        const senderLabel = sender === 'player' ? ((this.gameState && this.gameState.player_name) || 'You') : sender;
        if (typeof message === 'string' && message.startsWith('[image]')) {
            const url = message.substring(7);
            messageDiv.innerHTML = `<strong>${senderLabel}:</strong><br/><img src="${url}" alt="upload" style="max-width:100%; border:1px solid #333;" />`;
            // Store photo for gallery
            if (!this.photos.includes(url)) {
                this.photos.push(url);
                this.renderGallery();
            }
        } else {
            messageDiv.innerHTML = `<strong>${senderLabel}:</strong> ${message}`;
        }
        
        this.patchMessages.appendChild(messageDiv);
        this.patchMessages.scrollTop = this.patchMessages.scrollHeight;
    }

    renderGallery() {
        if (!this.patchGallery) return;
        this.patchGallery.innerHTML = '';
        this.photos.forEach((url) => {
            const item = document.createElement('div');
            item.className = 'patch-gallery-item';
            const img = document.createElement('img');
            img.src = url;
            img.alt = 'Photo';
            img.addEventListener('click', () => this.openPhotoViewer(url));
            item.appendChild(img);
            this.patchGallery.appendChild(item);
        });
    }
    
    updateGameState(gameState) {
        this.gameState = gameState;
        this.roomStateDisplay.textContent = this.getRoomStateText(gameState.room_state);
        this.positionDisplay.textContent = gameState.player_position.replace('_', ' ');
        
        // Handle Patch button blinking for photo requests
        const needsPhoto = !!gameState.photo_request_active;
        if (this.patchButton) {
            if (needsPhoto) {
                this.patchButton.classList.add('blink-red');
            } else {
                this.patchButton.classList.remove('blink-red');
            }
        }
        
        // Show/hide Patch button based on device pickup
        if (this.patchButton) {
            if (gameState.device_picked_up) {
                this.patchButton.classList.remove('hidden');
            } else {
                this.patchButton.classList.add('hidden');
            }
        }
        
        // Toggle camera button for photo requests (only when explicitly active)
        console.log('DEBUG: updateGameState - photo_request_active:', gameState.photo_request_active, 'needsPhoto:', needsPhoto);
        if (this.patchCamera) {
            // Make camera available only when photo_request_active is true
            if (needsPhoto) {
                this.patchCamera.classList.remove('hidden');
                console.log('DEBUG: Showing patch camera');
            } else {
                this.patchCamera.classList.add('hidden');
                console.log('DEBUG: Hiding patch camera');
            }
        }
        
        // Toggle red camera button below COMMAND box
        if (this.cameraButtonContainer) {
            if (needsPhoto) {
                this.cameraButtonContainer.classList.remove('hidden');
                console.log('DEBUG: Showing camera button container');
            } else {
                this.cameraButtonContainer.classList.add('hidden');
                console.log('DEBUG: Hiding camera button container');
            }
        }
        
        // Toggle Photos tab based on gallery_enabled
        if (this.patchPhotosTab) {
            if (gameState.gallery_enabled) {
                this.patchPhotosTab.classList.remove('hidden');
            } else {
                this.patchPhotosTab.classList.add('hidden');
            }
        }
        
        // Mini-map removed

        // Darkness hint timer management (3 minutes)
        if (!this.hintShown) {
            if (gameState.room_state === 'dark') {
                // Start timer if not already started
                if (!this.hintTimeoutId) {
                    this.hintTimeoutId = setTimeout(() => {
                        // Only fire if still dark and not already shown
                        if (this.gameState && this.gameState.room_state === 'dark' && !this.hintShown) {
                            this.addNarration('A disembodied voice: Hey, life is hard, but you\'re really in a pickle. I mean, you are in a jam. Try moving around, or use more of your heightened senses, Superman.', 'environmental');
                            this.hintShown = true;
                        }
                        this.hintTimeoutId = null;
                    }, 3 * 60 * 1000);
                }
            } else {
                // Cancel timer when no longer dark
                if (this.hintTimeoutId) {
                    clearTimeout(this.hintTimeoutId);
                    this.hintTimeoutId = null;
                }
            }
        }
    }

    async onCameraClick() {
        console.log('DEBUG: onCameraClick called, gameState:', this.gameState);
        // Check if camera is available for any photo request
        const needsPhoto = !!(this.gameState && this.gameState.photo_request_active);
        console.log('DEBUG: needsPhoto:', needsPhoto);
        if (needsPhoto) {
            try {
                const form = new FormData();
                form.append('auto', '1');
                const resp = await fetch('/patch/upload', { method: 'POST', body: form });
                const data = await resp.json();
                console.log('Upload response:', data);
                if (data.status === 'success') {
                    // Handle single URL (tutorial) or multiple URLs (article script)
                    if (data.urls && Array.isArray(data.urls)) {
                        // Article script: multiple images
                        console.log('DEBUG: Article script URLs:', data.urls);
                        data.urls.forEach(url => {
                            console.log('DEBUG: Processing URL:', url);
                            this.addPatchMessage(`[image]${url}`, 'player');
                        });
                    } else if (data.url) {
                        // Tutorial: single image
                        this.addPatchMessage(`[image]${data.url}`, 'player');
                    }
                    // Handle patch response if present (prefer envelope)
                    if (data.envelope && data.envelope.patch) {
                        console.log('Handling envelope patch response:', data.envelope.patch);
                        // Map envelope messages to expected format
                        const envelopeMessages = data.envelope.patch.messages.map(m => ({
                            text: m.text,
                            sender: m.sender || 'patch'
                        }));
                        this.handlePatchResponse({
                            messages: envelopeMessages,
                            stagger: data.envelope.patch.stagger,
                            unread_delta: data.envelope.patch.unread_delta
                        });
                    } else if (data.patch_response) {
                        console.log('Handling legacy patch response:', data.patch_response);
                        this.handlePatchResponse(data.patch_response);
                    }
                } else if (data.status === 'missing') {
                    this.addPatchMessage('well phones are hard, nevermind.', 'patch');
                }
                const gsResp = await fetch('/game/state');
                const gs = await gsResp.json();
                this.updateGameState(gs);
            } catch (e) {
                console.error('Auto image error:', e);
            }
            return;
        }
        // Otherwise, fall back to manual picker if present
        if (this.patchImage) this.patchImage.click();
    }

    async uploadPatchImage(e) {
        const file = e.target.files && e.target.files[0];
        if (!file) return;
        const form = new FormData();
        form.append('image', file);
        try {
            const resp = await fetch('/patch/upload', { method: 'POST', body: form });
            const data = await resp.json();
            if (data.status === 'success') {
                this.addPatchMessage(`[image]${data.url}`, 'player');
                const gsResp = await fetch('/game/state');
                const gs = await gsResp.json();
                this.updateGameState(gs);
            } else {
                this.addPatchMessage('Upload failed.', 'patch');
            }
        } catch (err) {
            console.error('Upload error:', err);
            this.addPatchMessage('Upload error.', 'patch');
        } finally {
            if (this.patchImage) this.patchImage.value = '';
        }
    }
    
    getRoomStateText(roomState) {
        switch (roomState) {
            case 'dark': return 'Dark';
            case 'device_lit': return 'Device Lit';
            case 'room_lit': return 'Room Lit';
            default: return 'Unknown';
        }
    }
    
    updatePatchBadge(count) {
        if (count > 0) {
            this.patchBadge.textContent = count > 9 ? '9+' : count.toString();
            this.patchBadge.classList.remove('hidden');
        } else {
            this.patchBadge.classList.add('hidden');
        }
    }
    
    showTypingIndicator() {
        if (this.patchTyping) {
            this.patchTyping.classList.remove('hidden');
        }
    }
    
    hideTypingIndicator() {
        if (this.patchTyping) {
            this.patchTyping.classList.add('hidden');
        }
    }
    
    openPatchModal() {
        this.patchModal.classList.remove('hidden');
        this.patchInput.focus();
        
        // Implement scroll behavior with timing logic
        const now = Date.now();
        const timeSinceClose = this.lastModalCloseTime ? (now - this.lastModalCloseTime) : 10000; // Default to >10s if no previous close
        
        if (timeSinceClose < 10000 && !this.gameState.photo_request_active) {
            // Reopening within 10 seconds and no camera active - preserve scroll position
            // Scroll position is already preserved by browser
        } else {
            // Camera available OR >10 seconds - scroll to bottom (newest messages visible)
            this.patchMessages.scrollTop = this.patchMessages.scrollHeight;
        }
        
        // Mark messages as read
        this.markPatchRead();
    }
    
    closePatchModal() {
        // Prevent closing if tutorial photo is needed AND camera is active
        // Allow closing if tutorial photo has been taken (tutorial_photo_needed = false)
        if (this.gameState && this.gameState.tutorial_photo_needed && this.gameState.photo_request_active) {
            console.log('Modal locked: tutorial photo needed');
            return;
        }
        
        // Store close time for scroll behavior
        this.lastModalCloseTime = Date.now();
        
        this.patchModal.classList.add('hidden');
    }
    
    switchToChatTab() {
        if (this.patchChatTab) this.patchChatTab.classList.add('active');
        if (this.patchPhotosTab) this.patchPhotosTab.classList.remove('active');
        if (this.patchMessages) this.patchMessages.classList.remove('hidden');
        if (this.patchGallery) this.patchGallery.classList.add('hidden');
    }

    switchToPhotosTab() {
        if (this.patchPhotosTab) this.patchPhotosTab.classList.add('active');
        if (this.patchChatTab) this.patchChatTab.classList.remove('active');
        if (this.patchGallery) this.patchGallery.classList.remove('hidden');
        if (this.patchMessages) this.patchMessages.classList.add('hidden');
        
        // Check if gallery is enabled
        if (this.gameState.gallery_enabled) {
            this.renderGallery();
        } else {
            this.patchGallery.innerHTML = '<div class="gallery-locked">Gallery not yet unlocked. Take a photo first!</div>';
        }
    }

    openPhotoViewer(url) {
        if (!this.photoViewer) {
            this.photoViewer = document.getElementById('photoViewer');
            this.photoViewerImage = document.getElementById('photoViewerImage');
            this.photoViewerClose = document.getElementById('photoViewerClose');
            if (this.photoViewerClose) {
                this.photoViewerClose.addEventListener('click', () => this.closePhotoViewer());
            }
            if (this.photoViewer) {
                this.photoViewer.addEventListener('click', (e) => {
                    if (e.target === this.photoViewer) this.closePhotoViewer();
                });
            }
        }
        if (this.photoViewerImage) this.photoViewerImage.src = url;
        if (this.photoViewer) this.photoViewer.classList.remove('hidden');
    }

    closePhotoViewer() {
        if (this.photoViewer) this.photoViewer.classList.add('hidden');
    }

    async startCodingSequence() {
        if (!this.patchTerminal || !this.terminalContent) return;
        
        // Prevent running multiple times
        if (this.codingSequenceRunning) return;
        this.codingSequenceRunning = true;
        
        // Show terminal
        this.patchTerminal.classList.remove('hidden');
        
        // Clear terminal content
        this.terminalContent.innerHTML = '';
        
        // Enable close button after sequence completes
        const closeBtn = this.patchTerminal.querySelector('.terminal-btn.close');
        if (closeBtn) {
            closeBtn.classList.add('disabled');
        }
        
        // Get player name for personalized comment
        const playerName = this.gameState.player_name || 'Player';
        
        // More realistic coding sequence with proper Python code (5x more code, faster)
        const steps = [
            { type: 'command', text: 'python3 gallery_hack.py', delay: 30 },
            { type: 'output', text: 'Traceback (most recent call last):', delay: 30 },
            { type: 'output', text: '  File "gallery_hack.py", line 1, in <module>', delay: 30 },
            { type: 'error', text: '    import photos', delay: 1800 },
            { type: 'error', text: 'ModuleNotFoundError: No module named \'photos\'', delay: 1800 },
            { type: 'comment', text: '# well hell, that didn\'t work', delay: 30 },
            { type: 'command', text: 'cat > gallery_hack.py << \'EOF\'', delay: 30 },
            { type: 'code', text: '#!/usr/bin/env python3', delay: 20 },
            { type: 'code', text: '"""Photo Gallery System for Device UI"""', delay: 20 },
            { type: 'code', text: 'from pathlib import Path', delay: 20 },
            { type: 'code', text: 'import json', delay: 20 },
            { type: 'code', text: 'import base64', delay: 20 },
            { type: 'code', text: 'import hashlib', delay: 20 },
            { type: 'code', text: 'from typing import List, Dict, Optional', delay: 20 },
            { type: 'code', text: 'from datetime import datetime', delay: 20 },
            { type: 'code', text: 'import sys', delay: 20 },
            { type: 'code', text: 'import os', delay: 20 },
            { type: 'code', text: '', delay: 20 },
            { type: 'code', text: 'class PhotoGallery:', delay: 20 },
            { type: 'code', text: '    """Manages photo storage and display for device UI"""', delay: 20 },
            { type: 'code', text: '    ', delay: 20 },
            { type: 'code', text: '    def __init__(self, device_id: str, storage_path: str = "/device/photos"):', delay: 20 },
            { type: 'code', text: '        self.device_id = device_id', delay: 20 },
            { type: 'code', text: '        self.storage_path = Path(storage_path)', delay: 20 },
            { type: 'code', text: '        self.photos: List[Dict] = []', delay: 20 },
            { type: 'code', text: '        self.gallery_enabled = False', delay: 20 },
            { type: 'code', text: '        self._init_storage()', delay: 20 },
            { type: 'code', text: '    ', delay: 20 },
            { type: 'code', text: '    def _init_storage(self) -> None:', delay: 20 },
            { type: 'code', text: '        """Initialize storage directory"""', delay: 20 },
            { type: 'code', text: '        try:', delay: 20 },
            { type: 'code', text: '            self.storage_path.mkdir(parents=True, exist_ok=True)', delay: 20 },
            { type: 'code', text: '        except PermissionError:', delay: 20 },
            { type: 'code', text: '            print(f"Error: Cannot create directory {self.storage_path}")', delay: 20 },
            { type: 'code', text: '            sys.exit(1)', delay: 20 },
            { type: 'code', text: '    ', delay: 20 },
            { type: 'code', text: '    def load_photos(self) -> None:', delay: 20 },
            { type: 'code', text: '        """Load all photos from device storage"""', delay: 20 },
            { type: 'code', text: '        try:', delay: 20 },
            { type: 'code', text: '            photos_dir = Path(f"/device/{self.device_id}/photos")', delay: 20 },
            { type: 'code', text: '            if not photos_dir.exists():', delay: 20 },
            { type: 'code', text: '                print("Warning: Photos directory not found")', delay: 20 },
            { type: 'code', text: '                return', delay: 20 },
            { type: 'code', text: '            ', delay: 20 },
            { type: 'code', text: '            for photo_file in photos_dir.glob("*.png"):', delay: 20 },
            { type: 'code', text: '                metadata = self._load_metadata(photo_file)', delay: 20 },
            { type: 'code', text: '                self.photos.append({', delay: 20 },
            { type: 'code', text: '                    "filename": photo_file.name,', delay: 20 },
            { type: 'code', text: '                    "path": str(photo_file),', delay: 20 },
            { type: 'code', text: '                    "size": photo_file.stat().st_size,', delay: 20 },
            { type: 'code', text: '                    "modified": photo_file.stat().st_mtime,', delay: 20 },
            { type: 'code', text: '                    "checksum": self._calc_checksum(photo_file),', delay: 20 },
            { type: 'code', text: '                    "metadata": metadata', delay: 20 },
            { type: 'code', text: '                })', delay: 20 },
            { type: 'code', text: '            ', delay: 20 },
            { type: 'code', text: '            print(f"Loaded {len(self.photos)} photos")', delay: 20 },
            { type: 'code', text: '        except Exception as e:', delay: 20 },
            { type: 'code', text: '            print(f"Error loading photos: {e}")', delay: 20 },
            { type: 'code', text: '            raise', delay: 20 },
            { type: 'code', text: '    ', delay: 20 },
            { type: 'code', text: '    def _load_metadata(self, photo_path: Path) -> Dict:', delay: 20 },
            { type: 'code', text: '        """Load metadata JSON for photo"""', delay: 20 },
            { type: 'code', text: '        meta_path = photo_path.with_suffix(\'.json\')', delay: 20 },
            { type: 'code', text: '        if meta_path.exists():', delay: 20 },
            { type: 'code', text: '            with open(meta_path) as f:', delay: 20 },
            { type: 'code', text: '                return json.load(f)', delay: 20 },
            { type: 'code', text: '        return {}', delay: 20 },
            { type: 'code', text: '    ', delay: 20 },
            { type: 'code', text: '    def _calc_checksum(self, file_path: Path) -> str:', delay: 20 },
            { type: 'code', text: '        """Calculate SHA256 checksum of file"""', delay: 20 },
            { type: 'code', text: '        sha256 = hashlib.sha256()', delay: 20 },
            { type: 'code', text: '        with open(file_path, \'rb\') as f:', delay: 20 },
            { type: 'code', text: '            for chunk in iter(lambda: f.read(4096), b""):', delay: 20 },
            { type: 'code', text: '                sha256.update(chunk)', delay: 20 },
            { type: 'code', text: '        return sha256.hexdigest()', delay: 20 },
            { type: 'code', text: '', delay: 20 },
            { type: 'code', text: 'def generate_gallery_html(photos: List[Dict]) -> str:', delay: 20 },
            { type: 'code', text: '    """Generate HTML for photo gallery"""', delay: 20 },
            { type: 'code', text: '    gallery_html = """', delay: 20 },
            { type: 'code', text: '    <div class="patch-tabs">', delay: 20 },
            { type: 'code', text: '        <button id="patchChatTab" class="patch-tab active">Chat</button>', delay: 20 },
            { type: 'code', text: '        <button id="patchPhotosTab" class="patch-tab">Photos</button>', delay: 20 },
            { type: 'code', text: '    </div>', delay: 20 },
            { type: 'code', text: '    <div class="patch-gallery" id="patchGallery">', delay: 20 },
            { type: 'code', text: '    """', delay: 20 },
            { type: 'code', text: '    for photo in photos:', delay: 20 },
            { type: 'code', text: '        gallery_html += f\'<img src="{photo["path"]}" />\'', delay: 20 },
            { type: 'code', text: '    gallery_html += "</div>"', delay: 20 },
            { type: 'code', text: '    return gallery_html', delay: 20 },
            { type: 'code', text: '', delay: 20 },
            { type: 'code', text: 'def inject_gallery_ui(html_content: str) -> None:', delay: 20 },
            { type: 'code', text: '    """Inject gallery into device UI"""', delay: 20 },
            { type: 'code', text: '    ui_file = Path("/device/ui/index.html")', delay: 20 },
            { type: 'code', text: '    with open(ui_file, \'r+\') as f:', delay: 20 },
            { type: 'code', text: '        content = f.read()', delay: 20 },
            { type: 'code', text: '        marker = "<!-- INJECT_GALLERY_HERE -->"', delay: 20 },
            { type: 'code', text: '        content = content.replace(marker, html_content)', delay: 20 },
            { type: 'code', text: '        f.seek(0)', delay: 20 },
            { type: 'code', text: '        f.write(content)', delay: 20 },
            { type: 'code', text: '        f.truncate()', delay: 20 },
            { type: 'code', text: '', delay: 20 },
            { type: 'code', text: 'if __name__ == "__main__":', delay: 20 },
            { type: 'code', text: '    print("Initializing photo gallery...")', delay: 20 },
            { type: 'code', text: '    gallery = PhotoGallery("device_001")', delay: 20 },
            { type: 'code', text: '    gallery.load_photos()', delay: 20 },
            { type: 'code', text: '    html = generate_gallery_html(gallery.photos)', delay: 20 },
            { type: 'code', text: '    inject_gallery_ui(html)', delay: 20 },
            { type: 'code', text: '    print("Gallery hack complete!")', delay: 20 },
            { type: 'command', text: 'EOF', delay: 30 },
            { type: 'output', text: 'Writing gallery_hack.py...', delay: 500 },
            { type: 'command', text: 'python3 gallery_hack.py', delay: 30 },
            { type: 'output', text: 'Initializing photo gallery...', delay: 30 },
            { type: 'output', text: 'Traceback (most recent call last):', delay: 30 },
            { type: 'error', text: '  File "gallery_hack.py", line 98, in inject_gallery_ui', delay: 1800 },
            { type: 'error', text: 'FileNotFoundError: [Errno 2] No such file: \'/device/ui/index.html\'', delay: 1800 },
            { type: 'comment', text: '# I swear I\'m good at this', delay: 30 },
            { type: 'command', text: 'mkdir -p /device/ui && touch /device/ui/index.html', delay: 30 },
            { type: 'output', text: 'mkdir: Permission denied', delay: 30 },
            { type: 'comment', text: `# It's because you are WATCHING me, ${playerName}!`, delay: 1800 },
            { type: 'command', text: 'sudo mkdir -p /device/ui && sudo touch /device/ui/index.html', delay: 30 },
            { type: 'output', text: '[sudo] password for patch:', delay: 30 },
            { type: 'command', text: '**********', delay: 30 },
            { type: 'output', text: 'Directory created successfully', delay: 30 },
            { type: 'command', text: 'python3 gallery_hack.py', delay: 30 },
            { type: 'output', text: 'Initializing photo gallery...', delay: 30 },
            { type: 'output', text: 'Warning: Photos directory not found', delay: 30 },
            { type: 'output', text: 'Loaded 0 photos', delay: 30 },
            { type: 'error', text: 'Traceback (most recent call last):', delay: 1800 },
            { type: 'error', text: 'AttributeError: \'NoneType\' object has no attribute \'append\'', delay: 1800 },
            { type: 'comment', text: `# ${playerName}, you didn't drop this in the toilet did you?`, delay: 30 },
            { type: 'command', text: 'pip3 install device_ui_framework --upgrade', delay: 30 },
            { type: 'output', text: 'Collecting device_ui_framework', delay: 30 },
            { type: 'output', text: '  Downloading device_ui_framework-3.2.1-py3-none-any.whl (2.4MB)', delay: 30 },
            { type: 'output', text: '  |████████████████████████████████| 2.4MB 8.2MB/s', delay: 30 },
            { type: 'output', text: 'Installing collected packages: device_ui_framework', delay: 30 },
            { type: 'output', text: 'Successfully installed device_ui_framework-3.2.1', delay: 500 },
            { type: 'command', text: 'python3 -c "from device_ui_framework import inject_gallery; inject_gallery()"', delay: 30 },
            { type: 'output', text: 'Injecting gallery module...', delay: 30 },
            { type: 'output', text: 'Gallery UI injected successfully!', delay: 500 },
            { type: 'command', text: 'systemctl --user restart patch-device.service', delay: 30 },
            { type: 'output', text: 'Restarting patch-device.service...', delay: 30 },
            { type: 'output', text: 'Job for patch-device.service failed', delay: 30 },
            { type: 'error', text: 'Failed to restart patch-device.service: Unit not found', delay: 1800 },
            { type: 'comment', text: '# OH BYTE ME!', delay: 30 },
            { type: 'command', text: 'pkill -9 device_ui && python3 /device/ui/main.py --enable-gallery &', delay: 30 },
            { type: 'output', text: 'device_ui: no process found', delay: 30 },
            { type: 'output', text: 'Starting device UI with gallery support...', delay: 30 },
            { type: 'output', text: 'Gallery module loaded', delay: 30 },
            { type: 'output', text: 'Photos tab initialized', delay: 30 },
            { type: 'output', text: 'Device UI ready on port 8080', delay: 500 },
            { type: 'output', text: '✓ Gallery hack complete!', delay: 500 },
            { type: 'comment', text: '# Alright, fine. That actually worked. Don\'t tell anyone.', delay: 1800 }
        ];
        
        let currentDelay = 0;
        
        for (let i = 0; i < steps.length; i++) {
            const step = steps[i];
            currentDelay += step.delay;
            
            setTimeout(() => {
                this.addTerminalLine(step.type, step.text);
                
                // If this is the last step, complete the sequence
                if (i === steps.length - 1) {
                    setTimeout(() => {
                        this.completeCodingSequence();
                    }, 2000);
                }
            }, currentDelay);
        }
    }
    
    addTerminalLine(type, text) {
        const line = document.createElement('div');
        line.className = 'terminal-line';
        
        if (type === 'command') {
            line.innerHTML = `
                <span class="terminal-prompt">PATCH@device:~$</span>
                <span class="terminal-command">${text}</span>
            `;
        } else if (type === 'output') {
            line.innerHTML = `<span class="terminal-output">${text}</span>`;
        } else if (type === 'error') {
            line.innerHTML = `<span class="terminal-error">${text}</span>`;
        } else if (type === 'comment') {
            line.innerHTML = `<span class="terminal-comment">${text}</span>`;
        } else if (type === 'code') {
            // Just show instantly, no typing animation
            line.innerHTML = `<span class="terminal-code">${text}</span>`;
        }
        
        this.terminalContent.appendChild(line);
        this.terminalContent.scrollTop = this.terminalContent.scrollHeight;
    }
    
    typeText(element, text) {
        element.textContent = '';
        let i = 0;
        const typeInterval = setInterval(() => {
            if (i < text.length) {
                element.textContent += text[i];
                i++;
                // Scroll to bottom as we type
                this.terminalContent.scrollTop = this.terminalContent.scrollHeight;
            } else {
                clearInterval(typeInterval);
            }
        }, 25); // Slightly faster typing for code
    }
    
    async completeCodingSequence() {
        try {
            // Enable close button
            const closeBtn = this.patchTerminal.querySelector('.terminal-btn.close');
            if (closeBtn) {
                closeBtn.classList.remove('disabled');
                closeBtn.addEventListener('click', () => {
                    this.patchTerminal.classList.add('hidden');
                });
            }
            
            // Call backend to complete sequence
            const response = await fetch('/patch/coding_sequence', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                // Show success message
                this.addPatchMessage('Gallery hack complete! Check the Photos tab.', 'patch');
                
                // Enable gallery if not already enabled
                if (data.gallery_enabled) {
                    this.gameState.gallery_enabled = true;
                    this.updateGameState(this.gameState);
                }
            }
        } catch (error) {
            console.error('Coding sequence completion error:', error);
        }
    }
    
    async loadMap() {
        try {
            const response = await fetch('/action/do', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'map', target: '' })
            });
            const data = await response.json();
            if (data.success) {
                this.mapDisplay.textContent = data.result;
            } else {
                this.mapDisplay.textContent = "You can't see the map in the darkness.";
            }
        } catch (error) {
            this.mapDisplay.textContent = "Error loading map.";
        }
    }
    
    async markPatchRead() {
        try {
            await fetch('/patch/mark_read', { method: 'POST' });
            this.updatePatchBadge(0);
        } catch (error) {
            console.error('Mark read error:', error);
        }
    }
    
    async setPhotoScript(script) {
        try {
            console.log('DEBUG: Setting photo script:', script);
            const response = await fetch('/game/set_photo_script', { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ script: script })
            });
            const data = await response.json();
            console.log('DEBUG: Photo script response:', data);
            if (data.game_state) {
                console.log('DEBUG: Updating game state with:', data.game_state);
                this.updateGameState(data.game_state);
            }
        } catch (error) {
            console.error('Set photo script error:', error);
        }
    }
    
    async loadGameState() {
        try {
            // Reset game to start fresh each time
            await fetch('/game/reset', { method: 'POST' });
            const response = await fetch('/game/state');
            const gameState = await response.json();
            this.updateGameState(gameState);
            this.updatePatchBadge(0); // Start with 0, let deltas increment it
            // Mini-map removed
            // Ensure darkness hint timer starts on first load
            if (gameState.room_state === 'dark' && !this.hintTimeoutId && !this.hintShown) {
                this.hintTimeoutId = setTimeout(() => {
                    if (this.gameState && this.gameState.room_state === 'dark' && !this.hintShown) {
                        this.addNarration('A disembodied voice: Hey, life is hard, but you\'re really in a pickle. I mean, you are in a jam. Try moving around, or use more of your heightened senses, Superman.', 'environmental');
                        this.hintShown = true;
                    }
                    this.hintTimeoutId = null;
                }, 3 * 60 * 1000);
            }
        } catch (error) {
            console.error('Load game state error:', error);
        }
    }

}

// Initialize game when page loads
document.addEventListener('DOMContentLoaded', () => {
    new VantablackGame();
});
