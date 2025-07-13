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
            element.innerHTML = '<div class="loading">Loading...</div>';
        }
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
                row.innerHTML = `
                    <td>${Utils.escapeHtml(holding.coin_id)}</td>
                    <td>${Utils.escapeHtml(holding.coin_symbol)}</td>
                    <td>${holding.quantity.toFixed(8)}</td>
                    <td>${holding.average_buy_price ? Utils.formatCurrency(holding.average_buy_price) : 'N/A'}</td>
                    <td>${Utils.escapeHtml(holding.exchange_wallet || 'N/A')}</td>
                    <td>${holding.current_price ? Utils.formatCurrency(holding.current_price) : 'Loading...'}</td>
                    <td>${holding.current_value ? Utils.formatCurrency(holding.current_value) : 'N/A'}</td>
                    <td>
                        <button onclick="portfolioManager.deleteHolding('${holding.id}')" 
                                class="btn btn-danger btn-sm">Delete</button>
                    </td>
                `;
            });
        } else {
            this.holdingsTableBody.innerHTML = 
                '<tr><td colspan="8">No holdings yet. Add one above!</td></tr>';
        }
        
        this.totalValueEl.textContent = Utils.formatCurrency(data.total_value_usd);
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
            
            const data = await response.json();
            
            if (response.ok) {
                Utils.showMessage(this.addHoldingMessageEl, data.msg || 'Holding added!', 'success');
                this.addHoldingForm.reset();
                this.loadPortfolio();
            } else {
                Utils.showMessage(this.addHoldingMessageEl, data.msg || 'Failed to add holding.', 'error');
            }
        } catch (error) {
            Utils.showMessage(this.addHoldingMessageEl, 'Error connecting to server.', 'error');
            console.error('Error adding holding:', error);
        }
    }

    async deleteHolding(holdingId) {
        if (!confirm('Are you sure you want to delete this holding?')) return;
        
        try {
            const response = await ApiService.fetchWithAuth(`${CONFIG.API_BASE_URL}/portfolio/holding/${holdingId}`, {
                method: 'DELETE',
            });
            
            const data = await response.json();
            
            if (response.ok) {
                alert(data.msg || 'Holding deleted successfully');
                this.loadPortfolio();
            } else {
                alert(data.msg || 'Failed to delete holding.');
            }
        } catch (error) {
            alert('Error connecting to server.');
            console.error('Error deleting holding:', error);
        }
    }
}

// Auth Manager
class AuthManager {
    constructor() {
        this.loginForm = document.getElementById('loginForm');
        this.logoutLink = document.getElementById('logoutLink');
        this.loginMessageEl = document.getElementById('loginMessage');
        
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        if (this.loginForm) {
            this.loginForm.addEventListener('submit', (e) => this.handleLogin(e));
        }
        
        if (this.logoutLink) {
            this.logoutLink.addEventListener('click', (e) => this.handleLogout(e));
        }
    }

    async handleLogin(e) {
        e.preventDefault();
        
        const username = e.target.username.value;
        const password = e.target.password.value;
        
        try {
            const response = await fetch(`${CONFIG.API_BASE_URL}/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password }),
            });
            
            const data = await response.json();
            
            if (response.ok) {
                localStorage.setItem(CONFIG.TOKEN_KEY, data.access_token);
                localStorage.setItem(CONFIG.USER_ID_KEY, data.user_id);
                localStorage.setItem(CONFIG.PREMIUM_KEY, data.is_premium);
                ApiService.updateNav();
                window.location.href = '/dashboard';
            } else {
                Utils.showMessage(this.loginMessageEl, data.msg || 'Login failed.', 'error');
            }
        } catch (error) {
            Utils.showMessage(this.loginMessageEl, 'Error connecting to server.', 'error');
            console.error('Login error:', error);
        }
    }

    handleLogout(e) {
        e.preventDefault();
        localStorage.removeItem(CONFIG.TOKEN_KEY);
        localStorage.removeItem(CONFIG.USER_ID_KEY);
        localStorage.removeItem(CONFIG.PREMIUM_KEY);
        ApiService.updateNav();
        window.location.href = '/login';
    }
}

// Data Consent Handler
function handleDataConsent() {
    const consentCheckbox = document.getElementById('dataConsentCheckbox');
    const consented = consentCheckbox.checked;
    
    console.log('User consent for data monetization:', consented);
    
    // TODO: Implement actual consent submission
    // ApiService.fetchWithAuth(`${CONFIG.API_BASE_URL}/user/consent`, {
    //     method: 'POST',
    //     body: JSON.stringify({ data_monetization_consent: consented })
    // }).then(response => response.json()).then(data => {
    //     alert('Preference saved!');
    // }).catch(err => console.error('Failed to save consent', err));
    
    alert('Consent preference (mock) submitted: ' + consented);
}

// Initialize application
document.addEventListener('DOMContentLoaded', () => {
    const authManager = new AuthManager();
    const portfolioManager = new PortfolioManager();
    
    // Make portfolioManager globally available for delete function
    window.portfolioManager = portfolioManager;
    
    ApiService.updateNav();
    
    if (window.location.pathname.includes('/dashboard')) {
        if (!localStorage.getItem(CONFIG.TOKEN_KEY)) {
            window.location.href = '/login';
        } else {
            portfolioManager.loadAvailableCoins();
            portfolioManager.loadPortfolio();
        }
    }
});
