# cryptotronbot_backend/utils/defi_api.py
# DeFi API integration utilities for stablecoin functionality

import requests
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

# API Configuration
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"
ETHERSCAN_API_URL = "https://api.etherscan.io/api"
BINANCE_API_URL = "https://api.binance.com/api/v3"

# Stablecoin configurations
STABLECOINS = {
    'USDT': {
        'coingecko_id': 'tether',
        'symbol': 'USDT',
        'name': 'Tether',
        'ethereum_contract': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
        'chains': ['ethereum', 'tron', 'bsc', 'polygon']
    },
    'USDC': {
        'coingecko_id': 'usd-coin',
        'symbol': 'USDC',
        'name': 'USD Coin',
        'ethereum_contract': '0xA0b86a33E6441c8C673f4c8e4e8c4e8c4e8c4e8c',
        'chains': ['ethereum', 'polygon', 'avalanche', 'solana']
    },
    'DAI': {
        'coingecko_id': 'dai',
        'symbol': 'DAI',
        'name': 'Dai',
        'ethereum_contract': '0x6B175474E89094C44Da98b954EedeAC495271d0F',
        'chains': ['ethereum', 'polygon', 'bsc']
    },
    'BUSD': {
        'coingecko_id': 'binance-usd',
        'symbol': 'BUSD',
        'name': 'Binance USD',
        'ethereum_contract': '0x4Fabb145d64652a948d72533023f6E7A623C7C53',
        'chains': ['ethereum', 'bsc']
    },
    'FRAX': {
        'coingecko_id': 'frax',
        'symbol': 'FRAX',
        'name': 'Frax',
        'ethereum_contract': '0x853d955aCEf822Db058eb8505911ED77F175b99e',
        'chains': ['ethereum', 'polygon', 'avalanche']
    }
}

