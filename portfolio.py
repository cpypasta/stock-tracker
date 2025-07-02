import json
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime

PORTFOLIO_FILE = "portfolio.json"

class Portfolio:
    def __init__(self, file_path: str = PORTFOLIO_FILE):
        self.file_path = file_path
        self.holdings = self.load_portfolio()
    
    def load_portfolio(self) -> Dict[str, List[Dict]]:
        """Load portfolio from JSON file."""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return {}
        return {}
    
    def save_portfolio(self):
        """Save portfolio to JSON file."""
        with open(self.file_path, 'w') as f:
            json.dump(self.holdings, f, indent=2)
    
    def add_stock(self, ticker: str, shares: float, price_paid: float, date: Optional[str] = None, transaction_type: str = 'BUY'):
        """Add a stock transaction (buy or sell)."""
        ticker = ticker.upper()
        if date is None:
            date = datetime.today().strftime('%Y-%m-%d')
        tx = {'shares': shares, 'price_paid': price_paid, 'date': date, 'type': transaction_type}
        if ticker in self.holdings:
            self.holdings[ticker].append(tx)
        else:
            self.holdings[ticker] = [tx]
        self.save_portfolio()
    
    def remove_stock(self, ticker: str, shares: float, price_sold: float, date: Optional[str] = None):
        """Add a sell transaction."""
        ticker = ticker.upper()
        if date is None:
            date = datetime.today().strftime('%Y-%m-%d')
        
        # Check if we have enough shares to sell
        current_shares = self.get_net_shares(ticker)
        if current_shares < shares:
            raise ValueError(f"Cannot sell {shares} shares of {ticker}, only have {current_shares}")
        
        # Add sell transaction
        tx = {'shares': shares, 'price_paid': price_sold, 'date': date, 'type': 'SELL'}
        if ticker in self.holdings:
            self.holdings[ticker].append(tx)
        else:
            self.holdings[ticker] = [tx]
        self.save_portfolio()
    
    def get_net_shares(self, ticker: str) -> float:
        """Get net shares (buys - sells) for a ticker."""
        ticker = ticker.upper()
        if ticker not in self.holdings:
            return 0.0
        
        net_shares = 0.0
        for tx in self.holdings[ticker]:
            if tx.get('type', 'BUY') == 'BUY':
                net_shares += tx['shares']
            else:  # SELL
                net_shares -= tx['shares']
        return net_shares
    
    def get_portfolio(self) -> Dict[str, Dict]:
        """Get current portfolio holdings (net positions) using FIFO accounting, sorted by shares descending."""
        result = {}
        for ticker in self.holdings.keys():
            remaining_lots = self.get_remaining_lots(ticker)
            
            if not remaining_lots:
                continue  # Skip if no net position
            
            # Calculate totals from remaining lots
            total_shares = sum(lot['shares'] for lot in remaining_lots)
            total_cost = sum(lot['shares'] * lot['price'] for lot in remaining_lots)
            avg_price = total_cost / total_shares if total_shares > 0 else 0
            
            result[ticker] = {'shares': total_shares, 'avg_price': avg_price}
        
        # Sort by shares descending
        sorted_result = dict(sorted(result.items(), key=lambda item: item[1]['shares'], reverse=True))
        return sorted_result
    
    def get_tickers(self) -> List[str]:
        """Get list of tickers in portfolio."""
        return list(self.holdings.keys())
    
    def get_holding(self, ticker: str) -> Optional[Dict]:
        """Get specific holding details (net position)."""
        ticker = ticker.upper()
        txs = self.holdings.get(ticker)
        if not txs:
            return None
        
        # Calculate net shares and weighted average cost basis
        total_buy_shares = 0.0
        total_buy_cost = 0.0
        total_sell_shares = 0.0
        
        for tx in txs:
            tx_type = tx.get('type', 'BUY')
            shares = tx['shares']
            price = tx['price_paid']
            
            if tx_type == 'BUY':
                total_buy_shares += shares
                total_buy_cost += shares * price
            else:  # SELL
                total_sell_shares += shares
        
        net_shares = total_buy_shares - total_sell_shares
        
        if net_shares <= 0:
            return None
        
        avg_price = total_buy_cost / total_buy_shares if total_buy_shares > 0 else 0
        return {'shares': net_shares, 'avg_price': avg_price}
    
    def clear_portfolio(self):
        """Clear all holdings."""
        self.holdings = {}
        self.save_portfolio()
    
    def get_transactions(self, ticker: str) -> List[Dict]:
        """Get all transactions for a ticker."""
        return self.holdings.get(ticker.upper(), [])
    
    def get_remaining_lots(self, ticker: str) -> List[Dict]:
        """Get remaining lots for a ticker after applying FIFO accounting for sells.
        
        Returns:
            List of dicts with keys: shares, price, date
        """
        ticker = ticker.upper()
        txs = self.holdings.get(ticker)
        if not txs:
            return []
        
        # Sort transactions by date to ensure FIFO order
        sorted_txs = sorted(txs, key=lambda tx: tx['date'])
        
        # Track remaining lots using FIFO
        remaining_lots = []
        
        for tx in sorted_txs:
            tx_type = tx.get('type', 'BUY')
            shares = tx['shares']
            price = tx['price_paid']
            date = tx['date']
            
            if tx_type == 'BUY':
                # Add new lot
                remaining_lots.append({'shares': shares, 'price': price, 'date': date})
            else:  # SELL
                # Remove shares using FIFO
                shares_to_sell = shares
                new_lots = []
                
                for lot in remaining_lots:
                    if shares_to_sell <= 0:
                        new_lots.append(lot)
                    elif lot['shares'] <= shares_to_sell:
                        # Sell entire lot
                        shares_to_sell -= lot['shares']
                    else:
                        # Partially sell lot
                        lot['shares'] -= shares_to_sell
                        shares_to_sell = 0
                        new_lots.append(lot)
                
                remaining_lots = new_lots
        
        return remaining_lots

# Convenience functions
def get_portfolio() -> Portfolio:
    """Get portfolio instance."""
    return Portfolio()

def add_stock(ticker: str, shares: float, price_paid: float, date: Optional[str] = None):
    """Add stock purchase to portfolio."""
    portfolio = get_portfolio()
    portfolio.add_stock(ticker, shares, price_paid, date, 'BUY')

def remove_stock(ticker: str, shares: float, price_sold: float, date: Optional[str] = None):
    """Add stock sale to portfolio."""
    portfolio = get_portfolio()
    portfolio.remove_stock(ticker, shares, price_sold, date)

def get_holdings() -> Dict[str, Dict]:
    """Get current holdings."""
    portfolio = get_portfolio()
    return portfolio.get_portfolio()

def get_tickers() -> List[str]:
    """Get list of tickers in portfolio."""
    portfolio = get_portfolio()
    return portfolio.get_tickers()

def get_transactions(ticker: str) -> List[Dict]:
    """Get all transactions for a ticker."""
    portfolio = get_portfolio()
    return portfolio.get_transactions(ticker)

def get_remaining_lots(ticker: str) -> List[Dict]:
    """Get remaining lots for a ticker after FIFO accounting."""
    portfolio = get_portfolio()
    return portfolio.get_remaining_lots(ticker)