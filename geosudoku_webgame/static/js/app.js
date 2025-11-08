// GeoSudoku Game JavaScript
class GeoSudokuGame {
    constructor(containerId, puzzleData, regionsData, currentState = null) {
        this.container = document.getElementById(containerId);
        this.puzzleData = puzzleData;
        this.regionsData = regionsData;
        this.currentState = currentState || JSON.parse(JSON.stringify(puzzleData));
        this.selectedCell = null;
        this.gameSession = null;
        this.mistakes = 0;
        this.hintsUsed = 0;
        this.gameStartTime = new Date();
        
        this.init();
    }
    
    init() {
        this.createGameBoard();
        this.createNumberPad();
        this.createGameControls();
        this.setupEventListeners();
        this.updateDisplay();
        
        // Auto-save every 30 seconds
        setInterval(() => this.autoSave(), 30000);
    }
    
    createGameBoard() {
        const boardContainer = document.createElement('div');
        boardContainer.className = 'sudoku-board';
        boardContainer.id = 'sudoku-board';
        
        // Create 9x9 grid
        for (let row = 0; row < 9; row++) {
            for (let col = 0; col < 9; col++) {
                const cell = document.createElement('div');
                cell.className = 'sudoku-cell';
                cell.dataset.row = row;
                cell.dataset.col = col;
                cell.setAttribute('draggable', 'false');
                
                // Add region class
                const regionIndex = this.getCellRegion(row, col);
                cell.classList.add(`region-${regionIndex}`);
                
                // Set initial value
                const value = this.currentState[row][col];
                if (value !== 0) {
                    cell.textContent = value;
                    if (this.puzzleData[row][col] !== 0) {
                        cell.classList.add('given');
                    } else {
                        cell.classList.add('user-input');
                    }
                }
                
                // Add click handler
                cell.addEventListener('click', () => this.selectCell(row, col));
                
                boardContainer.appendChild(cell);
            }
        }
        
        this.container.appendChild(boardContainer);
    }
    
    createNumberPad() {
        const numberPadContainer = document.createElement('div');
        numberPadContainer.className = 'number-pad';
        numberPadContainer.innerHTML = `
            <h5>Number Pad</h5>
            <div class="numbers-grid">
                ${Array.from({length: 9}, (_, i) => i + 1).map(num => 
                    `<button class="number-btn" data-number="${num}">${num}</button>`
                ).join('')}
                <button class="number-btn erase-btn" data-number="0">
                    <i class="fas fa-eraser"></i>
                </button>
            </div>
        `;
        
        this.container.appendChild(numberPadContainer);
    }
    
    createGameControls() {
        const controlsContainer = document.createElement('div');
        controlsContainer.className = 'game-controls';
        controlsContainer.innerHTML = `
            <div class="game-info">
                <div class="info-item">
                    <strong>Time:</strong> <span id="game-timer">00:00</span>
                </div>
                <div class="info-item">
                    <strong>Mistakes:</strong> <span id="mistakes-count">${this.mistakes}</span>/3
                </div>
                <div class="info-item">
                    <strong>Hints Used:</strong> <span id="hints-count">${this.hintsUsed}</span>
                </div>
            </div>
            <div class="control-buttons">
                <button class="btn btn-warning btn-sm" id="hint-btn">
                    <i class="fas fa-lightbulb"></i> Hint
                </button>
                <button class="btn btn-secondary btn-sm" id="undo-btn">
                    <i class="fas fa-undo"></i> Undo
                </button>
                <button class="btn btn-info btn-sm" id="save-btn">
                    <i class="fas fa-save"></i> Save
                </button>
                <button class="btn btn-success btn-sm" id="check-btn">
                    <i class="fas fa-check"></i> Check Solution
                </button>
            </div>
        `;
        
        this.container.appendChild(controlsContainer);
    }
    
