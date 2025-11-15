# cryptotronbot_backend/utils/yield_aggregator.py
# Yield aggregation utilities for DeFi stablecoin yield opportunities

import requests
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

# DeFiLlama API Configuration (Primary source for yield data)
DEFILLAMA_API_URL = "https://yields.llama.fi"
DEFILLAMA_PROTOCOLS_URL = "https://api.llama.fi/protocols"

class YieldAggregator:
    """
    Aggregates yield opportunities from various DeFi protocols
    This is a foundation for integrating with platforms like Kiln DeFi, Iron.xyz, etc.
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'CryptoTronBot-YieldAggregator/1.0'
        })
        
        # Cache for yield data (in production, use Redis or similar)
        self._yield_cache = {}
        self._cache_expiry = {}
        self.cache_duration = timedelta(minutes=15)  # Cache for 15 minutes
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached data is still valid"""
        return (key in self._cache_expiry and 
                datetime.utcnow() < self._cache_expiry[key])
    
    def _cache_data(self, key: str, data: Any) -> None:
        """Cache data with expiry"""
        self._yield_cache[key] = data
        self._cache_expiry[key] = datetime.utcnow() + self.cache_duration
    
    def _fetch_defillama_yields(self, protocol_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch yield opportunities from DeFiLlama API
        
        Args:
            protocol_filter: Optional protocol name to filter by (e.g., 'aave-v3')
            
        Returns:
            List of yield opportunities from DeFiLlama
        """
        cache_key = f"defillama_yields_{protocol_filter or 'all'}"
        
        if self._is_cache_valid(cache_key):
            return self._yield_cache[cache_key]
        
        try:
            # Fetch yield pools from DeFiLlama
            response = self.session.get(
                f"{DEFILLAMA_API_URL}/pools",
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            
            if 'data' not in data:
                logger.warning("Unexpected DeFiLlama API response format")
                return []
            
            pools = data['data']
            opportunities = []
            
            # Filter for stablecoins
            stablecoin_symbols = ['USDC', 'USDT', 'DAI', 'BUSD', 'FRAX']
            
            for pool in pools:
                # Filter by protocol if specified
                if protocol_filter and protocol_filter.lower() not in pool.get('project', '').lower():
                    continue
                
                # Filter for stablecoins
                symbol = pool.get('symbol', '').upper()
                if symbol not in stablecoin_symbols:
                    continue
                
                # Extract relevant data
                apy = pool.get('apy', 0)
                if apy <= 0:  # Skip pools with no yield
                    continue
                
                opportunity = {
                    'protocol': pool.get('project', 'Unknown'),
                    'asset': symbol,
                    'apy': round(apy, 2),
                    'supply_apy': round(pool.get('apyBase', 0), 2),
                    'borrow_apy': round(pool.get('apyReward', 0), 2),
                    'total_liquidity': pool.get('tvlUsd', 0),
                    'chain': pool.get('chain', 'Unknown'),
                    'pool': pool.get('pool', ''),
                    'minimum_deposit': 0.01,  # Default, as DeFiLlama doesn't always provide this
                    'risk_level': self._assess_risk_level(pool),
                    'last_updated': datetime.utcnow().isoformat()
                }
                
                opportunities.append(opportunity)
            
            # Sort by APY (descending)
            opportunities.sort(key=lambda x: x.get('apy', 0), reverse=True)
            
            self._cache_data(cache_key, opportunities)
            return opportunities
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching yields from DeFiLlama: {e}")
            return self._get_fallback_yields(protocol_filter)
        except Exception as e:
            logger.error(f"Unexpected error fetching DeFiLlama yields: {e}")
            return self._get_fallback_yields(protocol_filter)
    
    def _assess_risk_level(self, pool: Dict) -> str:
        """Assess risk level based on pool data"""
        tvl = pool.get('tvlUsd', 0)
        apy = pool.get('apy', 0)
        
        # High TVL + low APY = Low risk
        if tvl > 1000000000 and apy < 10:  # >$1B TVL, <10% APY
            return 'Low'
        elif tvl > 100000000 or apy < 15:  # >$100M TVL or <15% APY
            return 'Medium'
        else:
            return 'High'
    
    def _get_fallback_yields(self, protocol_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fallback to mock data if API fails"""
        logger.warning("Using fallback mock data due to API failure")
        
        if protocol_filter and 'aave' in protocol_filter.lower():
            return self._get_aave_mock_data()
        elif protocol_filter and 'compound' in protocol_filter.lower():
            return self._get_compound_mock_data()
        elif protocol_filter and 'curve' in protocol_filter.lower():
            return self._get_curve_mock_data()
        elif protocol_filter and 'yearn' in protocol_filter.lower():
            return self._get_yearn_mock_data()
        else:
            # Return all mock data
            all_mock = []
            all_mock.extend(self._get_aave_mock_data())
            all_mock.extend(self._get_compound_mock_data())
            all_mock.extend(self._get_curve_mock_data())
            all_mock.extend(self._get_yearn_mock_data())
            return all_mock
    
    def _get_aave_mock_data(self) -> List[Dict[str, Any]]:
        """Fallback mock data for Aave"""
        return [
                {
                    'protocol': 'Aave V3',
                    'asset': 'USDC',
                    'apy': 4.25,
                    'supply_apy': 4.25,
                    'borrow_apy': 5.15,
                    'total_liquidity': 1250000000,  # $1.25B
                    'utilization_rate': 0.78,
                    'risk_level': 'Low',
                    'minimum_deposit': 0.01,
                    'chain': 'Ethereum',
                    'contract_address': '0x...',
                    'last_updated': datetime.utcnow().isoformat()
                },
                {
                    'protocol': 'Aave V3',
                    'asset': 'USDT',
                    'apy': 3.95,
                    'supply_apy': 3.95,
                    'borrow_apy': 4.85,
                    'total_liquidity': 890000000,  # $890M
                    'utilization_rate': 0.72,
                    'risk_level': 'Low',
                    'minimum_deposit': 0.01,
                    'chain': 'Ethereum',
                    'contract_address': '0x...',
                    'last_updated': datetime.utcnow().isoformat()
                },
                {
                    'protocol': 'Aave V3',
                    'asset': 'DAI',
                    'apy': 4.15,
                    'supply_apy': 4.15,
                    'borrow_apy': 5.05,
                    'total_liquidity': 650000000,  # $650M
                    'utilization_rate': 0.68,
                    'risk_level': 'Low',
                    'minimum_deposit': 0.01,
                    'chain': 'Ethereum',
                    'contract_address': '0x...',
                    'last_updated': datetime.utcnow().isoformat()
                }
            ]
    
    def get_compound_yields(self) -> List[Dict[str, Any]]:
        """
        Get yield opportunities from Compound protocol
        Uses DeFiLlama API with fallback to mock data
        """
        try:
            # Try to fetch from DeFiLlama, filtering for Compound
            yields = self._fetch_defillama_yields(protocol_filter='compound')
            if yields:
                return yields
            # Fallback to mock data
            return self._get_compound_mock_data()
        except Exception as e:
            logger.error(f"Error fetching Compound yields: {e}")
            return self._get_compound_mock_data()
    
    def _get_compound_mock_data(self) -> List[Dict[str, Any]]:
        """Mock data for Compound (fallback only)"""
        return [
                {
                    'protocol': 'Compound V3',
                    'asset': 'USDC',
                    'apy': 3.85,
                    'supply_apy': 3.85,
                    'borrow_apy': 4.75,
                    'total_liquidity': 980000000,  # $980M
                    'utilization_rate': 0.75,
                    'risk_level': 'Low',
                    'minimum_deposit': 0.01,
                    'chain': 'Ethereum',
                    'contract_address': '0x...',
                    'last_updated': datetime.utcnow().isoformat()
                },
                {
                    'protocol': 'Compound V3',
                    'asset': 'DAI',
                    'apy': 3.65,
                    'supply_apy': 3.65,
                    'borrow_apy': 4.55,
                    'total_liquidity': 420000000,  # $420M
                    'utilization_rate': 0.71,
                    'risk_level': 'Low',
                    'minimum_deposit': 0.01,
                    'chain': 'Ethereum',
                    'contract_address': '0x...',
                    'last_updated': datetime.utcnow().isoformat()
                }
            ]
    
    def get_curve_yields(self) -> List[Dict[str, Any]]:
        """
        Get yield opportunities from Curve Finance
        Uses DeFiLlama API with fallback to mock data
        """
        try:
            # Try to fetch from DeFiLlama, filtering for Curve
            yields = self._fetch_defillama_yields(protocol_filter='curve')
            if yields:
                return yields
            # Fallback to mock data
            return self._get_curve_mock_data()
        except Exception as e:
            logger.error(f"Error fetching Curve yields: {e}")
            return self._get_curve_mock_data()
    
    def _get_curve_mock_data(self) -> List[Dict[str, Any]]:
        """Mock data for Curve (fallback only)"""
        return [
                {
                    'protocol': 'Curve Finance',
                    'asset': 'USDT',
                    'pool_name': '3Pool',
                    'apy': 5.12,
                    'base_apy': 2.15,
                    'crv_apy': 2.97,
                    'total_liquidity': 2100000000,  # $2.1B
                    'risk_level': 'Medium',
                    'minimum_deposit': 10,
                    'chain': 'Ethereum',
                    'contract_address': '0x...',
                    'last_updated': datetime.utcnow().isoformat()
                },
                {
                    'protocol': 'Curve Finance',
                    'asset': 'USDC',
                    'pool_name': '3Pool',
                    'apy': 5.25,
                    'base_apy': 2.28,
                    'crv_apy': 2.97,
                    'total_liquidity': 2100000000,  # $2.1B
                    'risk_level': 'Medium',
                    'minimum_deposit': 10,
                    'chain': 'Ethereum',
                    'contract_address': '0x...',
                    'last_updated': datetime.utcnow().isoformat()
                },
                {
                    'protocol': 'Curve Finance',
                    'asset': 'DAI',
                    'pool_name': '3Pool',
                    'apy': 5.08,
                    'base_apy': 2.11,
                    'crv_apy': 2.97,
                    'total_liquidity': 2100000000,  # $2.1B
                    'risk_level': 'Medium',
                    'minimum_deposit': 10,
                    'chain': 'Ethereum',
                    'contract_address': '0x...',
                    'last_updated': datetime.utcnow().isoformat()
                }
            ]
    
    def get_yearn_yields(self) -> List[Dict[str, Any]]:
        """
        Get yield opportunities from Yearn Finance vaults
        Uses DeFiLlama API with fallback to mock data
        """
        try:
            # Try to fetch from DeFiLlama, filtering for Yearn
            yields = self._fetch_defillama_yields(protocol_filter='yearn')
            if yields:
                return yields
            # Fallback to mock data
            return self._get_yearn_mock_data()
        except Exception as e:
            logger.error(f"Error fetching Yearn yields: {e}")
            return self._get_yearn_mock_data()
    
    def _get_yearn_mock_data(self) -> List[Dict[str, Any]]:
        """Mock data for Yearn (fallback only)"""
        return [
                {
                    'protocol': 'Yearn Finance',
                    'asset': 'USDC',
                    'vault_name': 'USDC Vault',
                    'apy': 6.45,
                    'net_apy': 6.45,
                    'gross_apy': 7.15,
                    'total_assets': 450000000,  # $450M
                    'risk_level': 'Medium',
                    'minimum_deposit': 0.01,
                    'chain': 'Ethereum',
                    'contract_address': '0x...',
                    'strategy': 'Multi-strategy yield optimization',
                    'last_updated': datetime.utcnow().isoformat()
                },
                {
                    'protocol': 'Yearn Finance',
                    'asset': 'DAI',
                    'vault_name': 'DAI Vault',
                    'apy': 6.25,
                    'net_apy': 6.25,
                    'gross_apy': 6.95,
                    'total_assets': 320000000,  # $320M
                    'risk_level': 'Medium',
                    'minimum_deposit': 0.01,
                    'chain': 'Ethereum',
                    'contract_address': '0x...',
                    'strategy': 'Multi-strategy yield optimization',
                    'last_updated': datetime.utcnow().isoformat()
                }
            ]
    
    def get_all_yield_opportunities(self, asset_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Aggregate yield opportunities from all supported protocols
        
        Args:
            asset_filter: Optional asset symbol to filter by (e.g., 'USDC')
            
        Returns:
            List of all yield opportunities, sorted by APY
        """
        try:
            all_opportunities = []
            
            # Fetch from all protocols
            all_opportunities.extend(self.get_aave_yields())
            all_opportunities.extend(self.get_compound_yields())
            all_opportunities.extend(self.get_curve_yields())
            all_opportunities.extend(self.get_yearn_yields())
            
            # Filter by asset if specified
            if asset_filter:
                asset_filter = asset_filter.upper()
                all_opportunities = [
                    opp for opp in all_opportunities 
                    if opp.get('asset', '').upper() == asset_filter
                ]
            
            # Sort by APY (descending)
            all_opportunities.sort(key=lambda x: x.get('apy', 0), reverse=True)
            
            # Add ranking and additional metadata
            for i, opp in enumerate(all_opportunities):
                opp['rank'] = i + 1
                opp['category'] = self._categorize_opportunity(opp)
                opp['risk_score'] = self._calculate_risk_score(opp)
            
            return all_opportunities
            
        except Exception as e:
            logger.error(f"Error aggregating yield opportunities: {e}")
            return []
    
    def _categorize_opportunity(self, opportunity: Dict[str, Any]) -> str:
        """Categorize yield opportunity by type"""
        protocol = opportunity.get('protocol', '').lower()
        
        if 'aave' in protocol or 'compound' in protocol:
            return 'Lending'
        elif 'curve' in protocol:
            return 'Liquidity Pool'
        elif 'yearn' in protocol:
            return 'Yield Vault'
        else:
            return 'Other'
    
    def _calculate_risk_score(self, opportunity: Dict[str, Any]) -> int:
        """Calculate a simple risk score (1-100, lower is safer)"""
        base_score = 20  # Base risk for DeFi
        
        # Adjust based on protocol
        protocol = opportunity.get('protocol', '').lower()
        if 'aave' in protocol or 'compound' in protocol:
            base_score += 10  # Lower risk for established lending protocols
        elif 'curve' in protocol:
            base_score += 25  # Medium risk for AMM pools
        elif 'yearn' in protocol:
            base_score += 30  # Higher risk for complex strategies
        
        # Adjust based on APY (higher APY = higher risk)
        apy = opportunity.get('apy', 0)
        if apy > 10:
            base_score += 20
        elif apy > 5:
            base_score += 10
        
        # Adjust based on liquidity
        liquidity = opportunity.get('total_liquidity', 0)
        if liquidity < 100000000:  # Less than $100M
            base_score += 15
        elif liquidity > 1000000000:  # More than $1B
            base_score -= 10
        
        return min(100, max(1, base_score))
    
    def get_yield_recommendations(self, user_portfolio: List[Dict], risk_tolerance: str = 'medium') -> List[Dict[str, Any]]:
        """
        Get personalized yield recommendations based on user's portfolio
        
        Args:
            user_portfolio: List of user's holdings
            risk_tolerance: 'low', 'medium', or 'high'
            
        Returns:
            List of recommended yield opportunities
        """
        try:
            # Get user's stablecoin holdings
            stablecoin_holdings = [
                holding for holding in user_portfolio 
                if holding.get('coin_symbol', '').upper() in ['USDT', 'USDC', 'DAI', 'BUSD', 'FRAX']
            ]
            
            if not stablecoin_holdings:
                return []
            
            recommendations = []
            
            for holding in stablecoin_holdings:
                asset = holding.get('coin_symbol', '').upper()
                quantity = holding.get('quantity', 0)
                
                # Get opportunities for this asset
                opportunities = self.get_all_yield_opportunities(asset)
                
                # Filter by risk tolerance
                risk_threshold = {'low': 40, 'medium': 60, 'high': 100}[risk_tolerance]
                filtered_opportunities = [
                    opp for opp in opportunities 
                    if opp.get('risk_score', 100) <= risk_threshold
                ]
                
                # Get top 3 opportunities for this asset
                top_opportunities = filtered_opportunities[:3]
                
                for opp in top_opportunities:
                    potential_yield = quantity * (opp.get('apy', 0) / 100)
                    
                    recommendation = {
                        **opp,
                        'user_holding_quantity': quantity,
                        'potential_annual_yield': potential_yield,
                        'recommendation_reason': self._get_recommendation_reason(opp, holding, risk_tolerance)
                    }
                    
                    recommendations.append(recommendation)
            
            # Sort by potential yield
            recommendations.sort(key=lambda x: x.get('potential_annual_yield', 0), reverse=True)
            
            return recommendations[:10]  # Return top 10 recommendations
            
        except Exception as e:
            logger.error(f"Error generating yield recommendations: {e}")
            return []
    
    def _get_recommendation_reason(self, opportunity: Dict, holding: Dict, risk_tolerance: str) -> str:
        """Generate a recommendation reason"""
        asset = holding.get('coin_symbol', '')
        apy = opportunity.get('apy', 0)
        protocol = opportunity.get('protocol', '')
        risk_level = opportunity.get('risk_level', 'Medium').lower()
        
        reasons = []
        
        if apy > 5:
            reasons.append(f"High APY of {apy:.2f}%")
        
        if risk_level == 'low' and risk_tolerance == 'low':
            reasons.append("Matches your low risk preference")
        
        if protocol in ['Aave V3', 'Compound V3']:
            reasons.append("Established and secure protocol")
        
        if opportunity.get('total_liquidity', 0) > 500000000:
            reasons.append("High liquidity pool")
        
        if not reasons:
            reasons.append(f"Good yield opportunity for {asset}")
        
        return "; ".join(reasons)

# Global instance
yield_aggregator = YieldAggregator()

