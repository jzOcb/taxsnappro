#!/usr/bin/env python3
"""
WebSocket Infrastructure Test Script

Tests:
1. Kalshi WebSocket connection
2. BRTI proxy latency
3. End-to-end pipeline latency
4. Data quality validation

Usage:
    python3 test_websocket.py [duration_seconds]
"""

import asyncio
import time
import statistics
from datetime import datetime
from typing import List, Dict
import sys

try:
    from kalshi_websocket import KalshiWebSocketClient
    from brti_proxy_enhanced import BTRIProxyEnhanced
except ImportError:
    print("❌ Missing dependencies")
    print("Install with: sudo apt-get install python3-websockets")
    sys.exit(1)


class WebSocketTester:
    """Test harness for WebSocket infrastructure"""
    
    def __init__(self, duration_seconds: int = 60):
        self.duration = duration_seconds
        
        # Metrics
        self.orderbook_latencies = []
        self.brti_latencies = []
        self.orderbook_count = 0
        self.brti_count = 0
        
        # Test results
        self.results = {
            'connection_test': None,
            'latency_test': None,
            'data_quality_test': None,
        }
    
    async def test_connection(self) -> bool:
        """Test 1: Basic WebSocket connection"""
        print("\n" + "="*70)
        print("TEST 1: WebSocket Connection")
        print("="*70)
        
        connected = False
        error_msg = None
        
        def on_error(e):
            nonlocal error_msg
            error_msg = str(e)
        
        client = KalshiWebSocketClient(on_error=on_error)
        
        try:
            # Try to connect
            print("Attempting connection to Kalshi WebSocket...")
            connected = await asyncio.wait_for(client.connect(), timeout=15.0)
            
            if connected:
                print("✅ Connection successful")
                
                # Try to subscribe
                print("Testing subscription to KXBTC15M...")
                subscribed = await client.subscribe_series("KXBTC15M")
                
                if subscribed:
                    print("✅ Subscription successful")
                    
                    # Wait for first message
                    print("Waiting for first message (max 30s)...")
                    start = time.time()
                    
                    while time.time() - start < 30:
                        stats = client.get_stats()
                        if stats['messages_received'] > 0:
                            print(f"✅ Received first message after {time.time()-start:.1f}s")
                            break
                        await asyncio.sleep(0.5)
                    else:
                        print("⚠️  No messages received in 30s")
                        connected = False
                else:
                    print("❌ Subscription failed")
                    connected = False
            else:
                print(f"❌ Connection failed: {error_msg}")
        
        except asyncio.TimeoutError:
            print("❌ Connection timeout")
            connected = False
        except Exception as e:
            print(f"❌ Connection error: {e}")
            connected = False
        finally:
            await client.stop()
        
        self.results['connection_test'] = {
            'passed': connected,
            'error': error_msg if not connected else None,
        }
        
        return connected
    
    async def test_latency(self) -> bool:
        """Test 2: Measure latencies"""
        print("\n" + "="*70)
        print("TEST 2: Latency Measurement")
        print("="*70)
        print(f"Duration: {self.duration}s")
        print("Measuring Kalshi WebSocket + BRTI Proxy latencies...")
        
        # Kalshi WebSocket latency
        def on_orderbook(data):
            # Measure time from server timestamp to receipt
            if 'timestamp' in data:
                try:
                    server_time = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
                    latency_ms = (datetime.now() - server_time.replace(tzinfo=None)).total_seconds() * 1000
                    self.orderbook_latencies.append(latency_ms)
                except:
                    pass
            
            self.orderbook_count += 1
            
            if self.orderbook_count % 10 == 0:
                print(f"  Orderbook updates: {self.orderbook_count}")
        
        client = KalshiWebSocketClient(on_orderbook=on_orderbook)
        
        # Start client
        client_task = asyncio.create_task(client.start(series="KXBTC15M"))
        
        # BRTI proxy latency
        proxy = BTRIProxyEnhanced(use_volume_weights=True)
        
        async def measure_brti():
            while self.brti_count < self.duration / 2:  # Every 2 seconds
                start = time.time()
                result = proxy.calculate()
                
                if result:
                    latency_ms = (time.time() - start) * 1000
                    self.brti_latencies.append(latency_ms)
                    self.brti_count += 1
                    
                    if self.brti_count % 10 == 0:
                        print(f"  BRTI updates: {self.brti_count}")
                
                await asyncio.sleep(2.0)
        
        brti_task = asyncio.create_task(measure_brti())
        
        # Run for duration
        await asyncio.sleep(self.duration)
        
        # Stop
        await client.stop()
        brti_task.cancel()
        
        try:
            await brti_task
        except asyncio.CancelledError:
            pass
        
        client_task.cancel()
        
        # Analyze results
        print("\n" + "-"*70)
        print("Latency Results:")
        print("-"*70)
        
        success = True
        
        if self.orderbook_latencies:
            avg = statistics.mean(self.orderbook_latencies)
            med = statistics.median(self.orderbook_latencies)
            p95 = statistics.quantiles(self.orderbook_latencies, n=20)[18] if len(self.orderbook_latencies) > 10 else 0
            
            print(f"\nKalshi WebSocket:")
            print(f"  Updates received: {self.orderbook_count}")
            print(f"  Avg latency: {avg:.0f}ms")
            print(f"  Median latency: {med:.0f}ms")
            print(f"  P95 latency: {p95:.0f}ms")
            
            if avg < 1000:
                print(f"  ✅ Latency <1s (target met)")
            else:
                print(f"  ❌ Latency >{avg/1000:.1f}s (target: <1s)")
                success = False
        else:
            print("\nKalshi WebSocket:")
            print("  ❌ No latency measurements (no updates received)")
            success = False
        
        if self.brti_latencies:
            avg = statistics.mean(self.brti_latencies)
            med = statistics.median(self.brti_latencies)
            
            print(f"\nBTRI Proxy:")
            print(f"  Updates calculated: {self.brti_count}")
            print(f"  Avg latency: {avg:.0f}ms")
            print(f"  Median latency: {med:.0f}ms")
            
            if avg < 500:
                print(f"  ✅ Latency <500ms")
            else:
                print(f"  ⚠️  Latency {avg:.0f}ms (high)")
        else:
            print("\nBTRI Proxy:")
            print("  ❌ No measurements")
            success = False
        
        self.results['latency_test'] = {
            'passed': success,
            'kalshi_avg_ms': statistics.mean(self.orderbook_latencies) if self.orderbook_latencies else None,
            'brti_avg_ms': statistics.mean(self.brti_latencies) if self.brti_latencies else None,
        }
        
        return success
    
    async def test_data_quality(self) -> bool:
        """Test 3: Data quality validation"""
        print("\n" + "="*70)
        print("TEST 3: Data Quality")
        print("="*70)
        
        received_data = []
        
        def on_orderbook(data):
            received_data.append(data)
        
        client = KalshiWebSocketClient(on_orderbook=on_orderbook)
        
        # Collect data for 30 seconds
        print("Collecting data for 30 seconds...")
        client_task = asyncio.create_task(client.start(series="KXBTC15M"))
        
        await asyncio.sleep(30)
        
        await client.stop()
        client_task.cancel()
        
        # Analyze data quality
        print("\n" + "-"*70)
        print("Data Quality Results:")
        print("-"*70)
        
        success = True
        
        if received_data:
            print(f"\nMessages received: {len(received_data)}")
            
            # Check for required fields
            required_fields = ['yes_bid', 'yes_ask']
            has_required = all(
                any(field in msg for field in required_fields)
                for msg in received_data
            )
            
            if has_required:
                print("✅ All messages have required fields")
            else:
                print("❌ Some messages missing required fields")
                success = False
            
            # Check for reasonable values
            # (Add more validation as needed)
            
        else:
            print("❌ No data received")
            success = False
        
        self.results['data_quality_test'] = {
            'passed': success,
            'messages_received': len(received_data),
        }
        
        return success
    
    async def run_all_tests(self):
        """Run all tests"""
        print("\n" + "="*70)
        print("WebSocket Infrastructure Test Suite")
        print("="*70)
        print(f"Test duration: {self.duration}s")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Test 1: Connection
        test1_pass = await self.test_connection()
        
        if not test1_pass:
            print("\n❌ Connection test failed - skipping remaining tests")
            self._print_summary()
            return False
        
        # Test 2: Latency
        test2_pass = await self.test_latency()
        
        # Test 3: Data Quality
        test3_pass = await self.test_data_quality()
        
        # Summary
        self._print_summary()
        
        return test1_pass and test2_pass and test3_pass
    
    def _print_summary(self):
        """Print test summary"""
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        
        for test_name, result in self.results.items():
            if result is None:
                status = "⊘ SKIPPED"
            elif result['passed']:
                status = "✅ PASSED"
            else:
                status = "❌ FAILED"
            
            print(f"{test_name:25s}: {status}")
        
        all_passed = all(
            r['passed'] for r in self.results.values() 
            if r is not None
        )
        
        print("="*70)
        
        if all_passed:
            print("✅ ALL TESTS PASSED")
        else:
            print("❌ SOME TESTS FAILED")
        
        print("="*70)


async def main():
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    
    tester = WebSocketTester(duration_seconds=duration)
    
    try:
        await tester.run_all_tests()
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")


if __name__ == "__main__":
    asyncio.run(main())
