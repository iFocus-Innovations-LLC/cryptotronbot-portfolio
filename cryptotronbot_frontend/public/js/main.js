// Configuration
const CONFIG = {
    API_BASE_URL: window.location.hostname === 'localhost' 
        ? 'http://localhost:5000/api' 
        : '/api', // Production URL
    TOKEN_KEY: 'jwtToken',
    USER_ID_KEY: 'userId',
    PREMIUM_KEY: 'isPremium'
};

// Utility functions
const Utils = {
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    formatCurrency(amount) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(amount || 0);
    },

    formatPercentage(amount) {
        return new Intl.NumberFormat('en-US', {
            style: 'percent',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(amount || 0);
    },

    showMessage(element, message, type = 'info') {
        if (!element) return;
        element.textContent = message;
        element.className = `message message-${type}`;
        element.style.display = 'block';
        
        // Auto-hide success messages
        if (type === 'success') {
            setTimeout(() => {
                element.style.display = 'none';
            }, 3000);
        }
    },

    showLoading(element) {
        if (element) {
            element.innerHTML = '<div class="loading"></div><span>Loading...</span>';
        }
    },

    addLoadingState(button) {
        if (button) {
            button.disabled = true;
            button.innerHTML = '<div class="loading"></div> Processing...';
        }
    },

    removeLoadingState(button, originalText) {
        if (button) {
            button.disabled = false;
            button.textContent = originalText;
        }
    },

    animateValue(element, start, end, duration = 1000) {
        const startTime = performance.now();
        const startValue = parseFloat(start) || 0;
        const endValue = parseFloat(end) || 0;
        
        function updateValue(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            const currentValue = startValue + (endValue - startValue) * progress;
            element.textContent = Utils.formatCurrency(currentValue);
            
            if (progress < 1) {
                requestAnimationFrame(updateValue);
            }
        }
        
        requestAnimationFrame(updateValue);
    }
};

// API Service
class ApiService {
    static async fetchWithAuth(url, options = {}) {
        const token = localStorage.getItem(CONFIG.TOKEN_KEY);
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers,
        };
        
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        
        try {
            const response = await fetch(url, { ...options, headers });
            
            if (response.status === 401) {
                localStorage.removeItem(CONFIG.TOKEN_KEY);
                localStorage.removeItem(CONFIG.USER_ID_KEY);
                localStorage.removeItem(CONFIG.PREMIUM_KEY);
                this.updateNav();
                
                if (!window.location.pathname.includes('/login') && 
                    !window.location.pathname.includes('/register')) {
                    window.location.href = '/login';
                }
            }
            
            return response;
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }

    static updateNav() {
        const token = localStorage.getItem(CONFIG.TOKEN_KEY);
        const elements = ['loginLink', 'registerLink', 'dashboardLink', 'logoutLink'];
        
        elements.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.style.display = token ? 
                    (id.includes('login') || id.includes('register') ? 'none' : 'inline') :
                    (id.includes('login') || id.includes('register') ? 'inline' : 'none');
            }
        });
    }
}

// Portfolio Manager
class PortfolioManager {
    constructor() {
        this.holdingsTableBody = document.querySelector('#holdingsTable tbody');
        this.totalValueEl = document.getElementById('totalValue');
        this.addHoldingForm = document.getElementById('addHoldingForm');
        this.addHoldingMessageEl = document.getElementById('addHoldingMessage');
        this.coinSelectEl = document.getElementById('coin_id');
        this.submitButton = this.addHoldingForm?.querySelector('button[type="submit"]');
        
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        if (this.addHoldingForm) {
            this.addHoldingForm.addEventListener('submit', (e) => this.handleAddHolding(e));
        }
    }

    async loadPortfolio() {
        if (!this.holdingsTableBody || !this.totalValueEl) return;

        try {
            Utils.showLoading(this.holdingsTableBody);
            
            const response = await ApiService.fetchWithAuth(`${CONFIG.API_BASE_URL}/portfolio`);
            
            if (!response.ok) {
                this.holdingsTableBody.innerHTML = 
                    `<tr><td colspan="8">Error loading portfolio: ${response.statusText}</td></tr>`;
                return;
            }
            
            const data = await response.json();
            this.renderPortfolio(data);
            this.updatePremiumFeatures(data);
            
        } catch (error) {
            this.holdingsTableBody.innerHTML = 
                '<tr><td colspan="8">Failed to load portfolio. Check connection.</td></tr>';
            console.error('Error loading portfolio:', error);
        }
    }

