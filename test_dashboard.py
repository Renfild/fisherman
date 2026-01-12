"""
Demo script to test the Gaming Dashboard without running the full bot
This simulates fishing activity and demonstrates all dashboard features
"""
import time
import random
import threading
from metrics import FishingMetrics
from sounds import sound_manager
from ui_theme import ACHIEVEMENTS

def simulate_fishing_session(metrics: FishingMetrics, duration: int = 60):
    """Simulate a fishing session with random catches"""
    print("🎣 Starting simulated fishing session...")
    print(f"Duration: {duration} seconds\n")
    
    metrics.start_session()
    
    start_time = time.time()
    catch_count = 0
    attempt_count = 0
    
    while time.time() - start_time < duration:
        # Simulate a fishing attempt every 3-5 seconds
        wait_time = random.uniform(3, 5)
        time.sleep(wait_time)
        
        metrics.start_attempt()
        attempt_count += 1
        
        # Simulate volume changes
        volume = random.randint(1000, 8000)
        metrics.update_volume(volume)
        
        # Simulate audio spectrum
        spectrum = [random.uniform(0, 100) for _ in range(32)]
        metrics.update_audio_spectrum(spectrum)
        
        # 80% success rate
        success = random.random() < 0.8
        
        if success:
            catch_count += 1
            metrics.record_catch(success=True)
            print(f"✅ Catch #{catch_count} - Volume: {volume}")
            
            # Play sound if enabled
            if sound_manager.enabled:
                sound_manager.play_catch_sound()
        else:
            metrics.record_catch(success=False)
            print(f"❌ Missed catch - Volume: {volume}")
            
            if sound_manager.enabled:
                sound_manager.play_error_sound()
        
        # Print progress every 10 seconds
        elapsed = time.time() - start_time
        if int(elapsed) % 10 == 0 and int(elapsed) > 0:
            stats = metrics.get_stats_dict()
            print(f"\n📊 Progress Update ({int(elapsed)}s):")
            print(f"   Fish/hour: {stats['fish_per_hour']:.1f}")
            print(f"   Success rate: {stats['success_rate']:.1f}%")
            print(f"   Mastery: {stats['mastery_title']} ({stats['mastery_exp']} XP)")
            print()
    
    metrics.stop_session()
    
    # Print final stats
    print("\n" + "="*60)
    print("🏆 SESSION COMPLETE")
    print("="*60)
    
    stats = metrics.get_stats_dict()
    
    print(f"\n📈 Final Statistics:")
    print(f"   Total Catches: {stats['total_catches']}")
    print(f"   Total Attempts: {stats['total_attempts']}")
    print(f"   Success Rate: {stats['success_rate']:.1f}%")
    print(f"   Fish per Hour: {stats['fish_per_hour']:.1f}")
    print(f"   Average Catch Time: {stats['average_catch_time']:.2f}s")
    print(f"   Uptime: {stats['uptime']:.0f}s")
    print(f"   Downtime: {stats['downtime']:.0f}s")
    print(f"   Estimated Value: {stats['estimated_value']}")
    
    print(f"\n🎖️  Mastery Progress:")
    print(f"   Level: {stats['mastery_title']}")
    print(f"   Experience: {stats['mastery_exp']} XP")
    print(f"   Progress: {stats['mastery_progress']*100:.1f}%")
    
    # Check achievements
    print(f"\n🏅 Achievements Unlocked:")
    unlocked_count = 0
    for achievement in ACHIEVEMENTS:
        unlocked = False
        
        if achievement['type'] == 'catches':
            unlocked = stats['total_catches'] >= achievement['requirement']
        elif achievement['type'] == 'uptime':
            unlocked = stats['uptime'] >= achievement['requirement']
        elif achievement['type'] == 'value':
            unlocked = stats['estimated_value'] >= achievement['requirement']
        elif achievement['type'] == 'success_rate':
            unlocked = stats['success_rate'] >= achievement['requirement']
        
        if unlocked:
            unlocked_count += 1
            print(f"   {achievement['icon']} {achievement['name']}")
            print(f"      {achievement['description']}")
    
    if unlocked_count == 0:
        print("   No achievements unlocked yet. Keep fishing!")
    
    print(f"\n   Total: {unlocked_count}/{len(ACHIEVEMENTS)}")
    print()


