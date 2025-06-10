JavaScript


document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = 'http://localhost:5000/api'; // Python backend
    const loginForm = document.getElementById('loginForm');
    const addHoldingForm = document.getElementById('addHoldingForm');
    const holdingsTableBody = document.querySelector('#holdingsTable tbody');
    const totalValueEl = document.getElementById('totalValue');
    const loginMessageEl = document.getElementById('loginMessage');
    const addHoldingMessageEl = document.getElementById('addHoldingMessage');
    const coinSelectEl = document.getElementById('coin_id');

    const loginLink = document.getElementById('loginLink');
    const registerLink = document.getElementById('registerLink');
    const dashboardLink = document.getElementById('dashboardLink');
    const logoutLink = document.getElementById('logoutLink');
    const premiumStatusEl = document.getElementById('userPremiumStatus');
    const premiumFeaturesSection = document.getElementById('premiumFeaturesSection');
    const premiumAnalyticsDataEl = document.getElementById('premiumAnalyticsData');
    const dataConsentEl = document.getElementById('dataConsent');
    const taxIntegrationEl = document.getElementById('taxIntegration');


    function updateNav() {
        const token = localStorage.getItem('jwtToken');
        if (token) {
            loginLink.style.display = 'none';
            registerLink.style.display = 'none';
            dashboardLink.style.display = 'inline';
            logoutLink.style.display = 'inline';
        } else {
            loginLink.style.display = 'inline';
            registerLink.style.display = 'inline';
            dashboardLink.style.display = 'none';
            logoutLink.style.display = 'none';
        }
    }

    async function fetchWithAuth(url, options = {}) {
        const token = localStorage.getItem('jwtToken');
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers,
        };
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        const response = await fetch(url, { ...options, headers });
        if (response.status === 401) { // Unauthorized
            localStorage.removeItem('jwtToken');
            localStorage.removeItem('userId');
            localStorage.removeItem('isPremium');
            updateNav();
            if (window.location.pathname !== '/login' && window.location.pathname !== '/register') {
                window.location.href = '/login'; // Redirect to login
            }
        }
        return response;
    }

    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = e.target.username.value;
            const password = e.target.password.value;
            try {
                const response = await fetch(`${API_BASE_URL}/login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password }),
                });
                const data = await response.json();
                if (response.ok) {
                    localStorage.setItem('jwtToken', data.access_token);
                    localStorage.setItem('userId', data.user_id);
                    localStorage.setItem('isPremium', data.is_premium);
                    updateNav();
                    window.location.href = '/dashboard';
                } else {
                    loginMessageEl.textContent = data.msg || 'Login failed.';
                }
            } catch (error) {
                loginMessageEl.textContent = 'Error connecting to server.';
                console.error('Login error:', error);
            }
        });
    }

    if (logoutLink) {
        logoutLink.addEventListener('click', (e) => {
            e.preventDefault();
            localStorage.removeItem('jwtToken');
            localStorage.removeItem('userId');
            localStorage.removeItem('isPremium');
            updateNav();
            // No backend call for logout with JWT, just clear client-side token
            window.location.href = '/login';
        });
    }

    async function loadPortfolio() {
        if (!holdingsTableBody || !totalValueEl) return; // Not on dashboard page

        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/portfolio`);
            if (!response.ok) {
                holdingsTableBody.innerHTML = `<tr><td colspan="8">Error loading portfolio: ${response.statusText}</td></tr>`;
                if (response.status === 401) window.location.href = '/login'; // Redirect if unauthorized
                return;
            }
            const data = await response.json();

            holdingsTableBody.innerHTML = ''; // Clear previous data
            if (data.holdings && data.holdings.length > 0) {
                data.holdings.forEach(h => {
                    const row = holdingsTableBody.insertRow();
                    row.insertCell().textContent = h.coin_id;
                    row.insertCell().textContent = h.coin_symbol;
                    row.insertCell().textContent = h.quantity.toFixed(8);
                    row.insertCell().textContent = h.average_buy_price ? `$${h.average_buy_price.toFixed(2)}` : 'N/A';
                    row.insertCell().textContent = h.exchange_wallet || 'N/A';
                    row.insertCell().textContent = h.current_price ? `$${h.current_price.toFixed(2)}` : 'Loading...';
                    row.insertCell().textContent = h.current_value ? `$${h.current_value.toFixed(2)}` : 'N/A';
                    const actionsCell = row.insertCell();
                    const deleteBtn = document.createElement('button');
                    deleteBtn.textContent = 'Delete';
                    deleteBtn.onclick = () => deleteHolding(h.id); // Implement deleteHolding
                    actionsCell.appendChild(deleteBtn);
                });
            } else {
                holdingsTableBody.innerHTML = '<tr><td colspan="8">No holdings yet. Add one above!</td></tr>';
            }
            totalValueEl.textContent = `$${data.total_value_usd.toFixed(2)}`;

            // Handle premium features display
            const isPremium = localStorage.getItem('isPremium') === 'true' || data.is_premium;
            premiumStatusEl.textContent = isPremium ? 'Premium' : 'Basic';
            if (isPremium) {
                premiumFeaturesSection.style.display = 'block';
                premiumAnalyticsDataEl.textContent = JSON.stringify(data.premium_analytics, null, 2);
                taxIntegrationEl.style.display = 'block'; // Show premium integration
            } else {
                premiumFeaturesSection.style.display = 'none';
                taxIntegrationEl.style.display = 'none'; // Hide premium integration
            }
             // Show data consent option (could be for all users or tied to specific features)
            dataConsentEl.style.display = 'block';

        } catch (error) {
            holdingsTableBody.innerHTML = `<tr><td colspan="8">Failed to load portfolio. Check connection.</td></tr>`;
            console.error('Error loading portfolio:', error);
        }
    }

    async function loadAvailableCoins() {
        if (!coinSelectEl) return;
        try {
            // This endpoint in Python backend does not require auth in the example,
            // but you might want to protect it or cache its response.
            const response = await fetch(`${API_BASE_URL}/crypto_prices_available`);
            if (!response.ok) {
                console.error("Failed to load available coins");
                coinSelectEl.innerHTML = '<option value="">Error loading coins</option>';
                return;
            }
            const coins = await response.json();
            coinSelectEl.innerHTML = '<option value="">Select a coin</option>'; // Clear loading
            coins.forEach(coin => {
                const option = document.createElement('option');
                option.value = coin.id; // Use coin 'id' (e.g., 'bitcoin')
                option.textContent = `${coin.name} (${coin.symbol.toUpperCase()})`;
                option.dataset.symbol = coin.symbol; // Store symbol for later use
                coinSelectEl.appendChild(option);
            });
        } catch (error) {
            console.error('Error loading available coins:', error);
            coinSelectEl.innerHTML = '<option value="">Error loading coins</option>';
        }
    }


    if (addHoldingForm) {
        addHoldingForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const selectedOption = coinSelectEl.options[coinSelectEl.selectedIndex];
            const coin_id = selectedOption.value;
            const coin_symbol = selectedOption.dataset.symbol; // Get symbol from data attribute

            const holdingData = {
                coin_id: coin_id,
                coin_symbol: coin_symbol,
                quantity: parseFloat(e.target.quantity.value),
                average_buy_price: parseFloat(e.target.average_buy_price.value) || null,
                exchange_wallet: e.target.exchange_wallet.value || null
            };

            try {
                const response = await fetchWithAuth(`${API_BASE_URL}/portfolio/add_holding`, {
                    method: 'POST',
                    body: JSON.stringify(holdingData),
                });
                const data = await response.json();
                if (response.ok) {
                    addHoldingMessageEl.textContent = data.msg || 'Holding added!';
                    addHoldingMessageEl.style.color = 'green';
                    addHoldingForm.reset();
                    loadPortfolio(); // Refresh portfolio
                } else {
                    addHoldingMessageEl.textContent = data.msg || 'Failed to add holding.';
                    addHoldingMessageEl.style.color = 'red';
                }
            } catch (error) {
                addHoldingMessageEl.textContent = 'Error connecting to server.';
                addHoldingMessageEl.style.color = 'red';
                console.error('Error adding holding:', error);
            }
        });
    }

    // Function to delete holding (basic implementation)
    async function deleteHolding(holdingId) {
        if (!confirm('Are you sure you want to delete this holding?')) return;
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/portfolio/holding/${holdingId}`, { // Assuming this endpoint exists
                method: 'DELETE',
            });
            const data = await response.json();
            if (response.ok) {
                alert(data.msg || 'Holding deleted successfully');
                loadPortfolio(); // Refresh
            } else {
                alert(data.msg || 'Failed to delete holding.');
            }
        } catch (error) {
            alert('Error connecting to server.');
            console.error('Error deleting holding:', error);
        }
    }

    // Initial setup
    updateNav();
    if (window.location.pathname.includes('/dashboard')) {
        if (!localStorage.getItem('jwtToken')) {
            window.location.href = '/login'; // Redirect if not logged in
        } else {
            loadAvailableCoins();
            loadPortfolio();
        }
    }
});

// Function for data consent (conceptual)
function handleDataConsent() {
    const consentCheckbox = document.getElementById('dataConsentCheckbox');
    const consented = consentCheckbox.checked;
    console.log('User consent for data monetization:', consented);
    // Here you would send this preference to your backend to store it.
    // Example:
    // fetchWithAuth(`${API_BASE_URL}/user/consent`, {
    //     method: 'POST',
    //     body: JSON.stringify({ data_monetization_consent: consented })
    // }).then(response => response.json()).then(data => {
    //     alert('Preference saved!');
    // }).catch(err => console.error('Failed to save consent', err));
    alert('Consent preference (mock) submitted: ' + consented);
}