    renderPortfolio(data) {
        this.holdingsTableBody.innerHTML = '';
        
        if (data.holdings && data.holdings.length > 0) {
            data.holdings.forEach(holding => {
                const row = this.holdingsTableBody.insertRow();
                const profitLoss = holding.current_value && holding.average_buy_price ? 
                    (holding.current_value - (holding.quantity * holding.average_buy_price)) : 0;
                const profitLossPercent = holding.average_buy_price && holding.current_price ? 
                    ((holding.current_price - holding.average_buy_price) / holding.average_buy_price) : 0;
                
                row.innerHTML = `
                    <td>
                        <strong>${Utils.escapeHtml(holding.coin_id)}</strong>
                    </td>
                    <td>
                        <span class="status-badge status-basic">${Utils.escapeHtml(holding.coin_symbol)}</span>
                    </td>
                    <td>${holding.quantity.toFixed(8)}</td>
                    <td>${holding.average_buy_price ? Utils.formatCurrency(holding.average_buy_price) : 'N/A'}</td>
                    <td>${Utils.escapeHtml(holding.exchange_wallet || 'N/A')}</td>
                    <td>${holding.current_price ? Utils.formatCurrency(holding.current_price) : 'Loading...'}</td>
                    <td>
                        <strong>${holding.current_value ? Utils.formatCurrency(holding.current_value) : 'N/A'}</strong>
                        ${profitLoss !== 0 ? `
                            <br><small class="${profitLoss > 0 ? 'text-success' : 'text-danger'}">
                                ${profitLoss > 0 ? '+' : ''}${Utils.formatCurrency(profitLoss)} 
                                (${Utils.formatPercentage(profitLossPercent)})
                            </small>
                        ` : ''}
                    </td>
                    <td>
                        <button onclick="portfolioManager.deleteHolding('${holding.id}')" 
                                class="btn btn-danger btn-sm">Delete</button>
                    </td>
                `;
            });
        } else {
            this.holdingsTableBody.innerHTML = `
                <tr>
                    <td colspan="8" style="text-align: center; padding: 2rem;">
                        <div style="color: var(--text-secondary);">
                            <h4>No holdings yet</h4>
                            <p>Add your first cryptocurrency holding above!</p>
                        </div>
                    </td>
                </tr>
            `;
        }
        
        // Animate the total value change
        const currentValue = parseFloat(this.totalValueEl.textContent.replace(/[$,]/g, '')) || 0;
        Utils.animateValue(this.totalValueEl, currentValue, data.total_value_usd);
    }

    updatePremiumFeatures(data) {
        const isPremium = localStorage.getItem(CONFIG.PREMIUM_KEY) === 'true' || data.is_premium;
        const premiumStatusEl = document.getElementById('userPremiumStatus');
        const premiumFeaturesSection = document.getElementById('premiumFeaturesSection');
        const premiumAnalyticsDataEl = document.getElementById('premiumAnalyticsData');
        const taxIntegrationEl = document.getElementById('taxIntegration');
        const dataConsentEl = document.getElementById('dataConsent');

        if (premiumStatusEl) {
            premiumStatusEl.textContent = isPremium ? 'Premium' : 'Basic';
            premiumStatusEl.className = `status-badge ${isPremium ? 'status-premium' : 'status-basic'}`;
        }

        if (isPremium && premiumFeaturesSection) {
            premiumFeaturesSection.style.display = 'block';
            if (premiumAnalyticsDataEl) {
                premiumAnalyticsDataEl.textContent = JSON.stringify(data.premium_analytics, null, 2);
            }
        } else if (premiumFeaturesSection) {
            premiumFeaturesSection.style.display = 'none';
        }

        if (taxIntegrationEl) {
            taxIntegrationEl.style.display = isPremium ? 'block' : 'none';
        }

        if (dataConsentEl) {
            dataConsentEl.style.display = 'block';
        }
    }

    async loadAvailableCoins() {
        if (!this.coinSelectEl) return;
        
        try {
            const response = await fetch(`${CONFIG.API_BASE_URL}/crypto_prices_available`);
            
            if (!response.ok) {
                console.error("Failed to load available coins");
                this.coinSelectEl.innerHTML = '<option value="">Error loading coins</option>';
                return;
            }
            
            const coins = await response.json();
            this.coinSelectEl.innerHTML = '<option value="">Select a coin</option>';
            
            coins.forEach(coin => {
                const option = document.createElement('option');
                option.value = coin.id;
                option.textContent = `${Utils.escapeHtml(coin.name)} (${coin.symbol.toUpperCase()})`;
                option.dataset.symbol = coin.symbol;
                this.coinSelectEl.appendChild(option);
            });
        } catch (error) {
            console.error('Error loading available coins:', error);
            this.coinSelectEl.innerHTML = '<option value="">Error loading coins</option>';
        }
    }

