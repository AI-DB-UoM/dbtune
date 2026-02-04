#!/usr/bin/env python3
"""
Example script demonstrating the new configuration system for DBTune.

This script shows how to:
1. Load configuration from YAML file
2. Access different configuration sections
3. Use configuration in the BanditTuner
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def example_basic_config_loading():
    """Example 1: Basic configuration loading"""
    print("=" * 60)
    print("Example 1: Basic Configuration Loading")
    print("=" * 60)
    
    from config_loader import load_config, get_config
    
    # Load configuration from default location
    try:
        config = load_config()
        print("✓ Configuration loaded successfully")
        
        # Print all sections
        for section, values in config.items():
            print(f"\n[{section}]")
            if isinstance(values, dict):
                for key, value in values.items():
                    if key != 'password':  # Don't print passwords
                        print(f"  {key}: {value}")
            else:
                print(f"  {values}")
    except FileNotFoundError as e:
        print(f"✗ Error: {e}")


def example_database_config():
    """Example 2: Accessing database configuration"""
    print("\n" + "=" * 60)
    print("Example 2: Database Configuration")
    print("=" * 60)
    
    from config_loader import load_config, get_db_config
    
    try:
        load_config()
        db_config = get_db_config()
        
        print("\nDatabase Configuration:")
        for key, value in db_config.items():
            if key != 'password':
                print(f"  {key}: {value}")
        
        # Example: Connect to database
        print("\nConnection String (without password):")
        conn_str = f"postgresql://{db_config['user']}@{db_config['host']}:{db_config['port']}/{db_config['dbname']}"
        print(f"  {conn_str}")
        
    except Exception as e:
        print(f"✗ Error: {e}")


def example_system_config():
    """Example 3: Accessing system configuration"""
    print("\n" + "=" * 60)
    print("Example 3: System Configuration")
    print("=" * 60)
    
    from config_loader import load_config, get_system_config
    
    try:
        load_config()
        system_config = get_system_config()
        
        print("\nSystem Configuration:")
        for key, value in system_config.items():
            print(f"  {key}: {value}")
        
        # Example: Check if tuning is enabled
        if system_config['enable_tune']:
            print("\n✓ Tuning is ENABLED")
            if system_config['with_mv']:
                print("✓ Materialized Views are ENABLED")
            else:
                print("✗ Materialized Views are DISABLED")
        else:
            print("\n✗ Tuning is DISABLED")
            
    except Exception as e:
        print(f"✗ Error: {e}")


def example_tuning_config():
    """Example 4: Accessing tuning configuration"""
    print("\n" + "=" * 60)
    print("Example 4: Tuning Configuration")
    print("=" * 60)
    
    from config_loader import load_config, get_tuning_config
    
    try:
        load_config()
        tuning_config = get_tuning_config()
        
        print("\nTuning Configuration:")
        for key, value in tuning_config.items():
            print(f"  {key}: {value}")
        
        # Example: Print tuning strategy
        print(f"\nTuning Strategy:")
        print(f"  Total rounds: {tuning_config['rounds']}")
        print(f"  Hypothesis checks per round: {tuning_config['hyp_check_rounds']}")
        print(f"  Context size: {tuning_config['super_static_context_size']}")
        
    except Exception as e:
        print(f"✗ Error: {e}")


def example_bandit_config():
    """Example 5: Accessing bandit algorithm configuration"""
    print("\n" + "=" * 60)
    print("Example 5: Bandit Algorithm Configuration")
    print("=" * 60)
    
    from config_loader import load_config, get_bandit_config
    
    try:
        load_config()
        bandit_config = get_bandit_config()
        
        print("\nBandit Algorithm Configuration:")
        for key, value in bandit_config.items():
            print(f"  {key}: {value}")
        
        # Example: Explain parameters
        print(f"\nParameter Interpretation:")
        print(f"  input_alpha = {bandit_config['input_alpha']}")
        print(f"    → Controls exploration vs exploitation")
        print(f"    → Lower value = more exploitation")
        print(f"    → Higher value = more exploration")
        
        print(f"\n  input_lambda = {bandit_config['input_lambda']}")
        print(f"    → Regularization parameter")
        print(f"    → Higher value = stronger regularization")
        
    except Exception as e:
        print(f"✗ Error: {e}")


def example_logging_config():
    """Example 6: Accessing logging configuration"""
    print("\n" + "=" * 60)
    print("Example 6: Logging Configuration")
    print("=" * 60)
    
    from config_loader import load_config, get_logging_config
    
    try:
        load_config()
        logging_config = get_logging_config()
        
        print("\nLogging Configuration:")
        for key, value in logging_config.items():
            print(f"  {key}: {value}")
        
        # Example: Validate log level
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if logging_config['log_level'] in valid_levels:
            print(f"\n✓ Log level '{logging_config['log_level']}' is valid")
        else:
            print(f"\n✗ Log level '{logging_config['log_level']}' is invalid")
            print(f"  Valid levels: {', '.join(valid_levels)}")
        
    except Exception as e:
        print(f"✗ Error: {e}")


def example_using_bandit_tuner():
    """Example 7: Using configuration with BanditTuner"""
    print("\n" + "=" * 60)
    print("Example 7: Using Configuration with BanditTuner")
    print("=" * 60)
    
    print("\nExample Code:")
    print("""
