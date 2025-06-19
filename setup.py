from setuptools import setup

setup(
    name='stock',
    version='0.1',
    py_modules=['stock_tracker', 'portfolio', 'tax_config'],
    entry_points={
        'console_scripts': [
            'stock = stock_tracker:main',
        ],
    },
    install_requires=[
        'yfinance',
        'asciichartpy',
        'rich',
    ],
) 