    setupEventListeners() {
        // Number pad buttons
        document.querySelectorAll('.number-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const number = parseInt(e.target.dataset.number);
                this.placeNumber(number);
            });
        });
        
        // Control buttons
        document.getElementById('hint-btn').addEventListener('click', () => this.giveHint());
        document.getElementById('undo-btn').addEventListener('click', () => this.undo());
        document.getElementById('save-btn').addEventListener('click', () => this.saveGame());
        document.getElementById('check-btn').addEventListener('click', () => this.checkSolution());
        
        // Keyboard input
        document.addEventListener('keydown', (e) => this.handleKeyPress(e));
        
        // Start timer
        this.startTimer();
    }
    
    selectCell(row, col) {
        // Remove previous selection
        document.querySelectorAll('.sudoku-cell').forEach(cell => {
            cell.classList.remove('selected');
        });
        
        // Add selection to new cell
        const cell = document.querySelector(`[data-row="${row}"][data-col="${col}"]`);
        if (cell && !cell.classList.contains('given')) {
            cell.classList.add('selected');
            this.selectedCell = { row, col };
            this.highlightRelatedCells(row, col);
        }
    }
    
    highlightRelatedCells(row, col) {
        document.querySelectorAll('.sudoku-cell').forEach(cell => {
            cell.classList.remove('highlighted');
        });
        
        // Highlight row, column, and region
        for (let i = 0; i < 9; i++) {
            // Row
            const rowCell = document.querySelector(`[data-row="${row}"][data-col="${i}"]`);
            if (rowCell) rowCell.classList.add('highlighted');
            
            // Column
            const colCell = document.querySelector(`[data-row="${i}"][data-col="${col}"]`);
            if (colCell) colCell.classList.add('highlighted');
        }
        
        // Region
        const regionIndex = this.getCellRegion(row, col);
        document.querySelectorAll(`.region-${regionIndex}`).forEach(cell => {
            cell.classList.add('highlighted');
        });
    }
    
    placeNumber(number) {
        if (!this.selectedCell) return;
        
        const { row, col } = this.selectedCell;
        const cell = document.querySelector(`[data-row="${row}"][data-col="${col}"]`);
        
        if (cell.classList.contains('given')) return;
        
        // Save previous state for undo
        this.saveState();
        
        // Place number
        this.currentState[row][col] = number;
        
        if (number === 0) {
            cell.textContent = '';
            cell.classList.remove('user-input', 'error');
        } else {
            cell.textContent = number;
            cell.classList.add('user-input');
            
            // Validate move
            if (this.isValidMove(row, col, number)) {
                cell.classList.remove('error');
            } else {
                cell.classList.add('error');
                this.mistakes++;
                this.updateMistakesDisplay();
                
                if (this.mistakes >= 3) {
                    this.gameOver();
                }
            }
        }
        
        // Check for completion
        if (this.isComplete()) {
            this.gameComplete();
        }
    }
    
    isValidMove(row, col, number) {
        // Check row
        for (let c = 0; c < 9; c++) {
            if (c !== col && this.currentState[row][c] === number) {
                return false;
            }
        }
        
        // Check column
        for (let r = 0; r < 9; r++) {
            if (r !== row && this.currentState[r][col] === number) {
                return false;
            }
        }
        
        // Check region
        const regionCells = this.getRegionCells(this.getCellRegion(row, col));
        for (let cell of regionCells) {
            if ((cell.row !== row || cell.col !== col) && 
                this.currentState[cell.row][cell.col] === number) {
                return false;
            }
        }
        
        return true;
    }
    
    getCellRegion(row, col) {
        // Find which region this cell belongs to
        for (let i = 0; i < this.regionsData.length; i++) {
            const region = this.regionsData[i];
            if (region.cells.some(cell => cell[0] === row && cell[1] === col)) {
                return i;
            }
        }
        return 0; // Default to first region if not found
    }
    
    getRegionCells(regionIndex) {
        if (regionIndex < this.regionsData.length) {
            return this.regionsData[regionIndex].cells.map(cell => ({
                row: cell[0],
                col: cell[1]
            }));
        }
        return [];
    }
    
    giveHint() {
        if (!this.selectedCell) {
            alert('Please select a cell first!');
            return;
        }
        
        const { row, col } = this.selectedCell;
        
        // Find correct number for this cell (this would need actual solution data)
        // For now, just show a message
        this.hintsUsed++;
        this.updateHintsDisplay();
        
        alert('Hint: Try analyzing the row, column, and region constraints!');
    }
    
    undo() {
        // Implement undo functionality
        console.log('Undo functionality to be implemented');
    }
    
    saveGame() {
        if (!this.gameSession) return;
        
        const gameData = {
            current_state: this.currentState,
            is_completed: false
        };
        
        fetch(`/api/games/sessions/${this.gameSession}/save/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify(gameData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.message) {
                this.showMessage('Game saved successfully!', 'success');
            }
        })
        .catch(error => {
            console.error('Error saving game:', error);
            this.showMessage('Error saving game', 'error');
        });
    }
    
    autoSave() {
        this.saveGame();
    }
    
    checkSolution() {
        if (this.isComplete() && this.isValid()) {
            this.gameComplete();
        } else {
            this.showMessage('Solution is not complete or contains errors', 'warning');
        }
    }
    
    isComplete() {
        for (let row = 0; row < 9; row++) {
            for (let col = 0; col < 9; col++) {
                if (this.currentState[row][col] === 0) {
                    return false;
                }
            }
        }
        return true;
    }
    
    isValid() {
        for (let row = 0; row < 9; row++) {
            for (let col = 0; col < 9; col++) {
                const value = this.currentState[row][col];
                if (value !== 0 && !this.isValidMove(row, col, value)) {
                    return false;
                }
            }
        }
        return true;
    }
    
    gameComplete() {
        this.showMessage('Congratulations! Puzzle completed!', 'success');
        
        // Save completed game
        const gameData = {
            current_state: this.currentState,
            is_completed: true
        };
        
        fetch(`/api/games/sessions/${this.gameSession}/save/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify(gameData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.score) {
                this.showMessage(`Final Score: ${data.score}`, 'info');
            }
        });
    }
    
    gameOver() {
        this.showMessage('Game Over! Too many mistakes.', 'error');
    }
    
    startTimer() {
        setInterval(() => {
            const now = new Date();
            const elapsed = Math.floor((now - this.gameStartTime) / 1000);
            const minutes = Math.floor(elapsed / 60);
            const seconds = elapsed % 60;
            
            document.getElementById('game-timer').textContent = 
                `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        }, 1000);
    }
    
    updateMistakesDisplay() {
        document.getElementById('mistakes-count').textContent = this.mistakes;
    }
    
    updateHintsDisplay() {
        document.getElementById('hints-count').textContent = this.hintsUsed;
    }
    
    updateDisplay() {
        this.updateMistakesDisplay();
        this.updateHintsDisplay();
    }
    
    handleKeyPress(e) {
        if (this.selectedCell) {
            const key = e.key;
            if (key >= '1' && key <= '9') {
                this.placeNumber(parseInt(key));
            } else if (key === 'Delete' || key === 'Backspace') {
                this.placeNumber(0);
            }
        }
    }
    
    saveState() {
        // Save current state for undo functionality
        // Implementation would store previous states
    }
    
    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]').value;
    }
    
    showMessage(message, type = 'info') {
        // Create a toast or alert message
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        // Add to top of container
        this.container.insertBefore(alertDiv, this.container.firstChild);
        
        // Auto-remove after 3 seconds
        setTimeout(() => {
            alertDiv.remove();
        }, 3000);
    }
}

// Utility functions
function initializeGame(puzzleId) {
    // Initialize a new game session
    fetch(`/api/games/puzzles/${puzzleId}/session/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        }
    })
    .then(response => response.json())
    .then(data => {
        const game = new GeoSudokuGame(
            'game-container',
            data.puzzle_data,
            data.regions_data,
            data.current_state
        );
        game.gameSession = data.session_id;
    })
    .catch(error => {
        console.error('Error initializing game:', error);
    });
}

// Global app functions
const GeoSudokuApp = {
    // Initialize when DOM is loaded
    init() {
        console.log('GeoSudoku App initialized');
        
        // Add smooth scrolling
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                document.querySelector(this.getAttribute('href')).scrollIntoView({
                    behavior: 'smooth'
                });
            });
        });
        
        // Initialize tooltips if Bootstrap is available
        if (typeof bootstrap !== 'undefined') {
            var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
            var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl);
            });
        }
    },
    
    // API helper functions
    async apiCall(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
            }
        };
        
        const mergedOptions = { ...defaultOptions, ...options };
        
        try {
            const response = await fetch(url, mergedOptions);
            return await response.json();
        } catch (error) {
            console.error('API call failed:', error);
            throw error;
        }
    }
};

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    GeoSudokuApp.init();
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { GeoSudokuGame, GeoSudokuApp };
}