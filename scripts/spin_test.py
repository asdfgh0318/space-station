#!/usr/bin/env python3
"""Simple motor spin test — no web GUI, just direct GPIO.
Run on RPi: python3 spin_test.py
"""
import lgpio
import time
import sys

# Waveshare HAT (B) pin mapping
MOTORS = {
    1: {"step": 19, "dir": 13, "enable": 12, "name": "AZ"},
    2: {"step": 18, "dir": 24, "enable": 4,  "name": "EL"},
}

def spin(motor_num=1, steps=200, delay_ms=5, direction="cw"):
    m = MOTORS[motor_num]
    h = lgpio.gpiochip_open(0)
    lgpio.gpio_claim_output(h, m["step"], 0)
    lgpio.gpio_claim_output(h, m["dir"], 0)
    lgpio.gpio_claim_output(h, m["enable"], 0)

    # Enable motor
    lgpio.gpio_write(h, m["enable"], 0)
    # Set direction
    lgpio.gpio_write(h, m["dir"], 1 if direction == "cw" else 0)
    time.sleep(0.01)

    # Step
    delay = delay_ms / 1000.0
    t0 = time.time()
    for i in range(steps):
        lgpio.gpio_write(h, m["step"], 1)
        time.sleep(0.000005)
        lgpio.gpio_write(h, m["step"], 0)
        time.sleep(delay)
    elapsed = time.time() - t0

    # Disable motor
    lgpio.gpio_write(h, m["enable"], 1)
    lgpio.gpiochip_close(h)
    print(f"Motor {m['name']}: {steps} steps {direction} in {elapsed:.1f}s ({int(steps/elapsed)} steps/s)")

def back_and_forth(motor_num=1, steps=800, delay_ms=5, pause=0.5, cycles=3):
    print(f"Back-and-forth test: motor {motor_num}, {steps} steps, {delay_ms}ms delay, {cycles} cycles")
    for i in range(cycles):
        print(f"  Cycle {i+1}/{cycles} — CW")
        spin(motor_num, steps, delay_ms, "cw")
        time.sleep(pause)
        print(f"  Cycle {i+1}/{cycles} — CCW")
        spin(motor_num, steps, delay_ms, "ccw")
        time.sleep(pause)
    print("Done!")

def disable_all():
    h = lgpio.gpiochip_open(0)
    for pin in [12, 4]:
        lgpio.gpio_claim_output(h, pin, 1)
        lgpio.gpio_write(h, pin, 1)
    lgpio.gpiochip_close(h)
    print("All motors disabled")

if __name__ == "__main__":
    motor = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    steps = int(sys.argv[2]) if len(sys.argv) > 2 else 800
    delay = float(sys.argv[3]) if len(sys.argv) > 3 else 5

    print(f"=== SPIN TEST: Motor {motor}, {steps} steps, {delay}ms delay ===")
    try:
        back_and_forth(motor, steps, delay)
    except KeyboardInterrupt:
        print("\nInterrupted!")
        disable_all()
