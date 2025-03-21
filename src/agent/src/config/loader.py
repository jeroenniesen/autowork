import os
import yaml
import json
import redis
from typing import Dict, Any, Optional, List

class ConfigLoader:
    """Configuration loader for agent profiles with Redis support."""
    
    def __init__(self, profiles_dir: str = "profiles", redis_url: Optional[str] = None):
        """Initialize the config loader.
        
        Args:
            profiles_dir: Directory containing agent profile configurations
            redis_url: Optional Redis URL for profile storage
        """
        self.profiles_dir = profiles_dir
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://redis:6379")
        self._config_cache = {}
        self._redis_client = redis.from_url(self.redis_url)
    
    def get_profile(self, profile_name: str = "default") -> Dict[str, Any]:
        """Load a specific agent profile configuration.
        
        Args:
            profile_name: Name of the profile to load
            
        Returns:
            Dict containing the profile configuration
            
        Raises:
            FileNotFoundError: If the profile doesn't exist
        """
        # First check Redis
        redis_key = f"profile:{profile_name}"
        profile_data = self._redis_client.get(redis_key)
        
        if profile_data:
            return json.loads(profile_data)
            
        # If not in Redis, check file system
        if profile_name in self._config_cache:
            return self._config_cache[profile_name]
            
        profile_path = os.path.join(self.profiles_dir, f"{profile_name}.yaml")
        
        if not os.path.exists(profile_path):
            raise FileNotFoundError(f"Profile '{profile_name}' not found")
            
        with open(profile_path, 'r') as file:
            config = yaml.safe_load(file)
            
        # Cache the config
        self._config_cache[profile_name] = config
        
        # Store in Redis for future use
        self._redis_client.set(redis_key, json.dumps(config))
        
        return config
    
    def list_available_profiles(self) -> List[str]:
        """List all available profile names."""
        profiles = set()
        
        # Get profiles from Redis
        redis_keys = self._redis_client.keys("profile:*")
        for key in redis_keys:
            profile_name = key.decode('utf-8').split(':')[1]
            profiles.add(profile_name)
        
        # Get profiles from filesystem
        if os.path.exists(self.profiles_dir):
            for file in os.listdir(self.profiles_dir):
                if file.endswith(".yaml"):
                    profiles.add(file[:-5])  # Remove .yaml extension
        
        return list(profiles)
    
    def save_profile(self, profile_name: str, config: Dict[str, Any]) -> None:
        """Save a profile configuration to Redis.
        
        Args:
            profile_name: Name of the profile
            config: Profile configuration dictionary
        """
        redis_key = f"profile:{profile_name}"
        self._redis_client.set(redis_key, json.dumps(config))
        self._config_cache[profile_name] = config
    
    def delete_profile(self, profile_name: str) -> bool:
        """Delete a profile from Redis.
        
        Args:
            profile_name: Name of the profile to delete
            
        Returns:
            bool: True if profile was deleted, False if it didn't exist
        """
        redis_key = f"profile:{profile_name}"
        deleted = self._redis_client.delete(redis_key)
        
        if profile_name in self._config_cache:
            del self._config_cache[profile_name]
            
        return deleted > 0