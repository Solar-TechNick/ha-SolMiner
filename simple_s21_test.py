#!/usr/bin/env python3
"""Simple test script to verify S21+ connectivity without external dependencies."""

import socket
import json
import time
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from urllib.error import URLError, HTTPError

# S21+ configuration
S21_PLUS_IP = "192.168.1.212"
TIMEOUT = 10

def test_basic_connectivity(host):
    """Test basic network connectivity."""
    print(f"Testing basic connectivity to {host}...")
    
    # Test port 80 (HTTP)
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, 80))
        sock.close()
        
        if result == 0:
            print("✅ Port 80 (HTTP) is reachable")
            return True
        else:
            print("❌ Port 80 (HTTP) is not reachable")
    except Exception as e:
        print(f"❌ Connectivity test failed: {e}")
    
    # Test port 4028 (CGMiner API)
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, 4028))
        sock.close()
        
        if result == 0:
            print("✅ Port 4028 (CGMiner API) is reachable")
            return True
        else:
            print("❌ Port 4028 (CGMiner API) is not reachable")
    except Exception as e:
        print(f"❌ CGMiner API test failed: {e}")
    
    return False

def test_http_endpoints(host):
    """Test various HTTP endpoints."""
    print(f"\nTesting HTTP endpoints on {host}...")
    
    endpoints = [
        "/",
        "/cgi-bin/luci/api",
        "/cgi-bin/api.cgi",
        "/api",
        "/cgi-bin/minerapi.cgi",
        "/cgi-bin/minerApi.cgi"
    ]
    
    working_endpoints = []
    
    for endpoint in endpoints:
        try:
            url = f"http://{host}{endpoint}"
            print(f"Testing: {url}")
            
            request = Request(url)
            request.add_header('User-Agent', 'SolMiner-Test/1.0')
            
            with urlopen(request, timeout=TIMEOUT) as response:
                status = response.getcode()
                content = response.read()[:500]  # First 500 bytes
                
                print(f"  ✅ Status: {status}")
                if content:
                    print(f"  📄 Content preview: {content[:100]}...")
                
                working_endpoints.append((endpoint, status))
                
        except HTTPError as e:
            print(f"  ⚠️  HTTP Error {e.code}: {e.reason}")
            if e.code in [401, 403]:  # Auth required, but endpoint exists
                working_endpoints.append((endpoint, e.code))
        except URLError as e:
            print(f"  ❌ URL Error: {e.reason}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    return working_endpoints

def test_cgminer_api(host):
    """Test CGMiner API on port 4028."""
    print(f"\nTesting CGMiner API on {host}:4028...")
    
    commands = ["summary", "stats", "devs", "pools", "version"]
    
    for command in commands:
        try:
            print(f"Testing command: {command}")
            
            # CGMiner API uses TCP socket communication
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(TIMEOUT)
            
            sock.connect((host, 4028))
            
            # Send command
            cmd_data = json.dumps({"command": command}).encode()
            sock.send(cmd_data)
            
            # Receive response
            response = sock.recv(4096)
            sock.close()
            
            if response:
                try:
                    data = json.loads(response.decode())
                    print(f"  ✅ {command}: Success")
                    print(f"  📊 Data preview: {str(data)[:100]}...")
                except json.JSONDecodeError:
                    print(f"  ⚠️  {command}: Non-JSON response: {response[:100]}")
            else:
                print(f"  ❌ {command}: No response")
                
        except socket.timeout:
            print(f"  ❌ {command}: Timeout")
        except ConnectionRefusedError:
            print(f"  ❌ {command}: Connection refused")
        except Exception as e:
            print(f"  ❌ {command}: Error: {e}")

def test_api_with_credentials(host):
    """Test API endpoints with different credential combinations."""
    print(f"\nTesting API with credentials on {host}...")
    
    credentials = [
        ("root", "root"),
        ("admin", "admin"),
        ("", "root"),
        ("root", ""),
        ("", ""),
    ]
    
    for username, password in credentials:
        print(f"\nTrying credentials: '{username}':'{password}'")
        
        # Test with POST data
        try:
            url = f"http://{host}/cgi-bin/luci/api"
            
            data = {
                "command": "summary",
                "parameter": ""
            }
            
            if username or password:
                data["username"] = username
                data["password"] = password
            
            post_data = json.dumps(data).encode()
            
            request = Request(url, post_data)
            request.add_header('Content-Type', 'application/json')
            request.add_header('User-Agent', 'SolMiner-Test/1.0')
            
            with urlopen(request, timeout=TIMEOUT) as response:
                status = response.getcode()
                content = response.read()
                
                print(f"  ✅ HTTP {status}")
                
                try:
                    data = json.loads(content.decode())
                    print(f"  📊 JSON Response: {str(data)[:200]}...")
                except json.JSONDecodeError:
                    print(f"  📄 Raw Response: {content[:200]}...")
                
        except HTTPError as e:
            print(f"  ❌ HTTP Error {e.code}: {e.reason}")
        except Exception as e:
            print(f"  ❌ Error: {e}")

def main():
    """Main test function."""
    print("=" * 60)
    print("ANTMINER S21+ API CONNECTIVITY TEST")
    print("=" * 60)
    print(f"Target: {S21_PLUS_IP}")
    print(f"Timestamp: {time.ctime()}")
    print("=" * 60)
    
    # Test basic connectivity
    if not test_basic_connectivity(S21_PLUS_IP):
        print("\n❌ CRITICAL: Cannot reach the miner at all!")
        print("Please verify:")
        print("1. IP address is correct (192.168.1.212)")
        print("2. Miner is powered on")
        print("3. Network connectivity")
        print("4. Firewall settings")
        return False
    
    # Test HTTP endpoints
    working_endpoints = test_http_endpoints(S21_PLUS_IP)
    
    # Test CGMiner API
    test_cgminer_api(S21_PLUS_IP)
    
    # Test with credentials
    test_api_with_credentials(S21_PLUS_IP)
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    if working_endpoints:
        print("✅ Working HTTP endpoints found:")
        for endpoint, status in working_endpoints:
            print(f"   {endpoint} (HTTP {status})")
    else:
        print("❌ No working HTTP endpoints found")
    
    print(f"\nNext steps:")
    print("1. If endpoints are working, check Home Assistant logs for detailed errors")
    print("2. Try the SolMiner integration with the working endpoints")
    print("3. Verify LuxOS firmware version on the S21+")
    
    return len(working_endpoints) > 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)