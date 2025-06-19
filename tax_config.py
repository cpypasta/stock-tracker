import json
import os
from typing import Dict, Optional, Union

TAX_CONFIG_FILE = "tax.json"

class TaxConfig:
    def __init__(self, file_path: str = TAX_CONFIG_FILE):
        self.file_path = file_path
        self.config = self.load_config()
    
    def load_config(self) -> Dict:
        """Load tax configuration from JSON file."""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return self.get_default_config()
        return self.get_default_config()
    
    def get_default_config(self) -> Dict:
        """Get default tax configuration."""
        return {
            'short_term_federal': 0.0,
            'long_term_federal': 0.0,
            'state': 0.0,
            'nii': False
        }
    
    def save_config(self):
        """Save tax configuration to JSON file."""
        with open(self.file_path, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def set_short_term_federal_rate(self, rate: float):
        """Set short-term federal tax rate (as percentage)."""
        self.config['short_term_federal'] = rate
        self.save_config()
    
    def set_long_term_federal_rate(self, rate: float):
        """Set long-term federal tax rate (as percentage)."""
        self.config['long_term_federal'] = rate
        self.save_config()
    
    def set_state_rate(self, rate: float):
        """Set state tax rate (as percentage)."""
        self.config['state'] = rate
        self.save_config()
    
    def set_nii(self, has_nii: bool):
        """Set whether subject to Net Investment Income tax."""
        self.config['nii'] = has_nii
        self.save_config()
    
    def set_all(self, short_term_federal: float, long_term_federal: float, state: float, nii: bool):
        """Set all tax configuration at once."""
        self.config['short_term_federal'] = short_term_federal
        self.config['long_term_federal'] = long_term_federal
        self.config['state'] = state
        self.config['nii'] = nii
        self.save_config()
    
    def get_config(self) -> Dict:
        """Get current tax configuration."""
        return self.config.copy()
    
    def get_short_term_federal_rate(self) -> float:
        """Get short-term federal tax rate."""
        return self.config.get('short_term_federal', 0.0)
    
    def get_long_term_federal_rate(self) -> float:
        """Get long-term federal tax rate."""
        return self.config.get('long_term_federal', 0.0)
    
    def get_state_rate(self) -> float:
        """Get state tax rate."""
        return self.config.get('state', 0.0)
    
    def has_nii(self) -> bool:
        """Check if subject to NII tax."""
        return self.config.get('nii', False)
    
    def calculate_short_term_tax_on_gains(self, gains: float) -> dict:
        federal_rate = self.get_short_term_federal_rate()
        federal_tax = gains * (federal_rate / 100)
        state_tax = gains * (self.get_state_rate() / 100)
        nii_tax = gains * 0.038 if self.has_nii() else 0.0
        return {
            'federal': federal_tax,
            'state': state_tax,
            'nii': nii_tax,
            'total': federal_tax + state_tax + nii_tax,
            'rate_type': 'short-term',
            'federal_rate_used': federal_rate
        }

    def calculate_long_term_tax_on_gains(self, gains: float) -> dict:
        federal_rate = self.get_long_term_federal_rate()
        federal_tax = gains * (federal_rate / 100)
        state_tax = gains * (self.get_state_rate() / 100)
        nii_tax = gains * 0.038 if self.has_nii() else 0.0
        return {
            'federal': federal_tax,
            'state': state_tax,
            'nii': nii_tax,
            'total': federal_tax + state_tax + nii_tax,
            'rate_type': 'long-term',
            'federal_rate_used': federal_rate
        }

# Convenience functions
def get_tax_config() -> TaxConfig:
    """Get tax configuration instance."""
    return TaxConfig()

def set_tax_rates(short_term_federal: float, long_term_federal: float, state: float, nii: bool):
    """Set all tax rates."""
    config = get_tax_config()
    config.set_all(short_term_federal, long_term_federal, state, nii)

def get_tax_rates() -> Dict:
    """Get current tax rates."""
    config = get_tax_config()
    return config.get_config()

def calculate_short_term_tax_on_gains(gains: float) -> dict:
    config = get_tax_config()
    return config.calculate_short_term_tax_on_gains(gains)

def calculate_long_term_tax_on_gains(gains: float) -> dict:
    config = get_tax_config()
    return config.calculate_long_term_tax_on_gains(gains) 