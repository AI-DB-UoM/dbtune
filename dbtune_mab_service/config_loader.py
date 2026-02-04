"""
Configuration Loader Module

This module loads configuration from YAML file and provides helper functions
to access configuration values throughout the application.
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigLoader:
    """Handles loading and accessing configuration from YAML files."""
    
    _instance = None
    _config: Optional[Dict[str, Any]] = None
    
    def __new__(cls):
        """Singleton pattern to ensure only one config instance exists."""
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
        return cls._instance
    
    def load_config(self, config_file: str = None) -> Dict[str, Any]:
        """
        Load configuration from YAML file.
        
        Args:
            config_file: Path to config file. If None, uses default './config.yaml'
                        Supports relative and absolute paths.
        
        Returns:
            Configuration dictionary
            
        Raises:
            FileNotFoundError: If config file does not exist
            yaml.YAMLError: If YAML parsing fails
        """
        if config_file is None:
            # Try multiple default locations
            # Priority: configs/config.yaml > ./config.yaml > module_dir/config.yaml > parent_dir/config.yaml
            default_paths = [
                os.path.join(os.path.dirname(__file__), 'configs', 'config.yaml'),
                './config.yaml',
                os.path.join(os.path.dirname(__file__), 'config.yaml'),
                os.path.join(os.path.dirname(__file__), '..', 'config.yaml'),
            ]
            
            for path in default_paths:
                if os.path.exists(path):
                    config_file = path
                    break
            else:
                raise FileNotFoundError(
                    f"Config file not found. Tried: {default_paths}"
                )
        
        config_path = Path(config_file)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_file}")
        
        try:
            with open(config_path, 'r') as f:
                self._config = yaml.safe_load(f)
                if self._config is None:
                    self._config = {}
                return self._config
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Failed to parse config file: {e}")
    
    def get_config(self) -> Dict[str, Any]:
        """Get loaded configuration. Loads if not already loaded."""
        if self._config is None:
            self.load_config()
        return self._config
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value by dot-notation key.
        
        Args:
            key: Configuration key with dot notation (e.g., 'database.host')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        config = self.get_config()
        keys = key.split('.')
        value = config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value
    
    def get_db_config(self) -> Dict[str, Any]:
        """
        Get database configuration.
        
        Returns:
            Database configuration dictionary with keys:
            - dbname: database name
            - user: database user
            - host: database host
            - port: database port
            - password (optional): database password
        """
        db_config = self.get('database', {})
        
        # Ensure required fields have defaults
        result = {
            'dbname': db_config.get('dbname', 'imdbload'),
            'user': db_config.get('user', 'guanlil1'),
            'host': db_config.get('host', '/var/run/postgresql'),
            'port': db_config.get('port', 5432),
        }
        
        # Add optional password if present
        if 'password' in db_config:
            result['password'] = db_config['password']
        
        return result
    
    def get_system_config(self) -> Dict[str, Any]:
        """
        Get system configuration.
        
        Returns:
            System config with keys: enable_tune, with_mv, mv, max_memory, hyp_file
        """
        system = self.get('system', {})
        
        return {
            'enable_tune': system.get('enable_tune', True),
            'with_mv': system.get('with_mv', True),
            'mv': system.get('mv', 'MV'),
            'max_memory': system.get('max_memory', 25000),
            'hyp_file': system.get('hyp_file', './hyp_files/temp.txt'),
        }
    
    def get_tuning_config(self) -> Dict[str, Any]:
        """
        Get tuning configuration.
        
        Returns:
            Tuning config with keys: hyp_check_rounds, rounds, super_static_context_size, cluster_id_start,
                                    queries_start, batch_size, offset
        """
        tuning = self.get('tuning', {})
        
        return {
            'hyp_check_rounds': tuning.get('hyp_check_rounds', 5),
            'rounds': tuning.get('rounds', 25),
            'super_static_context_size': tuning.get('super_static_context_size', 2),
            'cluster_id_start': tuning.get('cluster_id_start', 1),
            'queries_start': tuning.get('queries_start', 0),
            'batch_size': tuning.get('batch_size', 10),
            'offset': tuning.get('offset', 10),
        }
    
    def get_bandit_config(self) -> Dict[str, Any]:
        """
        Get bandit algorithm configuration.
        
        Returns:
            Bandit config with keys: input_alpha, input_lambda
        """
        bandit = self.get('bandit', {})
        
        return {
            'input_alpha': bandit.get('input_alpha', 0.05),
            'input_lambda': bandit.get('input_lambda', 0.5),
        }
    
    def get_logging_config(self) -> Dict[str, Any]:
        """
        Get logging configuration.
        
        Returns:
            Logging config with keys: log_file, log_level
        """
        logging_conf = self.get('logging', {})
        
        return {
            'log_file': logging_conf.get('log_file', 'test.log'),
            'log_level': logging_conf.get('log_level', 'DEBUG'),
        }
    
    def get_small_table_threshold(self) -> int:
        """
        Get the threshold for ignoring small tables.
        
        Returns:
            Row count threshold for small table ignore
        """
        tables = self.get('tables', {})
        return tables.get('small_table_ignore_threshold', 1000)


# Singleton instance
_config_loader = ConfigLoader()


# Convenience functions for accessing configuration
def load_config(config_file: str = None) -> Dict[str, Any]:
    """Load configuration from file."""
    return _config_loader.load_config(config_file)


def get_config() -> Dict[str, Any]:
    """Get loaded configuration."""
    return _config_loader.get_config()


def get_db_config() -> Dict[str, Any]:
    """Get database configuration."""
    return _config_loader.get_db_config()


def get_system_config() -> Dict[str, Any]:
    """Get system configuration."""
    return _config_loader.get_system_config()


def get_tuning_config() -> Dict[str, Any]:
    """Get tuning configuration."""
    return _config_loader.get_tuning_config()


def get_bandit_config() -> Dict[str, Any]:
    """Get bandit algorithm configuration."""
    return _config_loader.get_bandit_config()


def get_logging_config() -> Dict[str, Any]:
    """Get logging configuration."""
    return _config_loader.get_logging_config()


def get_small_table_threshold() -> int:
    """Get small table threshold."""
    return _config_loader.get_small_table_threshold()