from bandits.sim_c3ucb_vF import BanditTuner

# Create tuner instance
# Configuration is automatically loaded from config.yaml
tuner = BanditTuner()

# Access configuration through tuner instance
print(f"Enable tune: {tuner.enable_tune}")
print(f"With MV: {tuner.with_mv}")
print(f"Max memory: {tuner.max_memory}")
print(f"Rounds: {tuner.rounds}")
print(f"Input alpha: {tuner.input_alpha}")
print(f"Input lambda: {tuner.input_lambda}")

# Get database config
db_config = tuner.get_db_config()
print(f"Database: {db_config['dbname']}@{db_config['host']}")
""")
    
    print("\nNote: This requires PostgreSQL to be running and database to be accessible.")


def example_multiple_configs():
    """Example 8: Using multiple configuration files"""
    print("\n" + "=" * 60)
    print("Example 8: Using Multiple Configuration Files")
    print("=" * 60)
    
    print("\nExample Code:")
    print("""
from config_loader import load_config, get_db_config

# Load development configuration
load_config('config.dev.yaml')
dev_db = get_db_config()
print(f"Dev database: {dev_db['dbname']}@{dev_db['host']}")

# Load production configuration
load_config('config.prod.yaml')
prod_db = get_db_config()
print(f"Prod database: {prod_db['dbname']}@{prod_db['host']}")

# Load test configuration
load_config('config.test.yaml')
test_db = get_db_config()
print(f"Test database: {test_db['dbname']}@{test_db['host']}")
""")


def example_dot_notation():
    """Example 9: Using dot notation to access config"""
    print("\n" + "=" * 60)
    print("Example 9: Dot Notation Access")
    print("=" * 60)
    
    from config_loader import load_config, _config_loader
    
    try:
        load_config()
        
        print("\nAccessing config values using dot notation:")
        
        values = [
            'database.dbname',
            'database.host',
            'database.port',
            'system.enable_tune',
            'system.max_memory',
            'tuning.rounds',
            'bandit.input_alpha',
            'logging.log_level',
        ]
        
        for key in values:
            value = _config_loader.get(key)
            print(f"  {key}: {value}")
        
    except Exception as e:
        print(f"✗ Error: {e}")


def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("DBTune Configuration System - Examples")
    print("=" * 60)
    
    # Run all examples
    try:
        example_basic_config_loading()
        example_database_config()
        example_system_config()
        example_tuning_config()
        example_bandit_config()
        example_logging_config()
        example_using_bandit_tuner()
        example_multiple_configs()
        example_dot_notation()
        
        print("\n" + "=" * 60)
        print("All examples completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
