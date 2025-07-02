import argparse
import sys
import yfinance as yf
import asciichartpy
from portfolio import add_stock, remove_stock, get_holdings, get_tickers, get_transactions, get_remaining_lots, Portfolio
from tax_config import set_tax_rates, get_tax_rates, calculate_short_term_tax_on_gains, calculate_long_term_tax_on_gains
from datetime import datetime
from rich.console import Console
from rich.table import Table

ansi_colors = {
    'green': '\033[32m',
    'red': '\033[31m',
    'yellow': '\033[33m',
    'magenta': '\033[35m',
    'cyan': '\033[36m',
    'lightgray': '\033[37m',
    'blue': '\033[34m',
    'reset': '\033[0m'
}

TICKER_DISPLAY_NAMES = {
    '^IXIC': 'NASDAQ',
}

def get_stock_data(ticker_symbol, days):
    """
    Fetches historical stock data for a given ticker symbol.
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        hist_data = ticker.history(period=f"{days}d")
        return hist_data, None
    except Exception as e:
        return None, f"Error fetching data for {ticker_symbol}: {e}"


def print_price(price, prev_close, ticker):
    price_str = f"${price:.2f}"
    display_ticker = TICKER_DISPLAY_NAMES.get(ticker, ticker)
    ticker_str = f"{ansi_colors['lightgray']}{display_ticker}{ansi_colors['reset']}"
    if prev_close is not None:
        change = price - prev_close
        pct_change = (change / prev_close * 100) if prev_close != 0 else 0
        change_str = f"{change:+.2f}"
        pct_str = f"({pct_change:+.1f}%)"
        if change > 0:
            arrow = f"{ansi_colors['green']}▲{ansi_colors['reset']}"
            color_code = ansi_colors['green']
        elif change < 0:
            arrow = f"{ansi_colors['red']}▼{ansi_colors['reset']}"
            color_code = ansi_colors['red']
        else:
            arrow = '→'
            color_code = ansi_colors['lightgray']
        content = f"{ticker_str}: {color_code}{price_str}{ansi_colors['reset']} {arrow} {change_str} {pct_str}"
    else:
        content = f"{ticker_str}: {price_str}"
    print(content)


def plot_stocks(tickers, days, mode='price', zero=False, now=False):
    """
    Plots stock data for one or more tickers using asciichartpy (terminal-only, line chart only).
    mode: 'price' for absolute prices, 'change' for percent change.
    """
    color_list = [
        asciichartpy.green,
        asciichartpy.red,
        asciichartpy.yellow,
        asciichartpy.magenta,
        asciichartpy.cyan,
        asciichartpy.lightgray
    ]
    color_names = [
        'green',
        'red',
        'yellow',
        'magenta',
        'cyan',
        'lightgray'
    ]
    data = {}
    errors = {}
    # Print current price info for each ticker above the chart
    for ticker in tickers:
        hist, error = get_stock_data(ticker, days)
        if error or hist is None or hist.empty:
            errors[ticker] = error or f"No data for {ticker}"
            continue
        if mode == 'change':
            series = hist['Close'].pct_change().fillna(0) * 100
        else:
            series = hist['Close']
        data[ticker] = series
        # Print current price info (change from first day in range)
        current_price = hist['Close'].iloc[-1]
        first_close = hist['Close'].iloc[0] if len(hist['Close']) > 1 else None
        print_price(current_price, first_close, ticker)
    if not data:
        print("No valid data to plot.")
        for ticker, err in errors.items():
            print(f"{ticker}: {err}")
        return
    series_list = [s.values.tolist() for s in data.values()]
    colors = [color_list[i % len(color_list)] for i in range(len(series_list))]
    legend_lines = []
    for i, ticker in enumerate(data.keys()):
        display_ticker = TICKER_DISPLAY_NAMES.get(ticker, ticker)
        color = color_names[i % len(color_names)]
        ansi = ansi_colors[color]
        reset = ansi_colors['reset']
        legend_lines.append(f"{display_ticker}: {ansi}{color}{reset}")
    if mode == 'change':
        zero_line = [0] * len(series_list[0])
        series_list.append(zero_line)
        colors.append(asciichartpy.blue)
        # Do not add zero line to legend
    # Use display names in chart title
    display_names = [str(TICKER_DISPLAY_NAMES.get(t, t)) for t in data.keys()]
    print(f"\n{' vs '.join(display_names)} - {'% Change' if mode == 'change' else 'Price ($)'} ({days} days)")
    if len(data) > 1:
        for line in legend_lines:
            print("  " + line)
        print()
    plot_config = {'height': 12, 'colors': colors}
    if mode == 'price' and zero:
        plot_config['min'] = 0
    print(asciichartpy.plot(series_list, plot_config))
    if errors:
        print("\nSome tickers could not be plotted:")
        for ticker, err in errors.items():
            print(f"{ticker}: {err}")


def show_portfolio():
    """Display portfolio with current prices and gains/losses."""
    # default terminal color to lightgray
    print(ansi_colors['lightgray'])

    holdings = get_holdings()
    if not holdings:
        print("Portfolio is empty.")
        return
    
    total_cost = 0
    total_value = 0
    total_after_tax_gain = 0
    today = datetime.today().date()
    
    total_short_term_tax = 0
    total_long_term_tax = 0
    
    # Remove ASCII separators and use rich table with title 'Portfolio'
    portfolio_table = Table(show_header=True, header_style="bold magenta", title="Portfolio")
    portfolio_table.add_column("Ticker", style="dim", justify="left")
    portfolio_table.add_column("Shares", justify="right")
    portfolio_table.add_column("Avg Price", justify="right")
    portfolio_table.add_column("Total Value", justify="right")
    portfolio_table.add_column("Price Change", justify="right")
    portfolio_table.add_column("After-tax", justify="right")
    for ticker, holding in holdings.items():
        shares = holding['shares']
        avg_price = holding['avg_price']
        cost_basis = shares * avg_price
        total_cost += cost_basis
        # Get current price
        hist, error = get_stock_data(ticker, 1)
        if error or hist is None or hist.empty:
            current_price = 0
            portfolio_table.add_row(ticker, f"{shares:,.2f}", f"${avg_price:,.2f}", "-", "-", "-")
            continue
        current_price = hist['Close'].iloc[-1]
        current_value = shares * current_price
        total_value += current_value
        gain_loss = current_value - cost_basis
        gain_loss_pct = (gain_loss / cost_basis * 100) if cost_basis > 0 else 0
        if gain_loss > 0:
            color = 'green'
            arrow = '▲'
        elif gain_loss < 0:
            color = 'red'
            arrow = '▼'
        else:
            color = 'grey58'
            arrow = '→'
        # Calculate after-tax gain/loss for remaining shares using FIFO
        remaining_lots = get_remaining_lots(ticker)
        
        # Calculate after-tax gain only on remaining lots
        after_tax_gain = 0
        for lot in remaining_lots:
            lot_shares = lot['shares']
            lot_cost = lot_shares * lot['price']
            lot_value = lot_shares * current_price
            lot_gain = lot_value - lot_cost
            
            try:
                lot_date = datetime.strptime(lot['date'], '%Y-%m-%d').date()
            except Exception:
                lot_date = today
            
            holding_days = (today - lot_date).days
            
            if lot_gain > 0:
                if holding_days > 365:
                    tax = calculate_long_term_tax_on_gains(lot_gain)
                    total_long_term_tax += float(tax['total'])
                else:
                    tax = calculate_short_term_tax_on_gains(lot_gain)
                    total_short_term_tax += float(tax['total'])
                after_tax_gain += lot_gain - float(tax['total'])
            else:
                after_tax_gain += lot_gain
        total_after_tax_gain += after_tax_gain
        if after_tax_gain > 0:
            at_color = 'green'
            at_arrow = '▲'
        elif after_tax_gain < 0:
            at_color = 'red'
            at_arrow = '▼'
        else:
            at_color = 'grey58'
            at_arrow = '→'
        gain_loss_str = f"[{color}]{arrow} ${gain_loss:+,.2f} ({gain_loss_pct:+.1f}%)[/{color}]"
        after_tax_pct = (after_tax_gain / cost_basis * 100) if cost_basis > 0 else 0
        after_tax_str = f"[{at_color}]{at_arrow} ${after_tax_gain:+,.2f} ({after_tax_pct:+.1f}%)[/{at_color}]"
        portfolio_table.add_row(
            ticker,
            f"{shares:,.2f}",
            f"${avg_price:,.2f}",
            f"${current_value:,.2f}",
            gain_loss_str,
            after_tax_str
        )
    console = Console()
    console.print(portfolio_table)
    
    total_gain_loss = total_value - total_cost
    total_gain_loss_pct = (total_gain_loss / total_cost * 100) if total_cost > 0 else 0
    
    # Table for totals using rich
    def rich_gain_loss(val, arrow, color):
        return f"[{color}]{arrow} ${val:+,.2f}[/{color}]"
    total_table = Table(show_header=True, header_style="bold magenta", title="Totals")
    total_table.add_column("Total", style="dim", justify="left")
    total_table.add_column("Amount", justify="right")
    total_table.add_row("Total Cost", f"${total_cost:,.2f}")
    total_table.add_row("Price Change", rich_gain_loss(total_gain_loss, arrow, color))  
    total_table.add_row("Total Value", f"${total_value:,.2f}")
    total_table.add_row("Total Taxes", f"[red](${total_short_term_tax + total_long_term_tax:,.2f})[/red]")            
    total_table.add_row("After-tax Change", rich_gain_loss(total_after_tax_gain, at_arrow, at_color))
    
    # Calculate total cash value (original cost + after-tax gain)
    total_cash_value = total_cost + total_after_tax_gain
    total_table.add_row("Total Cash Value", f"${total_cash_value:,.2f}")
    
    console.print(total_table)
    # Table for tax summary using rich
    config = get_tax_rates()
    nii_rate = 3.8 if config['nii'] else 0.0
    st_total_pct = config['short_term_federal'] + config['state'] + nii_rate
    lt_total_pct = config['long_term_federal'] + config['state'] + nii_rate
    
    # Calculate individual tax amounts
    total_taxes = total_short_term_tax + total_long_term_tax
    if st_total_pct > 0:
        st_federal_amount = total_short_term_tax * (config['short_term_federal'] / st_total_pct)
        st_state_amount = total_short_term_tax * (config['state'] / st_total_pct)
        st_nii_amount = total_short_term_tax * (nii_rate / st_total_pct) if config['nii'] else 0
    else:
        st_federal_amount = st_state_amount = st_nii_amount = 0
        
    if lt_total_pct > 0:
        lt_federal_amount = total_long_term_tax * (config['long_term_federal'] / lt_total_pct)
        lt_state_amount = total_long_term_tax * (config['state'] / lt_total_pct)
        lt_nii_amount = total_long_term_tax * (nii_rate / lt_total_pct) if config['nii'] else 0
    else:
        lt_federal_amount = lt_state_amount = lt_nii_amount = 0
    
    total_federal = st_federal_amount + lt_federal_amount
    total_state = st_state_amount + lt_state_amount
    total_nii = st_nii_amount + lt_nii_amount
    
    tax_table = Table(show_header=True, header_style="bold magenta", title="Tax Breakdown")
    tax_table.add_column("Tax Type", style="dim", justify="left")
    tax_table.add_column("Rate", justify="right")
    tax_table.add_column("Amount", justify="right")
    tax_table.add_row("Short-term Federal", f"{config['short_term_federal']}%", f"${st_federal_amount:,.2f}")
    tax_table.add_row("Long-term Federal", f"{config['long_term_federal']}%", f"${lt_federal_amount:,.2f}")
    tax_table.add_row("State", f"{config['state']}%", f"${total_state:,.2f}")
    if config['nii']:
        tax_table.add_row("NII", f"{nii_rate:.1f}%", f"${total_nii:,.2f}")
    tax_table.add_row("Total Taxes", "-", f"${total_short_term_tax + total_long_term_tax:,.2f}")
    console.print(tax_table)
    print(ansi_colors['reset'])


def show_trades(ticker):
    """Display trade history for a specific ticker."""
    ticker = ticker.upper()
    transactions = get_transactions(ticker)
    
    if not transactions:
        print(f"No trades found for {ticker}")
        return
    
    # Sort transactions by date (oldest first)
    def parse_date(date_str):
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            try:
                # Handle dates like "2021-4-30" (single digit month/day)
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                # If parsing fails, return a very old date so it sorts first
                return datetime(1900, 1, 1).date()
    
    transactions = sorted(transactions, key=lambda tx: parse_date(tx['date']))
    
    # Get current price to calculate price change
    hist, error = get_stock_data(ticker, 1)
    current_price = None
    if not error and hist is not None and not hist.empty:
        current_price = hist['Close'].iloc[-1]
    
    # Create table for trades
    console = Console()
    trades_table = Table(show_header=True, header_style="bold magenta", title=f"{ticker} Trade History")
    trades_table.add_column("Date", style="dim", justify="left")
    trades_table.add_column("Type", justify="center")
    trades_table.add_column("Shares", justify="right")
    trades_table.add_column("Price", justify="right")
    trades_table.add_column("Value", justify="right")
    trades_table.add_column("Price Change", justify="right")
    
    for tx in transactions:
        shares = tx['shares']
        price = tx['price_paid']
        date = tx['date']
        tx_type_raw = tx.get('type', 'BUY')  # Default to BUY for backward compatibility
        
        # Determine transaction type and format
        if tx_type_raw == 'SELL':
            tx_type = "[red]SELL[/red]"
        else:
            tx_type = "[green]BUY[/green]"
        
        # Calculate current value and price change
        if current_price is not None:
            current_value = shares * current_price
            
            if tx_type_raw == 'SELL':
                # For SELL transactions, we need to show the profit/loss vs average cost basis
                # Use FIFO accounting to get the correct cost basis of remaining shares
                portfolio_obj = Portfolio()
                holdings = portfolio_obj.get_portfolio()
                
                if ticker in holdings:
                    # Use the FIFO-calculated average cost basis of remaining shares
                    avg_cost_basis = holdings[ticker]['avg_price']
                    
                    # For SELL: show profit/loss vs cost basis
                    price_change = price - avg_cost_basis
                    price_change_pct = (price_change / avg_cost_basis * 100) if avg_cost_basis != 0 else 0
                    
                    # Format price change for SELL transactions
                    if price_change > 0.001:  # Small tolerance for floating point precision
                        color = 'green'
                        arrow = '▲'
                        price_change_str = f"[{color}]{arrow} ${price_change:+.2f} ({price_change_pct:+.1f}%)[/{color}]"
                    elif price_change < -0.001:  # Small tolerance for floating point precision
                        color = 'red'
                        arrow = '▼'
                        price_change_str = f"[{color}]{arrow} ${price_change:+.2f} ({price_change_pct:+.1f}%)[/{color}]"
                    else:
                        color = 'grey58'
                        arrow = '→'
                        price_change_str = f"[{color}]{arrow} $0.00 (0.0%)[/{color}]"
                    
                    # Value shows what those shares would be worth at current price
                    # Show in red parentheses since they were sold (no longer owned)
                    value_str = f"[red](${current_value:,.2f})[/red]"
                else:
                    # No remaining position found, can't calculate cost basis
                    price_change = 0
                    price_change_pct = 0
                    price_change_str = "N/A"
                    value_str = f"[red](${current_value:,.2f})[/red]"
            else:
                # For BUY transactions: show current value vs purchase price
                price_change = current_price - price
                price_change_pct = (price_change / price * 100) if price != 0 else 0
                
                # Value column - always show positive value without conditional coloring
                value_str = f"${current_value:,.2f}"
                
                # Format price change column (no asterisk for BUY)
                if price_change > 0.001:  # Small tolerance for floating point precision
                    color = 'green'
                    arrow = '▲'
                    price_change_str = f"[{color}]{arrow} ${price_change:+.2f} ({price_change_pct:+.1f}%)[/{color}]"
                elif price_change < -0.001:  # Small tolerance for floating point precision
                    color = 'red'
                    arrow = '▼'
                    price_change_str = f"[{color}]{arrow} ${price_change:+.2f} ({price_change_pct:+.1f}%)[/{color}]"
                else:
                    color = 'grey58'
                    arrow = '→'
                    price_change_str = f"[{color}]{arrow} $0.00 (0.0%)[/{color}]"
        else:
            value_str = "N/A"
            price_change_str = "N/A"
        
        trades_table.add_row(
            date,
            tx_type,
            f"{shares:,.2f}",
            f"${price:.2f}",
            value_str,
            price_change_str
        )
    
    console.print(trades_table)
    
    if current_price is not None:
        print(f"\nCurrent {ticker} price: ${current_price:.2f}")
    else:
        print(f"\nCould not fetch current {ticker} price")


def main():
    # Check if first argument is a subcommand
    if len(sys.argv) > 1 and sys.argv[1] in ['buy', 'sell', 'port', 'list', 'tax-set', 'tax-show', 'trades']:
        # Use subparsers for portfolio and tax commands
        parser = argparse.ArgumentParser(description="Stock Tracker CLI (asciichartpy terminal version)")
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        buy_parser = subparsers.add_parser('buy', help='Buy shares of a stock')
        buy_parser.add_argument('ticker', help='Stock ticker symbol')
        buy_parser.add_argument('shares', type=float, help='Number of shares')
        buy_parser.add_argument('price', type=float, help='Price paid per share')
        buy_parser.add_argument('--date', type=str, help='Date of purchase (YYYY-MM-DD)', required=False)
        
        sell_parser = subparsers.add_parser('sell', help='Sell shares of a stock')
        sell_parser.add_argument('ticker', help='Stock ticker symbol')
        sell_parser.add_argument('shares', type=float, help='Number of shares to sell')
        sell_parser.add_argument('price', type=float, help='Price sold per share')
        sell_parser.add_argument('--date', type=str, help='Date of sale (YYYY-MM-DD)', required=False)
        
        portfolio_parser = subparsers.add_parser('portfolio', help='Show portfolio with current prices and gains/losses')
        port_parser = subparsers.add_parser('port', help='Show portfolio (alias for portfolio)')
        
        list_parser = subparsers.add_parser('list', help='List all tickers in portfolio')
        
        tax_set_parser = subparsers.add_parser('tax-set', help='Set tax configuration')
        tax_set_parser.add_argument('short_term_federal', type=float, help='Short-term federal tax rate (percentage)')
        tax_set_parser.add_argument('long_term_federal', type=float, help='Long-term federal tax rate (percentage)')
        tax_set_parser.add_argument('state', type=float, help='State tax rate (percentage)')
        tax_set_parser.add_argument('--nii', action='store_true', help='Subject to Net Investment Income tax')
        
        tax_show_parser = subparsers.add_parser('tax-show', help='Show current tax configuration')
        
        trades_parser = subparsers.add_parser('trades', help='Show trade history for a stock')
        trades_parser.add_argument('ticker', help='Stock ticker symbol')
        
        args = parser.parse_args()
        
        if args.command == 'buy':
            add_stock(args.ticker, args.shares, args.price, args.date)
            print(f"Added {args.shares} shares of {args.ticker.upper()} at ${args.price:.2f}" + (f" on {args.date}" if args.date else ""))
        
        elif args.command == 'sell':
            try:
                remove_stock(args.ticker, args.shares, args.price, args.date)
                print(f"Sold {args.shares} shares of {args.ticker.upper()} at ${args.price:.2f}" + (f" on {args.date}" if args.date else ""))
            except ValueError as e:
                print(f"Error: {e}")
        
        elif args.command == 'port':
            show_portfolio()
        
        elif args.command == 'list':
            tickers = get_tickers()
            if tickers:
                print("Portfolio Stocks:")
                holdings = get_holdings()
                for ticker in tickers:
                    shares = holdings[ticker]['shares']
                    print(f"  {ticker}: {shares:,.2f}")
            else:
                print("Portfolio is empty.")
        
        elif args.command == 'tax-set':
            set_tax_rates(args.short_term_federal, args.long_term_federal, args.state, args.nii)
            print(f"Tax configuration set:")
            print(f"  Short-term Federal: {args.short_term_federal}%")
            print(f"  Long-term Federal: {args.long_term_federal}%")
            print(f"  State: {args.state}%")
            print(f"  NII: {args.nii}")
        
        elif args.command == 'tax-show':
            config = get_tax_rates()
            print("Current tax configuration:")
            print(f"  Short-term Federal: {config['short_term_federal']}%")
            print(f"  Long-term Federal: {config['long_term_federal']}%")
            print(f"  State: {config['state']}%")
            print(f"  NII: {config['nii']}")
        
        elif args.command == 'trades':
            show_trades(args.ticker)
    
    else:
        # Treat as chart command
        parser = argparse.ArgumentParser(description="Show stock charts")
        parser.add_argument("ticker", nargs='+', help="Stock ticker symbol(s) (e.g., AAPL GOOGL TSLA)")
        parser.add_argument("--days", type=int, help="Number of days to display. If not provided, only show the current price.")
        parser.add_argument("--mode", choices=['price', 'change'], default='price',
                           help="Display mode: 'price' for absolute prices, 'change' for daily percent change (default: price)")
        parser.add_argument("--zero", action='store_true', help="In price mode, start y-axis at 0 instead of min price.")
        parser.add_argument("--base", action='store_true', help="Include NASDAQ (^IXIC) as a base ticker.")
        
        args = parser.parse_args()
        
        tickers = args.ticker[:]
        if args.base and '^IXIC' not in tickers:
            tickers.append('^IXIC')

        if args.days is None:
            # Show only the current price(s)
            for ticker in tickers:
                hist, error = get_stock_data(ticker, 2)
                if error or hist is None or hist.empty:
                    print(f"{ticker}: Error or no data")
                    continue
                current_price = hist['Close'].iloc[-1]
                prev_close = hist['Close'].iloc[-2] if len(hist['Close']) > 1 else None
                print_price(current_price, prev_close, ticker)
        else:
            plot_stocks(tickers, args.days, args.mode, args.zero, now=False)

if __name__ == "__main__":
    main()