    async handleAddHolding(e) {
        e.preventDefault();
        
        const selectedOption = this.coinSelectEl.options[this.coinSelectEl.selectedIndex];
        const coin_id = selectedOption.value;
        const coin_symbol = selectedOption.dataset.symbol;

        if (!coin_id) {
            Utils.showMessage(this.addHoldingMessageEl, 'Please select a coin', 'error');
            return;
        }

        const originalButtonText = this.submitButton?.textContent || 'Add Holding';
        Utils.addLoadingState(this.submitButton);

        const holdingData = {
            coin_id: coin_id,
            coin_symbol: coin_symbol,
            quantity: parseFloat(e.target.quantity.value),
            average_buy_price: parseFloat(e.target.average_buy_price.value) || null,
            exchange_wallet: e.target.exchange_wallet.value || null
        };

        try {
            const response = await ApiService.fetchWithAuth(`${CONFIG.API_BASE_URL}/portfolio/add_holding`, {
                method: 'POST',
                body: JSON.stringify(holdingData),
            });

            if (response.ok) {
                Utils.showMessage(this.addHoldingMessageEl, 'Holding added successfully!', 'success');
                e.target.reset();
                this.loadPortfolio(); // Refresh the portfolio
            } else {
                const errorData = await response.json();
                Utils.showMessage(this.addHoldingMessageEl, 
                    errorData.error || 'Failed to add holding', 'error');
            }
        } catch (error) {
            Utils.showMessage(this.addHoldingMessageEl, 
                'Network error. Please try again.', 'error');
            console.error('Error adding holding:', error);
        } finally {
            Utils.removeLoadingState(this.submitButton, originalButtonText);
        }
    }

    async deleteHolding(holdingId) {
        if (!confirm('Are you sure you want to delete this holding?')) {
            return;
        }

        try {
            const response = await ApiService.fetchWithAuth(`${CONFIG.API_BASE_URL}/portfolio/delete_holding/${holdingId}`, {
                method: 'DELETE',
            });

            if (response.ok) {
                Utils.showMessage(this.addHoldingMessageEl, 'Holding deleted successfully!', 'success');
                this.loadPortfolio(); // Refresh the portfolio
            } else {
                const errorData = await response.json();
                Utils.showMessage(this.addHoldingMessageEl, 
                    errorData.error || 'Failed to delete holding', 'error');
            }
        } catch (error) {
            Utils.showMessage(this.addHoldingMessageEl, 
                'Network error. Please try again.', 'error');
            console.error('Error deleting holding:', error);
        }
    }
}

// Auth Manager
class AuthManager {
    constructor() {
        this.loginForm = document.getElementById('loginForm');
        this.loginMessageEl = document.getElementById('loginMessage');
        this.submitButton = this.loginForm?.querySelector('button[type="submit"]');
        
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        if (this.loginForm) {
            this.loginForm.addEventListener('submit', (e) => this.handleLogin(e));
        }

        const logoutLink = document.getElementById('logoutLink');
        if (logoutLink) {
            logoutLink.addEventListener('click', (e) => this.handleLogout(e));
        }
    }

    async handleLogin(e) {
        e.preventDefault();
        
        const originalButtonText = this.submitButton?.textContent || 'Login';
        Utils.addLoadingState(this.submitButton);

        const formData = {
            username: e.target.username.value,
            password: e.target.password.value
        };

        try {
            const response = await fetch(`${CONFIG.API_BASE_URL}/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });

            if (response.ok) {
                const data = await response.json();
                localStorage.setItem(CONFIG.TOKEN_KEY, data.token);
                localStorage.setItem(CONFIG.USER_ID_KEY, data.user_id);
                localStorage.setItem(CONFIG.PREMIUM_KEY, data.is_premium || false);
                
                Utils.showMessage(this.loginMessageEl, 'Login successful! Redirecting...', 'success');
                ApiService.updateNav();
                
                setTimeout(() => {
                    window.location.href = '/dashboard';
                }, 1000);
            } else {
                const errorData = await response.json();
                Utils.showMessage(this.loginMessageEl, 
                    errorData.error || 'Login failed', 'error');
            }
        } catch (error) {
            Utils.showMessage(this.loginMessageEl, 
                'Network error. Please try again.', 'error');
            console.error('Login error:', error);
        } finally {
            Utils.removeLoadingState(this.submitButton, originalButtonText);
        }
    }

    handleLogout(e) {
        e.preventDefault();
        localStorage.removeItem(CONFIG.TOKEN_KEY);
        localStorage.removeItem(CONFIG.USER_ID_KEY);
        localStorage.removeItem(CONFIG.PREMIUM_KEY);
        ApiService.updateNav();
        window.location.href = '/';
    }
}

// Data Consent Handler
function handleDataConsent() {
    const checkbox = document.getElementById('dataConsentCheckbox');
    const message = checkbox.checked ? 
        'Thank you for helping improve CryptoTronBot!' : 
        'Your preference has been saved.';
    
    alert(message);
    // In a real implementation, you would send this to your backend
}

// Initialize everything when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize managers
    window.portfolioManager = new PortfolioManager();
    window.authManager = new AuthManager();
    
    // Update navigation based on auth status
    ApiService.updateNav();
    
    // Load portfolio if on dashboard page
    if (window.location.pathname === '/dashboard') {
        portfolioManager.loadPortfolio();
        portfolioManager.loadAvailableCoins();
    }
});
