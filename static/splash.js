// VANTABLACK Splash Page JavaScript

class SplashController {
    constructor() {
        this.audio = document.getElementById('background-music');
        this.howToPlayModal = document.getElementById('how-to-play-modal');
        this.miniGameModal = document.getElementById('mini-game-modal');
        this.timer = document.getElementById('timer');
        this.successMessage = document.getElementById('success-message');
        this.hurryMessage = document.getElementById('hurry-message');
        this.computerScreen = document.getElementById('computer-screen');
        this.redScreen = document.getElementById('red-screen');
        this.scoreValue = document.getElementById('score-value');
        
        // Mini-game state
        this.gameState = {
            currentTarget: null,
            timeLeft: 20,
            gameCount: 0,
            lossCount: 0,
            isPlaying: false,
            timerInterval: null,
            score: 0
        };
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.checkFirstVisit();
        this.startAudio();
    }
    
    setupEventListeners() {
        // Main buttons
        document.getElementById('how-to-play-btn').addEventListener('click', () => this.showHowToPlay());
        document.getElementById('mini-game-btn').addEventListener('click', () => this.showMiniGame());
        
        // Modal controls
        document.getElementById('close-modal').addEventListener('click', () => this.hideModal());
        document.getElementById('start-game-btn').addEventListener('click', () => this.startGame());
        
        
        // Mini-game grid cells
        document.querySelectorAll('.grid-cell').forEach(cell => {
            cell.addEventListener('click', (e) => this.handleGridClick(e));
        });
        
        // Close modals on background click
        this.howToPlayModal.addEventListener('click', (e) => {
            if (e.target === this.howToPlayModal) this.hideModal();
        });
        
        this.miniGameModal.addEventListener('click', (e) => {
            if (e.target === this.miniGameModal) this.hideMiniGame();
        });
    }
    
    checkFirstVisit() {
        const hasVisited = localStorage.getItem('vantablack-visited');
        if (!hasVisited) {
            localStorage.setItem('vantablack-visited', 'true');
            // First visit - show intro animation or special message
            console.log('First visit to VANTABLACK');
        }
    }
    
    startAudio() {
        if (this.audio) {
            this.audio.volume = 0.3;
            this.audio.play().catch(e => {
                console.log('Audio autoplay blocked:', e);
            });
        }
    }
    
    showHowToPlay() {
        this.howToPlayModal.classList.remove('hidden');
    }
    
    showMiniGame() {
        this.miniGameModal.classList.remove('hidden');
        this.startMiniGame();
    }
    
    hideModal() {
        this.howToPlayModal.classList.add('hidden');
    }
    
    hideMiniGame() {
        this.miniGameModal.classList.add('hidden');
        this.stopMiniGame();
    }
    
    startGame() {
        // Fade out audio
        this.fadeAudio();
        
        // Navigate to game
        setTimeout(() => {
            window.location.href = '/game';
        }, 2000);
    }
    
    fadeAudio() {
        if (this.audio) {
            const fadeInterval = setInterval(() => {
                if (this.audio.volume > 0.1) {
                    this.audio.volume -= 0.1;
                } else {
                    this.audio.volume = 0;
                    clearInterval(fadeInterval);
                }
            }, 100);
        }
    }
    
    startMiniGame() {
        this.gameState.isPlaying = true;
        this.gameState.gameCount++;
        
        // Calculate timer based on game count (decreases by 0.5 seconds each game)
        this.gameState.timeLeft = Math.max(5, 20 - (this.gameState.gameCount * 0.5));
        
        // Pick random target
        this.pickRandomTarget();
        
        // Start timer (hidden initially)
        this.startTimer();
    }
    
    pickRandomTarget() {
        const cells = document.querySelectorAll('.grid-cell');
        const randomIndex = Math.floor(Math.random() * cells.length);
        this.gameState.currentTarget = cells[randomIndex].dataset.coord;
        
        // Clear previous selections
        cells.forEach(cell => cell.classList.remove('selected'));
    }
    
    startTimer() {
        // Timer starts hidden
        this.timer.classList.add('hidden');
        this.hurryMessage.classList.add('hidden');
        
        this.gameState.timerInterval = setInterval(() => {
            this.gameState.timeLeft -= 0.1;
            const timeLeft = Math.ceil(this.gameState.timeLeft);
            
            // Show timer only when 10 seconds or less
            if (timeLeft <= 10) {
                this.timer.textContent = timeLeft;
                this.timer.classList.remove('hidden');
            }
            
            // Show hurry message at 5 seconds
            if (timeLeft <= 5 && timeLeft > 0) {
                this.hurryMessage.classList.remove('hidden');
            }
            
            // Time's up
            if (this.gameState.timeLeft <= 0) {
                this.gameOver();
            }
        }, 100);
    }
    
