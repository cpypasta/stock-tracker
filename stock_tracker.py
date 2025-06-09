import argparse
import yfinance as yf
import pandas as pd

def get_stock_data(ticker_symbol, days=7):
    """
    Fetches the current stock price and historical data for a given ticker symbol.
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        
        # Get current market price
        current_price = ticker.info.get('currentPrice')
        if not current_price:
            # Fallback for current price
            todays_data = ticker.history(period='1d')
            if not todays_data.empty:
                current_price = todays_data['Close'].iloc[-1]
            else:
                current_price = None

        # Get historical data for the specified number of days
        hist_data = ticker.history(period=f"{days}d")

        if hist_data.empty and current_price is None:
            return None, None, f"Could not find any data for the ticker {ticker_symbol}."
        
        return current_price, hist_data, None

    except Exception as e:
        return None, None, f"Error fetching data for {ticker_symbol}: {e}"

def display_trend(historical_data, ticker_symbol, historical_data2=None, ticker_symbol2=None, mode='price'):
    """
    Displays a simple vertical bar chart for the stock trend with integrated price labels.
    Supports comparing two stocks side by side with colors.
    Mode can be 'price' (absolute prices) or 'change' (day-to-day percentage change).
    """
    if historical_data is None or historical_data.empty:
        print("No historical data to display trend.")
        return

    prices1 = historical_data['Close'].tolist()
    prices2 = historical_data2['Close'].tolist() if historical_data2 is not None else None
    
    # Different max columns based on single vs comparison mode
    max_columns = 7 if prices2 is not None else 14
    
    # Process both datasets if comparing
    if prices2 is not None:
        # Ensure both datasets have the same length by taking minimum
        min_length = min(len(prices1), len(prices2))
        prices1 = prices1[-min_length:]  # Take most recent data
        prices2 = prices2[-min_length:]
    
    # If we have more data points than max columns, average them into groups
    def average_prices(prices):
        if len(prices) > max_columns:
            group_size = len(prices) // max_columns
            remainder = len(prices) % max_columns
            
            averaged_prices = []
            start_idx = 0
            
            for i in range(max_columns):
                current_group_size = group_size + (1 if i < remainder else 0)
                end_idx = start_idx + current_group_size
                
                group_avg = sum(prices[start_idx:end_idx]) / current_group_size
                averaged_prices.append(group_avg)
                
                start_idx = end_idx
            
            return averaged_prices
        return prices
    
    prices1 = average_prices(prices1)
    if prices2 is not None:
        prices2 = average_prices(prices2)
    
    # Convert to price changes if mode is 'change'
    if mode == 'change':
        if len(prices1) > 1:
            # Calculate day-to-day percentage changes
            changes1 = [0.0]  # First day has no previous day, so 0% change
            for i in range(1, len(prices1)):
                change = ((prices1[i] - prices1[i-1]) / prices1[i-1]) * 100
                changes1.append(change)
            prices1 = changes1
        
        if prices2 is not None and len(prices2) > 1:
            # Calculate day-to-day percentage changes
            changes2 = [0.0]  # First day has no previous day, so 0% change
            for i in range(1, len(prices2)):
                change = ((prices2[i] - prices2[i-1]) / prices2[i-1]) * 100
                changes2.append(change)
            prices2 = changes2
    
    # Create properly separated vertical bars
    all_prices = prices1 + (prices2 if prices2 else [])
    max_price = max(all_prices)
    min_price = min(all_prices)
    price_range = max_price - min_price if max_price > min_price else 1
    
    max_height = 10
    
    print()  # Add spacing
    
    # Show comparison title if two stocks
    if prices2 is not None:
        mode_text = "Daily Change %" if mode == 'change' else "Price Comparison"
        print(f"{ticker_symbol} vs {ticker_symbol2} - {mode_text}")
        print()
    elif mode == 'change':
        print(f"{ticker_symbol} - Daily Change %")
        print()
    
    # ANSI color codes
    RED = '\033[91m'
    GREEN = '\033[92m'
    RESET = '\033[0m'
    
    # For change mode, we need to handle negative values differently
    if mode == 'change':
        # Find the baseline (0% change) position - put it in the middle
        baseline_position = max_height // 2
    
    # Increase chart height to accommodate labels for both modes
    chart_height = max_height + 2
    
    # Create the bars row by row (top to bottom)
    for row in range(chart_height, 0, -1):
        line = ""
        for i in range(len(prices1)):
            if prices2 is not None:
                # Calculate heights for both stocks
                if mode == 'change':
                    # For change mode, bars go up or down from baseline
                    # Positive changes go up, negative changes go down
                    if prices1[i] >= 0:
                        # Positive: show bar from baseline up
                        bar_height1 = max(1, int((prices1[i] / max(abs(max_price), abs(min_price))) * (max_height // 2)))
                        show_bar1 = row > baseline_position and row <= (baseline_position + bar_height1)
                        # Show label above positive bars (including 0%) - ensure it's within bounds
                        label_row1 = min(baseline_position + bar_height1 + 1, chart_height)
                        show_label1 = row == label_row1
                    else:
                        # Negative: show bar from baseline down
                        bar_height1 = max(1, int((abs(prices1[i]) / max(abs(max_price), abs(min_price))) * (max_height // 2)))
                        show_bar1 = row >= (baseline_position - bar_height1) and row <= baseline_position
                        # Show label below negative bars - if it would go out of bounds, show above baseline instead
                        ideal_label_row1 = baseline_position - bar_height1 - 1
                        if ideal_label_row1 < 1:
                            # If label would be out of bounds, place it above the baseline
                            label_row1 = baseline_position + 1
                        else:
                            label_row1 = ideal_label_row1
                        show_label1 = row == label_row1
                    
                    if prices2[i] >= 0:
                        # Positive: show bar from baseline up
                        bar_height2 = max(1, int((prices2[i] / max(abs(max_price), abs(min_price))) * (max_height // 2)))
                        show_bar2 = row > baseline_position and row <= (baseline_position + bar_height2)
                        # Show label above positive bars (including 0%) - ensure it's within bounds
                        label_row2 = min(baseline_position + bar_height2 + 1, chart_height)
                        show_label2 = row == label_row2
                    else:
                        # Negative: show bar from baseline down
                        bar_height2 = max(1, int((abs(prices2[i]) / max(abs(max_price), abs(min_price))) * (max_height // 2)))
                        show_bar2 = row >= (baseline_position - bar_height2) and row <= baseline_position
                        # Show label below negative bars - if it would go out of bounds, show above baseline instead
                        ideal_label_row2 = baseline_position - bar_height2 - 1
                        if ideal_label_row2 < 1:
                            # If label would be out of bounds, place it above the baseline
                            label_row2 = baseline_position + 1
                        else:
                            label_row2 = ideal_label_row2
                        show_label2 = row == label_row2
                        
                    # Show baseline (0% line) for change mode
                    if row == baseline_position:
                        if i > 0:
                            line += "   "  # Space between column groups
                        line += "----"  # Baseline for first stock
                        line += " "     # Space between bars
                        line += "----"  # Baseline for second stock
                        continue
                else:
                    # Price mode - calculate bar heights and label positions
                    height1 = max(1, int(((prices1[i] - min_price) / price_range) * max_height))
                    height2 = max(1, int(((prices2[i] - min_price) / price_range) * max_height))
                    show_bar1 = row <= height1
                    show_bar2 = row <= height2
                    
                    # Show price labels above bars
                    label_row1 = height1 + 1
                    label_row2 = height2 + 1
                    show_label1 = row == label_row1
                    show_label2 = row == label_row2
                
                if i > 0:
                    line += "   "  # Space between column groups
                
                # First stock bar (red) with labels
                if show_bar1:
                    line += f"{RED}████{RESET}"
                elif mode == 'price' and show_label1:
                    # Show price label above bar
                    label = f"${prices1[i]:.0f}"[:4]  # Format price and truncate to fit
                    line += f"{label:^4}"
                elif mode == 'change' and show_label1:
                    # Show percentage label above/below bar
                    label = f"{prices1[i]:+.0f}%"[:4]  # Truncate to fit in bar width
                    line += f"{label:^4}"
                else:
                    line += "    "
                
                line += " "  # Space between the two bars
                
                # Second stock bar (green) with labels
                if show_bar2:
                    line += f"{GREEN}████{RESET}"
                elif mode == 'price' and show_label2:
                    # Show price label above bar
                    label = f"${prices2[i]:.0f}"[:4]  # Format price and truncate to fit
                    line += f"{label:^4}"
                elif mode == 'change' and show_label2:
                    # Show percentage label above/below bar
                    label = f"{prices2[i]:+.0f}%"[:4]  # Truncate to fit in bar width
                    line += f"{label:^4}"
                else:
                    line += "    "
            else:
                # Single stock display
                if mode == 'change':
                    # For change mode, bars go up or down from baseline
                    if prices1[i] >= 0:
                        # Positive: show bar from baseline up
                        bar_height = max(1, int((prices1[i] / max(abs(max_price), abs(min_price))) * (max_height // 2)))
                        show_bar = row > baseline_position and row <= (baseline_position + bar_height)
                        # Show label above positive bars (including 0%) - ensure it's within bounds
                        label_row = min(baseline_position + bar_height + 1, chart_height)
                        show_label = row == label_row
                    else:
                        # Negative: show bar from baseline down
                        bar_height = max(1, int((abs(prices1[i]) / max(abs(max_price), abs(min_price))) * (max_height // 2)))
                        show_bar = row >= (baseline_position - bar_height) and row <= baseline_position
                        # Show label below negative bars - if it would go out of bounds, show above baseline instead
                        ideal_label_row = baseline_position - bar_height - 1
                        if ideal_label_row < 1:
                            # If label would be out of bounds, place it above the baseline
                            label_row = baseline_position + 1
                        else:
                            label_row = ideal_label_row
                        show_label = row == label_row
                
                else:
                    # Price mode - calculate bar height and label position
                    normalized_height = max(1, int(((prices1[i] - min_price) / price_range) * max_height))
                    show_bar = row <= normalized_height
                    
                    # Show price label above bar - ensure it's within bounds
                    label_row = min(normalized_height + 1, chart_height)
                    show_label = row == label_row
                
                if i > 0:
                    line += "  "  # Space between columns
                
                if show_bar:
                    line += "██████"  # Bar segment
                elif mode == 'price' and show_label:
                    # Show price label above bar
                    label = f"${prices1[i]:.0f}"[:6]  # Format price and truncate to fit
                    line += f"{label:^6}"
                elif mode == 'change' and show_label:
                    # Show percentage label above/below bar
                    label = f"{prices1[i]:+.0f}%"[:6]  # Truncate to fit in bar width
                    line += f"{label:^6}"
                else:
                    line += "      "  # Empty space
        print(line)
    
    # Remove the separate label section since labels are now embedded
    # Show legend if comparing two stocks
    if prices2 is not None:
        print()
        print(f"{RED}████{RESET} {ticker_symbol}    {GREEN}████{RESET} {ticker_symbol2}")
    
    print()  # Add spacing

def create_change_chart(stock_data, width=80, height=10, title="Daily Change %"):
    changes = stock_data['Close'].pct_change() * 100
    
    # Calculate max change for scaling
    max_change = max(abs(changes.max()), abs(changes.min())) if not changes.empty else 1
    
    # Chart title
    title = title[:width]  # Truncate title to fit width
    title_padding = (width - len(title)) // 2
    chart = ["" for _ in range(height + 4)]  # Extra space for title and labels
    
    # Create baseline
    baseline_row = height // 2 + 2
    chart[baseline_row] = " " * width
    
    # Draw bars
    for i, change in enumerate(changes):
        if abs(change) > 0.01:  # Only show significant changes
            bar_height = max(1, int(abs(change) * height / max_change))
            if change > 0:
                # Positive change
                for h in range(bar_height):
                    if baseline_row - h - 1 >= 0:
                        chart[baseline_row - h - 1] = (
                            chart[baseline_row - h - 1][:i * 8] + "█" + chart[baseline_row - h - 1][i * 8 + 1:]
                        )
            else:
                # Negative change
                for h in range(bar_height):
                    if baseline_row + h + 1 < len(chart):
                        chart[baseline_row + h + 1] = (
                            chart[baseline_row + h + 1][:i * 8] + "█" + chart[baseline_row + h + 1][i * 8 + 1:]
                        )
    
    # Add percentage labels
    for i, change in enumerate(changes):
        if abs(change) > 0.01:  # Show labels for changes > 0.01%
            bar_height = max(1, int(abs(change) * height / max_change))
            
            # Calculate label position more carefully
            if change > 0:
                # For positive changes, place label above the bar
                if bar_height == 1:
                    # For very small positive bars, place label 2 rows above baseline
                    label_row = baseline_row - 2
                else:
                    # For larger bars, place at the top
                    label_row = baseline_row - bar_height - 1
            else:
                # For negative changes, place label below the bar
                if bar_height == 1:
                    # For very small negative bars, place label 2 rows below baseline
                    label_row = baseline_row + 2
                else:
                    # For larger bars, place at the bottom
                    label_row = baseline_row + bar_height + 1
            
            # Ensure label is within chart bounds
            if 0 <= label_row < height + 4:  # Extended bounds for labels
                label = f"{change:+.0f}%"
                # Calculate horizontal position to center the label
                label_start = max(0, i * 8 + 4 - len(label) // 2)
                label_end = min(width, label_start + len(label))
                
                # Only place label if it fits within bounds
                if label_start < width and label_end > 0:
                    # Adjust label if it would be cut off
                    if label_end > width:
                        label = label[:width - label_start]
                    if label_start < 0:
                        label = label[-label_start:]
                        label_start = 0
                    
                    # Place the label
                    existing_line = chart[label_row] if label_row < len(chart) else ' ' * width
                    chart[label_row] = existing_line[:label_start] + label + existing_line[label_start + len(label):]

    # Add title to chart
    chart_title = f"{'=' * title_padding}{title}{'=' * (width - len(title) - title_padding)}"
    chart.insert(0, chart_title)
    
    # Print the chart
    for line in chart:
        print(line)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stock Tracker CLI")
    parser.add_argument("ticker", help="Stock ticker symbol (e.g., AAPL, GOOGL)")
    parser.add_argument("ticker2", nargs="?", help="Second stock ticker for comparison (optional)")
    parser.add_argument("--days", type=int, default=7, help="Number of days to display (default: 7)")
    parser.add_argument("--mode", choices=['price', 'change'], default='price', 
                       help="Display mode: 'price' for absolute prices, 'change' for percentage change from first day (default: price)")
    args = parser.parse_args()

    # Get data for first stock
    current_price1, historical_data1, error1 = get_stock_data(args.ticker, args.days)
    
    # Get data for second stock if provided
    current_price2, historical_data2, error2 = None, None, None
    if args.ticker2:
        current_price2, historical_data2, error2 = get_stock_data(args.ticker2, args.days)

    # Display results
    if error1:
        print(error1)
    else:
        if current_price1 is not None:
            print(f"The current price of {args.ticker} is: ${current_price1:.2f}")
        
        if args.ticker2:
            if error2:
                print(error2)
            elif current_price2 is not None:
                print(f"The current price of {args.ticker2} is: ${current_price2:.2f}")

        if historical_data1 is not None and not historical_data1.empty:
            display_trend(historical_data1, args.ticker, historical_data2, args.ticker2, args.mode)
        else:
            print("No historical data available to display trend.")
