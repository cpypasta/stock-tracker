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
    
    def add_stock(self, ticker: str, shares: float, price_paid: float, date: Optional[str] = None):
        """Add a stock purchase transaction."""
        ticker = ticker.upper()
        if date is None:
            date = datetime.today().strftime('%Y-%m-%d')
        tx = {'shares': shares, 'price_paid': price_paid, 'date': date}
        if ticker in self.holdings:
            self.holdings[ticker].append(tx)
        else:
            self.holdings[ticker] = [tx]
        self.save_portfolio()
    
    def remove_stock(self, ticker: str, shares: Optional[float] = None):
        """Remove shares of a stock (FIFO). If shares not specified, remove all."""
        ticker = ticker.upper()
        if ticker not in self.holdings:
            raise ValueError(f"Stock {ticker} not found in portfolio")
        txs = self.holdings[ticker]
        if shares is None:
            # Remove all
            del self.holdings[ticker]
        else:
            shares_to_remove = shares
            new_txs = []
            for tx in txs:
                if shares_to_remove <= 0:
                    new_txs.append(tx)
                elif tx['shares'] <= shares_to_remove:
                    shares_to_remove -= tx['shares']
                    # Remove this tx
                else:
                    # Partially remove from this tx
                    tx['shares'] -= shares_to_remove
                    shares_to_remove = 0
                    new_txs.append(tx)
            if shares_to_remove > 0:
                raise ValueError(f"Cannot remove {shares} shares, only have {sum(tx['shares'] for tx in txs)}")
            if new_txs:
                self.holdings[ticker] = new_txs
            else:
                del self.holdings[ticker]
        self.save_portfolio()
    
    def get_portfolio(self) -> Dict[str, Dict]:
        """Get current portfolio holdings (summed), sorted by shares descending."""
        result = {}
        for ticker, txs in self.holdings.items():
            total_shares = sum(tx['shares'] for tx in txs)
            if total_shares == 0:
                continue
            # Weighted average price
            total_cost = sum(tx['shares'] * tx['price_paid'] for tx in txs)
            avg_price = total_cost / total_shares if total_shares > 0 else 0
            result[ticker] = {'shares': total_shares, 'avg_price': avg_price}
        # Sort by shares descending
        sorted_result = dict(sorted(result.items(), key=lambda item: item[1]['shares'], reverse=True))
        return sorted_result
    
    def get_tickers(self) -> List[str]:
        """Get list of tickers in portfolio."""
        return list(self.holdings.keys())
    
    def get_holding(self, ticker: str) -> Optional[Dict]:
        """Get specific holding details (summed)."""
        ticker = ticker.upper()
        txs = self.holdings.get(ticker)
        if not txs:
            return None
        total_shares = sum(tx['shares'] for tx in txs)
        if total_shares == 0:
            return None
        total_cost = sum(tx['shares'] * tx['price_paid'] for tx in txs)
        avg_price = total_cost / total_shares if total_shares > 0 else 0
        return {'shares': total_shares, 'avg_price': avg_price}
    
    def clear_portfolio(self):
        """Clear all holdings."""
        self.holdings = {}
        self.save_portfolio()
    
    def get_transactions(self, ticker: str) -> List[Dict]:
        """Get all transactions for a ticker."""
        return self.holdings.get(ticker.upper(), [])

# Convenience functions
def get_portfolio() -> Portfolio:
    """Get portfolio instance."""
    return Portfolio()

def add_stock(ticker: str, shares: float, price_paid: float, date: Optional[str] = None):
    """Add stock to portfolio."""
    portfolio = get_portfolio()
    portfolio.add_stock(ticker, shares, price_paid, date)

def remove_stock(ticker: str, shares: Optional[float] = None):
    """Remove stock from portfolio."""
    portfolio = get_portfolio()
    portfolio.remove_stock(ticker, shares)

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