def test_metrics_basic():
    """Test basic metrics functionality"""
    print("="*60)
    print("🧪 TESTING BASIC METRICS")
    print("="*60 + "\n")
    
    m = FishingMetrics()
    
    print("1. Starting session...")
    m.start_session()
    assert m.session_start is not None, "Session should be started"
    print("   ✓ Session started")
    
    print("2. Recording catches...")
    for i in range(5):
        m.start_attempt()
        time.sleep(0.1)
        m.record_catch(success=True)
    print(f"   ✓ Recorded 5 catches")
    
    print("3. Getting statistics...")
    stats = m.get_stats_dict()
    assert stats['total_catches'] == 5, f"Expected 5 catches, got {stats['total_catches']}"
    assert stats['mastery_exp'] == 50, f"Expected 50 XP, got {stats['mastery_exp']}"
    print(f"   ✓ Total catches: {stats['total_catches']}")
    print(f"   ✓ Mastery XP: {stats['mastery_exp']}")
    print(f"   ✓ Success rate: {stats['success_rate']:.1f}%")
    
    print("4. Testing volume tracking...")
    m.update_volume(5000)
    stats = m.get_stats_dict()
    assert stats['current_volume'] == 5000, "Volume should be updated"
    print(f"   ✓ Volume: {stats['current_volume']}")
    
    print("5. Testing audio spectrum...")
    spectrum = [float(i*10) for i in range(32)]
    m.update_audio_spectrum(spectrum)
    stats = m.get_stats_dict()
    assert len(stats['audio_spectrum']) == 32, "Spectrum should have 32 bars"
    print(f"   ✓ Spectrum bars: {len(stats['audio_spectrum'])}")
    
    print("\n✅ All basic tests passed!\n")


def test_mastery_levels():
    """Test mastery level progression"""
    print("="*60)
    print("🎓 TESTING MASTERY LEVELS")
    print("="*60 + "\n")
    
    m = FishingMetrics()
    
    levels = [
        (0, "Новичок", 99),
        (100, "Опытный", 299),
        (300, "Мастер", 699),
        (700, "Легенда", 1000),
    ]
    
    for exp, expected_title, max_exp in levels:
        m.mastery_exp = exp
        m._update_mastery_level()
        stats = m.get_stats_dict()
        
        print(f"XP: {exp:4d} → {stats['mastery_title']:8s} (Progress: {stats['mastery_progress']*100:5.1f}%)")
        assert stats['mastery_title'] == expected_title, f"Expected {expected_title}, got {stats['mastery_title']}"
    
    print("\n✅ Mastery level tests passed!\n")


def test_sounds():
    """Test sound effects"""
    print("="*60)
    print("🔊 TESTING SOUND EFFECTS")
    print("="*60 + "\n")
    
    print(f"Sound manager enabled: {sound_manager.enabled}")
    
    if sound_manager.enabled:
        print("Playing sounds...")
        print("  🎣 Bite sound...")
        sound_manager.play_bite_sound()
        time.sleep(0.5)
        
        print("  🐟 Catch sound...")
        sound_manager.play_catch_sound()
        time.sleep(0.8)
        
        print("  🏆 Achievement sound...")
        sound_manager.play_achievement_sound()
        time.sleep(1.0)
        
        print("  ⬆️  Level up sound...")
        sound_manager.play_level_up_sound()
        time.sleep(1.2)
        
        print("\n✅ Sound tests completed!")
    else:
        print("⚠️  Sound effects are disabled (winsound not available)")
        print("   On Windows, sounds would be enabled automatically")
    
    print()


def main():
    """Main demo function"""
    print("\n" + "="*60)
    print("🎮 FISHERMAN GAMING DASHBOARD - DEMO")
    print("="*60 + "\n")
    
    # Run tests
    test_metrics_basic()
    test_mastery_levels()
    test_sounds()
    
    # Ask user if they want to run simulation
    print("="*60)
    print("Would you like to run a simulated fishing session?")
    print("This will demonstrate the dashboard metrics in action.")
    print("="*60 + "\n")
    
    try:
        response = input("Run simulation? (y/n): ").strip().lower()
        if response == 'y':
            duration = input("Duration in seconds (default 30): ").strip()
            duration = int(duration) if duration else 30
            
            print()
            metrics = FishingMetrics()
            simulate_fishing_session(metrics, duration)
    except (EOFError, KeyboardInterrupt):
        print("\n\nDemo mode - skipping interactive simulation")
        print("Running automated 10-second simulation...\n")
        metrics = FishingMetrics()
        simulate_fishing_session(metrics, 10)
    
    print("="*60)
    print("✅ DEMO COMPLETE")
    print("="*60 + "\n")
    print("To use the dashboard in the actual bot:")
    print("1. Run: python Fisherman.py")
    print("2. Click '🎮 SHOW DASHBOARD' button")
    print("3. Start fishing and watch the metrics update in real-time!")
    print()


if __name__ == "__main__":
    main()
