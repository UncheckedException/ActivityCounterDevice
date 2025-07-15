from machine import Pin, I2C, RTC
import ssd1306, time, os
from ds3231 import DS3231

# ------------OLED Setup--------------------------------------------
i2cOled = I2C(1, scl=Pin(7), sda=Pin(6))
oled = ssd1306.SSD1306_I2C(128, 64, i2cOled)
WIDTH, HEIGHT = 128, 64
LINE_HEIGHT = 11  # Pixels height per row
MAX_VISIBLE = 5

# ── Buttons ─────────────────────────────────────────────────
btn_nav = Pin(15, Pin.IN, Pin.PULL_DOWN)  # cycle activities
btn_log = Pin(14, Pin.IN, Pin.PULL_DOWN)  # log press

# -------DS2321 Setup-----------------------------------------''
i2cClock = I2C(0, scl = Pin(10), sda = Pin(12))
rtc = DS3231(i2cClock)

# ----------LOG_FILE---------------------------------------------
LOG_FILE = "activity_data.csv"

# ------------ACTIVITIES---------------------------------------------
activities = ["A", "B", "C", "D", "E", "F"]
counts_today = [0] * len(activities)

# -------------Display State---------------------------------------
# State
current = 0  # index of selected activity
offset = 0  # scroll window start index

# def time_str():
#     t = RTC.
#     return "{:02d}:{:02d}:{:02d}".format(t[3], t[4], t[5])
#rtc = RTC()

def date_str():
    t = time.localtime()
    return "{:02d}:{:02d}:{:02d},{}".format(t[2], t[1], t[0] % 100, ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][t[6]])


def create_logfile_if_not_exists():
    """Creates the log file with headers if it doesn't exist."""
    if LOG_FILE not in os.listdir():
        with open(LOG_FILE, "w") as f:
            f.write("Activity,Timestamp\n")
        print(f"[INFO] Created log file: {LOG_FILE}")
    else:
        print(f"[INFO] Log file already exists: {LOG_FILE}")


def log_activity(activity: str):
    """Appends activity and current DS3231 epoch time to the log file."""
    timestamp = date_str()
    with open(LOG_FILE, "a") as f:
        f.write(f"{activity},{timestamp}\n")
    print(f"[LOG] {activity} at {timestamp}")


def draw_screen():
    oled.fill(0)

    # Draw centered clock
    clk = date_str()
    x = (WIDTH - len(clk) * 8) // 2
    oled.text(clk, x, 0)

    # Draw activity list slice
    for i in range(MAX_VISIBLE):
        activity_index = offset + i
        if activity_index >= len(activities):
            break
        y = LINE_HEIGHT * (i + 1)
        name = activities[activity_index][:10]
        count = str(counts_today[activity_index])
        if activity_index == current:
            oled.fill_rect(0, y, WIDTH, LINE_HEIGHT, 1)
            oled.text(name, 0, y, 0)
            oled.text(count, WIDTH - len(count) * 8, y, 0)
        else:
            oled.text(name, 0, y, 1)
            oled.text(count, WIDTH - len(count) * 8, y, 1)

    oled.show()


# ── Input Handling ───────────────────────────────
def scroll_activity():
    global current, offset
    current = (current + 1) % len(activities)
    if current >= offset + MAX_VISIBLE:
        offset = current - MAX_VISIBLE + 1
    elif current < offset:
        offset = current
    draw_screen()


def increment_count():
    counts_today[current] += 1
    draw_screen()


def handle_long_press_history():
    hist = {}
    try:
        with open(LOG_FILE) as f:
            next(f)  # skip header
            for line in f:
                ts, act = line.strip().split(",")
                if act == activities[current]:
                    day = ts.split()[0]
                    hist[day] = hist.get(day, 0) + 1
    except Exception as e:
        hist = {}

    # Get last 3 days (oldest to newest)
    days = []
    for i in range(2, -1, -1):
        t = time.localtime(time.time() - i * 86400)
        days.append("%04d-%02d-%02d" % t[:3])

    # Display on OLED
    oled.fill(0)
    oled.text("History:", 0, 0)

    # Activity name (trimmed if needed)
    act_name = activities[current][:16]  # 16 chars max in one line
    oled.text(act_name, 0, 10)

    # Daily counts (start from line 3)
    for i, d in enumerate(days):
        cnt = str(hist.get(d, 0))
        oled.text(f"{d[-5:]}: {cnt}", 0, 22 + i * 12)  # show MM-DD format

    oled.show()
    time.sleep(2.5)
    draw_screen()


def save_counts():
    pass


def main():
    create_logfile_if_not_exists()
    draw_screen()

    hold_start_nav = None
    hold_start_log = None
    nav_hold_handled = False
    log_hold_handled = False

    last_nav = 0
    last_log = 0

    while True:
        nav = btn_nav.value()
        log = btn_log.value()

        # ──────────────── NAVIGATION (Scroll) ────────────────
        if nav == 1 and log == 0:
            if hold_start_nav is None:
                hold_start_nav = time.ticks_ms()
            elif time.ticks_diff(time.ticks_ms(), hold_start_nav) > 2000 and not nav_hold_handled:
                handle_long_press_history()
                nav_hold_handled = True
                hold_start_nav = None
        elif nav == 0 and last_nav == 1:
            if hold_start_nav is not None and not nav_hold_handled:
                scroll_activity()
                draw_screen()
            hold_start_nav = None
            nav_hold_handled = False

        # ──────────────── LOGGING / RESET ────────────────
        if log == 1 and nav == 0:
            if hold_start_log is None:
                hold_start_log = time.ticks_ms()
            elif time.ticks_diff(time.ticks_ms(), hold_start_log) > 2000 and not log_hold_handled:
                # RESET COUNTER
                counts_today[current] = 0
                save_counts()  # Optional: if you're persisting counts
                draw_screen()
                log_hold_handled = True
                hold_start_log = None
        elif log == 0 and last_log == 1:
            if hold_start_log is not None and not log_hold_handled:
                # SHORT PRESS: INCREMENT
                increment_count()
                draw_screen()
            hold_start_log = None
            log_hold_handled = False

        # Update previous states
        last_nav = nav
        last_log = log


main()