    handleGridClick(event) {
        if (!this.gameState.isPlaying) return;
        
        const clickedCoord = event.target.dataset.coord;
        
        if (clickedCoord === this.gameState.currentTarget) {
            this.correctSelection(event.target);
        } else {
            // Wrong selection - could add penalty or just ignore
            console.log('Wrong selection');
        }
    }
    
    correctSelection(cell) {
        this.gameState.isPlaying = false;
        clearInterval(this.gameState.timerInterval);
        
        // Random score jump between 262-1334
        const scoreJump = Math.floor(Math.random() * (1334 - 262 + 1)) + 262;
        this.gameState.score += scoreJump;
        this.animateScoreUpdate();
        
        // Show success
        cell.classList.add('selected');
        this.showSuccess();
        
        // Hide timer
        this.timer.classList.add('hidden');
        this.hurryMessage.classList.add('hidden');
        
        // Show computer screen message
        setTimeout(() => {
            this.showComputerScreen();
        }, 1000);
        
        // Always start next game after winning (never end on win)
        setTimeout(() => {
            this.startMiniGame();
        }, 2000);
    }
    
    showSuccess() {
        this.successMessage.classList.remove('hidden');
        setTimeout(() => {
            this.successMessage.classList.add('hidden');
        }, 1000);
    }
    
    showComputerScreen() {
        this.computerScreen.classList.remove('hidden');
        setTimeout(() => {
            this.computerScreen.classList.add('hidden');
        }, 500);
    }
    
    updateScoreDisplay() {
        if (this.scoreValue) {
            this.scoreValue.textContent = this.gameState.score.toLocaleString();
        }
    }
    
    animateScoreUpdate() {
        const targetScore = this.gameState.score;
        const currentScore = parseInt(this.scoreValue.textContent.replace(/,/g, '') || '0');
        const increment = Math.max(1, Math.floor((targetScore - currentScore) / 20));
        
        const animate = () => {
            if (currentScore < targetScore) {
                const newScore = Math.min(currentScore + increment, targetScore);
                this.scoreValue.textContent = newScore.toLocaleString();
                requestAnimationFrame(animate);
            } else {
                this.scoreValue.textContent = targetScore.toLocaleString();
            }
        };
        animate();
    }
    
    showRedScreen() {
        if (this.redScreen) {
            this.redScreen.classList.remove('hidden');
        }
    }
    
    gameOver() {
        this.gameState.isPlaying = false;
        this.gameState.lossCount++;
        clearInterval(this.gameState.timerInterval);
        this.timer.classList.add('hidden');
        this.hurryMessage.classList.add('hidden');
        
        // Show red screen
        this.showRedScreen();
        
        // Redirect to main game after delay
        setTimeout(() => {
            this.endMiniGame();
        }, 3000);
    }
    
    endMiniGame() {
        this.gameState.isPlaying = false;
        clearInterval(this.gameState.timerInterval);
        
        // Hide mini-game and start main game
        setTimeout(() => {
            this.hideMiniGame();
            this.startGame();
        }, 2000);
    }
    
    stopMiniGame() {
        this.gameState.isPlaying = false;
        if (this.gameState.timerInterval) {
            clearInterval(this.gameState.timerInterval);
        }
        this.timer.classList.add('hidden');
        this.successMessage.classList.add('hidden');
        this.hurryMessage.classList.add('hidden');
        this.computerScreen.classList.add('hidden');
        
        // Clear grid
        document.querySelectorAll('.grid-cell').forEach(cell => {
            cell.classList.remove('selected');
        });
        
        // Reset game state
        this.resetMiniGame();
    }
    
    resetMiniGame() {
        this.gameState = {
            currentTarget: null,
            timeLeft: 20,
            gameCount: 0,
            lossCount: 0,
            isPlaying: false,
            timerInterval: null,
            score: 0
        };
        
        // Reset score display
        this.updateScoreDisplay();
        
        // Hide red screen if visible
        if (this.redScreen) {
            this.redScreen.classList.add('hidden');
        }
    }
    
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new SplashController();
});
