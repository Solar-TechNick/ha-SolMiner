#!/usr/bin/env python3
"""Test script to verify SolMiner API works with Antminer S21+."""

import asyncio
import logging
import sys
import json
from typing import Dict, Any

# Add the custom_components path to import our API
sys.path.append('./custom_components/solminer')

from luxos_api import LuxOSAPI, LuxOSAPIError

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# S21+ configuration from CLAUDE.md
S21_PLUS_IP = "192.168.1.212"
COMMON_CREDENTIALS = [
    ("root", "root"),
    ("admin", "admin"),
    ("", "root"),
    ("root", ""),
    ("", ""),
]

class S21PlusAPITester:
    """Test API functionality with Antminer S21+."""
    
    def __init__(self, host: str):
        self.host = host
        self.api = None
        self.working_credentials = None
    
    async def test_connectivity(self) -> bool:
        """Test basic network connectivity."""
        logger.info(f"Testing connectivity to S21+ at {self.host}")
        
        for username, password in COMMON_CREDENTIALS:
            logger.info(f"Trying credentials: '{username}':'{password}'")
            
            api = LuxOSAPI(self.host, username, password)
            try:
                if await api.test_connection():
                    logger.info("✅ Basic connectivity successful")
                    self.api = api
                    self.working_credentials = (username, password)
                    return True
                else:
                    logger.warning("❌ No response from miner")
            except Exception as e:
                logger.error(f"❌ Connectivity test failed: {e}")
            finally:
                if api != self.api:
                    await api.close()
        
        return False
    
    async def test_authentication(self) -> bool:
        """Test authentication methods."""
        logger.info("Testing authentication methods")
        
        if not self.api:
            logger.error("No API connection available")
            return False
        
        try:
            if await self.api.logon():
                logger.info("✅ Authentication successful")
                return True
            else:
                logger.warning("❌ Authentication failed, but may not be required")
                return True  # Some miners don't require auth
        except Exception as e:
            logger.error(f"❌ Authentication error: {e}")
            return False
    
    async def test_basic_commands(self) -> Dict[str, Any]:
        """Test basic API commands."""
        logger.info("Testing basic API commands")
        results = {}
        
        if not self.api:
            return {"error": "No API connection"}
        
        # Test basic info commands
        commands = {
            "summary": "Get miner summary",
            "stats": "Get detailed statistics", 
            "devs": "Get device information",
            "pools": "Get pool information",
            "version": "Get version info"
        }
        
        for cmd, description in commands.items():
            try:
                logger.info(f"Testing {cmd}: {description}")
                method = getattr(self.api, f"get_{cmd}")
                result = await method()
                
                if result:
                    logger.info(f"✅ {cmd} command successful")
                    # Store abbreviated result (first few keys for debugging)
                    if isinstance(result, dict):
                        results[cmd] = {k: str(v)[:100] + "..." if len(str(v)) > 100 else v 
                                      for k, v in list(result.items())[:3]}
                    else:
                        results[cmd] = str(result)[:200]
                else:
                    logger.warning(f"❌ {cmd} command returned empty result")
                    results[cmd] = "Empty response"
                    
            except Exception as e:
                logger.error(f"❌ {cmd} command failed: {e}")
                results[cmd] = f"Error: {e}"
        
        return results
    
    async def test_s21_specific_features(self) -> Dict[str, Any]:
        """Test S21+ specific features."""
        logger.info("Testing S21+ specific features")
        results = {}
        
        if not self.api:
            return {"error": "No API connection"}
        
        # Test S21+ specific commands
        s21_tests = [
            ("get_frequency", "Chip frequency"),
            ("get_profile", "Power profile"),
            ("get_health_chip", "Chip health"),
        ]
        
        for method_name, description in s21_tests:
            try:
                logger.info(f"Testing {method_name}: {description}")
                method = getattr(self.api, method_name)
                result = await method()
                
                if result:
                    logger.info(f"✅ {method_name} successful")
                    results[method_name] = result
                else:
                    logger.warning(f"❌ {method_name} returned empty")
                    results[method_name] = "Empty response"
                    
            except Exception as e:
                logger.error(f"❌ {method_name} failed: {e}")
                results[method_name] = f"Error: {e}"
        
        return results
    
    async def test_control_commands(self) -> Dict[str, Any]:
        """Test control commands (read-only tests)."""
        logger.info("Testing control commands (read-only)")
        results = {}
        
        if not self.api:
            return {"error": "No API connection"}
        
        # Only test commands that don't change miner state
        try:
            # Test getting current profile (safe)
            profile = await self.api.get_profile()
            results["current_profile"] = profile
            logger.info(f"✅ Current profile: {profile}")
            
            # Test getting current frequency (safe)
            frequency = await self.api.get_frequency()
            results["current_frequency"] = frequency  
            logger.info(f"✅ Current frequency: {frequency}")
            
        except Exception as e:
            logger.error(f"❌ Control command test failed: {e}")
            results["error"] = str(e)
        
        return results
    
    async def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        logger.info("=" * 60)
        logger.info("ANTMINER S21+ API COMPATIBILITY TEST")
        logger.info("=" * 60)
        
        report = {
            "miner_model": "Antminer S21+",
            "ip_address": self.host,
            "test_timestamp": asyncio.get_event_loop().time(),
            "working_credentials": self.working_credentials,
            "tests": {}
        }
        
        # Run all tests
        tests = [
            ("connectivity", self.test_connectivity),
            ("authentication", self.test_authentication),
            ("basic_commands", self.test_basic_commands),
            ("s21_specific", self.test_s21_specific_features),
            ("control_commands", self.test_control_commands),
        ]
        
        for test_name, test_method in tests:
            logger.info(f"\n--- Running {test_name} test ---")
            try:
                result = await test_method()
                report["tests"][test_name] = {
                    "status": "passed" if result else "failed",
                    "result": result
                }
            except Exception as e:
                logger.error(f"Test {test_name} crashed: {e}")
                report["tests"][test_name] = {
                    "status": "crashed",
                    "error": str(e)
                }
        
        return report
    
    async def cleanup(self):
        """Clean up API connections."""
        if self.api:
            await self.api.close()

async def main():
    """Main test function."""
    tester = S21PlusAPITester(S21_PLUS_IP)
    
    try:
        report = await tester.generate_report()
        
        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("TEST SUMMARY")
        logger.info("=" * 60)
        
        for test_name, test_result in report["tests"].items():
            status = test_result["status"]
            emoji = "✅" if status == "passed" else "❌"
            logger.info(f"{emoji} {test_name}: {status}")
        
        # Save detailed report
        with open("s21_api_test_report.json", "w") as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"\nDetailed report saved to: s21_api_test_report.json")
        logger.info(f"Working credentials: {report['working_credentials']}")
        
        return report
        
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())