class DeFiAPIClient:
    """
    Client for integrating with various DeFi APIs for stablecoin data and functionality
    """
    
    def __init__(self, etherscan_api_key: Optional[str] = None):
        self.etherscan_api_key = etherscan_api_key
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'CryptoTronBot/1.0'
        })
    
    def get_stablecoin_prices(self, stablecoin_symbols: List[str]) -> Dict[str, Optional[float]]:
        """
        Get current prices for specified stablecoins using CoinGecko API
        
        Args:
            stablecoin_symbols: List of stablecoin symbols (e.g., ['USDT', 'USDC'])
            
        Returns:
            Dictionary mapping symbols to current USD prices
        """
        try:
            # Map symbols to CoinGecko IDs
            coin_ids = []
            symbol_to_id = {}
            
            for symbol in stablecoin_symbols:
                if symbol in STABLECOINS:
                    coin_id = STABLECOINS[symbol]['coingecko_id']
                    coin_ids.append(coin_id)
                    symbol_to_id[coin_id] = symbol
            
            if not coin_ids:
                return {symbol: None for symbol in stablecoin_symbols}
            
            # Fetch prices from CoinGecko
            params = {
                'ids': ','.join(coin_ids),
                'vs_currencies': 'usd'
            }
            
            response = self.session.get(
                f"{COINGECKO_API_URL}/simple/price",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Map back to symbols
            result = {}
            for coin_id, price_data in data.items():
                symbol = symbol_to_id.get(coin_id)
                if symbol and 'usd' in price_data:
                    result[symbol] = price_data['usd']
            
            # Fill in None for missing symbols
            for symbol in stablecoin_symbols:
                if symbol not in result:
                    result[symbol] = None
                    
            return result
            
        except Exception as e:
            logger.error(f"Error fetching stablecoin prices: {e}")
            return {symbol: None for symbol in stablecoin_symbols}
    
    def get_stablecoin_market_data(self, stablecoin_symbol: str) -> Dict[str, Any]:
        """
        Get comprehensive market data for a specific stablecoin
        
        Args:
            stablecoin_symbol: Symbol of the stablecoin (e.g., 'USDT')
            
        Returns:
            Dictionary containing market data
        """
        try:
            if stablecoin_symbol not in STABLECOINS:
                return {}
            
            coin_id = STABLECOINS[stablecoin_symbol]['coingecko_id']
            
            response = self.session.get(
                f"{COINGECKO_API_URL}/coins/{coin_id}",
                params={'localization': 'false', 'tickers': 'false', 'community_data': 'false'},
                timeout=15
            )
            response.raise_for_status()
            
            data = response.json()
            
            market_data = data.get('market_data', {})
            
            return {
                'symbol': stablecoin_symbol,
                'name': data.get('name'),
                'current_price': market_data.get('current_price', {}).get('usd'),
                'market_cap': market_data.get('market_cap', {}).get('usd'),
                'total_volume': market_data.get('total_volume', {}).get('usd'),
                'circulating_supply': market_data.get('circulating_supply'),
                'total_supply': market_data.get('total_supply'),
                'price_change_24h': market_data.get('price_change_24h'),
                'price_change_percentage_24h': market_data.get('price_change_percentage_24h'),
                'market_cap_rank': market_data.get('market_cap_rank'),
                'last_updated': market_data.get('last_updated')
            }
            
        except Exception as e:
            logger.error(f"Error fetching market data for {stablecoin_symbol}: {e}")
            return {}
    
    def get_ethereum_stablecoin_balance(self, wallet_address: str, stablecoin_symbol: str) -> Optional[float]:
        """
        Get stablecoin balance for an Ethereum wallet address
        
        Args:
            wallet_address: Ethereum wallet address
            stablecoin_symbol: Symbol of the stablecoin
            
        Returns:
            Balance in stablecoin units or None if error
        """
        try:
            if not self.etherscan_api_key:
                logger.warning("Etherscan API key not provided")
                return None
                
            if stablecoin_symbol not in STABLECOINS:
                return None
            
            contract_address = STABLECOINS[stablecoin_symbol]['ethereum_contract']
            
            params = {
                'module': 'account',
                'action': 'tokenbalance',
                'contractaddress': contract_address,
                'address': wallet_address,
                'tag': 'latest',
                'apikey': self.etherscan_api_key
            }
            
            response = self.session.get(ETHERSCAN_API_URL, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') == '1':
                # Convert from wei to token units (most stablecoins use 6 or 18 decimals)
                balance_wei = int(data.get('result', '0'))
                # USDT and USDC typically use 6 decimals, DAI uses 18
                decimals = 6 if stablecoin_symbol in ['USDT', 'USDC'] else 18
                balance = balance_wei / (10 ** decimals)
                return balance
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching Ethereum balance for {stablecoin_symbol}: {e}")
            return None
    
    def get_stablecoin_yield_opportunities(self) -> List[Dict[str, Any]]:
        """
        Get available yield opportunities for stablecoins
        This is a placeholder for integration with DeFi yield platforms like Kiln, Iron.xyz, etc.
        
        Returns:
            List of yield opportunities
        """
        # Placeholder data - in real implementation, this would integrate with:
        # - Kiln DeFi API for aggregated yields
        # - Iron.xyz API for yield optimization
        # - Aave, Compound, and other DeFi protocols
        
        mock_opportunities = [
            {
                'protocol': 'Aave',
                'stablecoin': 'USDC',
                'apy': 4.25,
                'risk_level': 'Low',
                'minimum_deposit': 100,
                'description': 'Lending USDC on Aave protocol'
            },
            {
                'protocol': 'Compound',
                'stablecoin': 'DAI',
                'apy': 3.85,
                'risk_level': 'Low',
                'minimum_deposit': 50,
                'description': 'Supply DAI to Compound lending pool'
            },
            {
                'protocol': 'Curve',
                'stablecoin': 'USDT',
                'apy': 5.12,
                'risk_level': 'Medium',
                'minimum_deposit': 1000,
                'description': 'USDT liquidity provision on Curve'
            }
        ]
        
        return mock_opportunities
    
    def get_stablecoin_trading_pairs(self, stablecoin_symbol: str) -> List[Dict[str, Any]]:
        """
        Get available trading pairs for a stablecoin from Binance
        
        Args:
            stablecoin_symbol: Symbol of the stablecoin
            
        Returns:
            List of trading pairs with volume and price data
        """
        try:
            # Get 24hr ticker statistics from Binance
            response = self.session.get(
                f"{BINANCE_API_URL}/ticker/24hr",
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Filter for pairs involving the stablecoin
            relevant_pairs = []
            for ticker in data:
                symbol = ticker['symbol']
                if stablecoin_symbol in symbol:
                    relevant_pairs.append({
                        'symbol': symbol,
                        'price': float(ticker['lastPrice']),
                        'volume': float(ticker['volume']),
                        'price_change_percent': float(ticker['priceChangePercent']),
                        'high_price': float(ticker['highPrice']),
                        'low_price': float(ticker['lowPrice'])
                    })
            
            # Sort by volume (descending)
            relevant_pairs.sort(key=lambda x: x['volume'], reverse=True)
            
            return relevant_pairs[:10]  # Return top 10 pairs
            
        except Exception as e:
            logger.error(f"Error fetching trading pairs for {stablecoin_symbol}: {e}")
            return []
    
    def analyze_stablecoin_stability(self, stablecoin_symbol: str, days: int = 30) -> Dict[str, Any]:
        """
        Analyze the price stability of a stablecoin over a specified period
        
        Args:
            stablecoin_symbol: Symbol of the stablecoin
            days: Number of days to analyze
            
        Returns:
            Dictionary containing stability metrics
        """
        try:
            if stablecoin_symbol not in STABLECOINS:
                return {}
            
            coin_id = STABLECOINS[stablecoin_symbol]['coingecko_id']
            
            # Get historical price data
            response = self.session.get(
                f"{COINGECKO_API_URL}/coins/{coin_id}/market_chart",
                params={
                    'vs_currency': 'usd',
                    'days': days,
                    'interval': 'daily'
                },
                timeout=15
            )
            response.raise_for_status()
            
            data = response.json()
            prices = [price[1] for price in data.get('prices', [])]
            
            if not prices:
                return {}
            
            # Calculate stability metrics
            avg_price = sum(prices) / len(prices)
            max_price = max(prices)
            min_price = min(prices)
            price_range = max_price - min_price
            
            # Calculate standard deviation
            variance = sum((price - avg_price) ** 2 for price in prices) / len(prices)
            std_deviation = variance ** 0.5
            
            # Calculate coefficient of variation (relative volatility)
            cv = (std_deviation / avg_price) * 100 if avg_price > 0 else 0
            
            return {
                'symbol': stablecoin_symbol,
                'period_days': days,
                'average_price': round(avg_price, 6),
                'max_price': round(max_price, 6),
                'min_price': round(min_price, 6),
                'price_range': round(price_range, 6),
                'standard_deviation': round(std_deviation, 6),
                'coefficient_of_variation': round(cv, 4),
                'stability_score': max(0, 100 - (cv * 10)),  # Simple stability score
                'analysis_date': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing stability for {stablecoin_symbol}: {e}")
            return {}

# Utility functions
def get_supported_stablecoins() -> List[Dict[str, str]]:
    """
    Get list of supported stablecoins
    
    Returns:
        List of stablecoin information
    """
    return [
        {
            'symbol': symbol,
            'name': info['name'],
            'coingecko_id': info['coingecko_id'],
            'chains': info['chains']
        }
        for symbol, info in STABLECOINS.items()
    ]

def is_stablecoin(symbol: str) -> bool:
    """
    Check if a given symbol is a supported stablecoin
    
    Args:
        symbol: Cryptocurrency symbol
        
    Returns:
        True if it's a supported stablecoin
    """
    return symbol.upper() in STABLECOINS

