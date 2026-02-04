#!/usr/bin/env python3
"""
Test script for the configuration system.

This script validates that:
1. Configuration file exists and is valid
2. All required parameters are present
3. Configuration loader works correctly
4. BanditTuner can load configuration
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_config_file_exists():
    """Test 1: Check if config.yaml exists"""
    print("\n[Test 1] Configuration file exists")
    
    config_paths = [
        os.path.join(os.path.dirname(__file__), 'configs', 'config.yaml'),
        'config.yaml',
        os.path.join(os.path.dirname(__file__), 'config.yaml'),
        os.path.join(os.path.dirname(__file__), '..', 'config.yaml'),
    ]
    
    for path in config_paths:
        if os.path.exists(path):
            print(f"  ✓ Found: {path}")
            return True
    
    print(f"  ✗ Config file not found in:")
    for path in config_paths:
        print(f"    - {path}")
    return False


def test_yaml_parsing():
    """Test 2: Verify YAML file can be parsed"""
    print("\n[Test 2] YAML file is valid")
    
    try:
        import yaml
    except ImportError:
        print("  ✗ PyYAML not installed. Install with: pip install pyyaml")
        return False
    
    try:
        # Find config file
        config_file = None

        config_paths = [
            os.path.join(os.path.dirname(__file__), 'configs', 'config.yaml'),
            'config.yaml',
            os.path.join(os.path.dirname(__file__), 'config.yaml'),
            os.path.join(os.path.dirname(__file__), '..', 'config.yaml'),
        ]
        
        for path in config_paths:
            if os.path.exists(path):
                config_file = path
                break

        if not config_file:
            print("  ✗ Config file not found")
            return False
        
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        if config is None:
            print("  ✗ Config file is empty")
            return False
        
        print(f"  ✓ YAML parsed successfully")
        print(f"    Sections: {', '.join(config.keys())}")
        return True
        
    except yaml.YAMLError as e:
        print(f"  ✗ YAML parsing error: {e}")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_config_loader_import():
    """Test 3: Import config_loader module"""
    print("\n[Test 3] Config loader module imports")
    
    try:
        from config_loader import (
            load_config,
            get_config,
            get_db_config,
            get_system_config,
            get_tuning_config,
            get_bandit_config,
            get_logging_config,
        )
        print("  ✓ All functions imported successfully")
        return True
    except ImportError as e:
        print(f"  ✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_config_loading():
    """Test 4: Load configuration"""
    print("\n[Test 4] Configuration loads successfully")
    
    try:
        from config_loader import load_config, get_config
        
        config = load_config()
        
        if not config:
            print("  ✗ Configuration is empty")
            return False
        
        required_sections = ['database', 'system', 'tuning', 'bandit', 'logging']
        missing_sections = [s for s in required_sections if s not in config]
        
        if missing_sections:
            print(f"  ✗ Missing sections: {', '.join(missing_sections)}")
            return False
        
        print("  ✓ Configuration loaded successfully")
        print(f"    Sections: {', '.join(config.keys())}")
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_database_config():
    """Test 5: Database configuration is valid"""
    print("\n[Test 5] Database configuration")
    
    try:
        from config_loader import load_config, get_db_config
        
        load_config()
        db_config = get_db_config()
        
        required_fields = ['dbname', 'user', 'host', 'port']
        missing_fields = [f for f in required_fields if f not in db_config]
        
        if missing_fields:
            print(f"  ✗ Missing fields: {', '.join(missing_fields)}")
            return False
        
        print("  ✓ Database configuration valid")
        print(f"    dbname: {db_config['dbname']}")
        print(f"    user: {db_config['user']}")
        print(f"    host: {db_config['host']}")
        print(f"    port: {db_config['port']}")
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_system_config():
    """Test 6: System configuration is valid"""
    print("\n[Test 6] System configuration")
    
    try:
        from config_loader import load_config, get_system_config
        
        load_config()
        system_config = get_system_config()
        
        required_fields = ['enable_tune', 'with_mv', 'mv', 'max_memory', 'hyp_file']
        missing_fields = [f for f in required_fields if f not in system_config]
        
        if missing_fields:
            print(f"  ✗ Missing fields: {', '.join(missing_fields)}")
            return False
        
        # Validate types
        if not isinstance(system_config['enable_tune'], bool):
            print("  ✗ enable_tune should be boolean")
            return False
        
        if not isinstance(system_config['max_memory'], int):
            print("  ✗ max_memory should be integer")
            return False
        
        print("  ✓ System configuration valid")
        print(f"    enable_tune: {system_config['enable_tune']}")
        print(f"    with_mv: {system_config['with_mv']}")
        print(f"    max_memory: {system_config['max_memory']} MB")
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_tuning_config():
    """Test 7: Tuning configuration is valid"""
    print("\n[Test 7] Tuning configuration")
    
    try:
        from config_loader import load_config, get_tuning_config
        
        load_config()
        tuning_config = get_tuning_config()
        
        required_fields = ['hyp_check_rounds', 'rounds', 'super_static_context_size', 'cluster_id_start']
        missing_fields = [f for f in required_fields if f not in tuning_config]
        
        if missing_fields:
            print(f"  ✗ Missing fields: {', '.join(missing_fields)}")
            return False
        
        # Validate all are integers
        for field in required_fields:
            if not isinstance(tuning_config[field], int):
                print(f"  ✗ {field} should be integer")
                return False
        
        # Validate ranges
        if tuning_config['rounds'] <= 0:
            print("  ✗ rounds should be positive")
            return False
        
        print("  ✓ Tuning configuration valid")
        print(f"    rounds: {tuning_config['rounds']}")
        print(f"    hyp_check_rounds: {tuning_config['hyp_check_rounds']}")
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_bandit_config():
    """Test 8: Bandit configuration is valid"""
    print("\n[Test 8] Bandit configuration")
    
    try:
        from config_loader import load_config, get_bandit_config
        
        load_config()
        bandit_config = get_bandit_config()
        
        required_fields = ['input_alpha', 'input_lambda']
        missing_fields = [f for f in required_fields if f not in bandit_config]
        
        if missing_fields:
            print(f"  ✗ Missing fields: {', '.join(missing_fields)}")
            return False
        
        # Validate ranges
        if not (0 <= bandit_config['input_alpha'] <= 1):
            print(f"  ✗ input_alpha should be between 0 and 1")
            return False
        
        if not isinstance(bandit_config['input_lambda'], (int, float)):
            print(f"  ✗ input_lambda should be numeric")
            return False
        
        print("  ✓ Bandit configuration valid")
        print(f"    input_alpha: {bandit_config['input_alpha']}")
        print(f"    input_lambda: {bandit_config['input_lambda']}")
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_logging_config():
    """Test 9: Logging configuration is valid"""
    print("\n[Test 9] Logging configuration")
    
    try:
        from config_loader import load_config, get_logging_config
        
        load_config()
        logging_config = get_logging_config()
        
        required_fields = ['log_file', 'log_level']
        missing_fields = [f for f in required_fields if f not in logging_config]
        
        if missing_fields:
            print(f"  ✗ Missing fields: {', '.join(missing_fields)}")
            return False
        
        # Validate log level
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if logging_config['log_level'] not in valid_levels:
            print(f"  ✗ Invalid log level: {logging_config['log_level']}")
            print(f"    Valid levels: {', '.join(valid_levels)}")
            return False
        
        print("  ✓ Logging configuration valid")
        print(f"    log_file: {logging_config['log_file']}")
        print(f"    log_level: {logging_config['log_level']}")
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_singleton_pattern():
    """Test 10: ConfigLoader singleton pattern"""
    print("\n[Test 10] Singleton pattern works")
    
    try:
        from config_loader import ConfigLoader
        
        loader1 = ConfigLoader()
        loader2 = ConfigLoader()
        
        if loader1 is not loader2:
            print("  ✗ Singleton pattern not working")
            return False
        
        print("  ✓ Singleton pattern verified")
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("DBTune Configuration System - Tests")
    print("=" * 60)
    
    tests = [
        test_config_file_exists,
        test_yaml_parsing,
        test_config_loader_import,
        test_config_loading,
        test_database_config,
        test_system_config,
        test_tuning_config,
        test_bandit_config,
        test_logging_config,
        test_singleton_pattern,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\n  ✗ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n✓ All tests passed!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
