#!/usr/bin/env python3
from RPLCD.i2c import CharLCD
import time

# Initialize 20x4 LCD on I2C address 0x27
lcd = CharLCD(i2c_expander='PCF8574', address=0x27, port=1, cols=20, rows=4)

try:
    lcd.clear()
    lcd.cursor_pos = (0, 0)
    lcd.write_string("GeeekPi 2004 LCD")
    lcd.cursor_pos = (1, 0)
    lcd.write_string("I2C Address: 0x27")
    lcd.cursor_pos = (2, 0)
    lcd.write_string("System Status: OK")
    lcd.cursor_pos = (3, 0)
    lcd.write_string("Raspberry Pi Ready")

    print("Success! Display should now show 4 lines of text.")
    time.sleep(10)

except KeyboardInterrupt:
    lcd.clear()
