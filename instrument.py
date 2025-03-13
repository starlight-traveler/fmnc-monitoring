#!/usr/bin/env python3

# It mostly works

import json
import subprocess
import time
import os
import shutil
import logging
from datetime import datetime

def setup_logging(log_file_path):
    """
    Set up a logger that writes to both a file and the console.
    """
    logger = logging.getLogger("capture_logger")
    logger.setLevel(logging.INFO)
    logger.propagate = False  # To prevent duplicate logs if root logger is used

    # File handler
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging.INFO)
    file_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_format)

    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

def load_config(config_file='capture_config.json'):
    """
    Loads configuration from a JSON file
      - interface            (monitor-mode interface)
      - use_band             (bool)
      - band                 (str) 'a', 'bg', 'abg', etc.
      - channel_hop_time     (int) dwell time per channel in seconds
      - duration             (int or str) how long to run capture in seconds,
                             or 'infinite' for no time limit
      - output_prefix        (str) filename prefix for output
      - min_free_space_mb    (int) required free space in MB
      - use_gpsd             (bool) if True, airodump will use gpsd
      - output_formats       (list of str) which output formats to generate
      - space_check_interval (int) how often to check disk space if 'infinite'
    """
    with open(config_file, 'r') as f:
        cfg = json.load(f)

    # Provide defaults if something is missing:
    cfg.setdefault('interface', 'mon0')
    cfg.setdefault('use_band', False)
    cfg.setdefault('band', 'a')
    cfg.setdefault('channel_hop_time', 2)
    cfg.setdefault('duration', 10)  # can be an integer or the string 'infinite'
    cfg.setdefault('output_prefix', 'testcapture')
    cfg.setdefault('min_free_space_mb', 100)  # default: 100 MB
    cfg.setdefault('use_gpsd', False)
    # default output formats (airodump-ng recognizes csv, netxml, pcap, logcsv)
    cfg.setdefault('output_formats', ['pcap', 'csv', 'netxml'])
    # how often we check for free space when running infinitely
    cfg.setdefault('space_check_interval', 30)  # seconds

    return cfg

def check_disk_space(required_mb, path='.'):
    """
    Checks if there is enough disk space (in MB) at the given path.
    Returns True if enough space is available, False otherwise.
    """
    usage = shutil.disk_usage(path)
    free_mb = usage.free / (1024 * 1024)  # bytes to MB
    return free_mb >= required_mb

def generate_folder_name(prefix):
    """
    Generate a new folder name using a prefix and timestamp.
    Example:  prefix_2025-03-07_12-34-56
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return f"{prefix}_{timestamp}"

def create_output_folder(folder_name):
    """
    Create a folder if it doesn't already exist.
    """
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

def run_airodump(logger, interface, output_prefix, folder_name,
                 channel_hop_time=5,
                 duration=15,   # can be an integer or 'infinite'
                 use_band=False, band='a',
                 use_gpsd=False,
                 output_formats=None,
                 min_free_space_mb=100,
                 space_check_interval=30):
    """
    Runs airodump-ng as a subprocess because I am not using the API:
      - interface: monitor-mode interface
      - output_prefix: base filename for output
      - folder_name: folder where output files are to be stored
      - channel_hop_time: dwell time per channel (seconds)
      - duration: total run time in seconds or 'infinite' for indefinite
      - use_band: True/False
      - band: which band(s) to use, e.g. 'a', 'bg'
      - use_gpsd: if True, pass --gpsd to airodump-ng
      - output_formats: list of output formats (e.g. ['netxml','pcap','csv'])
      - min_free_space_mb: if free space dips below this, terminate capture
      - space_check_interval: how often to check disk space if running indefinitely

    Produces files in folder_name named <output_prefix>-01.[csv|cap|netxml], etc.
    """
    # Build the full path for the filename prefix
    full_output_prefix = os.path.join(folder_name, output_prefix)

    # Construct the base command
    cmd = [
        'airodump-ng',
        interface,
        '-f', str(channel_hop_time),
        '-w', full_output_prefix
    ]

    # Add user-requested output formats (comma-separated)
    if output_formats and isinstance(output_formats, list):
        fmt_string = ','.join(output_formats)
        cmd.extend(['--output-format', fmt_string])

    # If user wants to specify a band
    if use_band and band:
        cmd.extend(['--band', band])

    # If GPSD usage is requested
    if use_gpsd:
        cmd.append('--gpsd')

    logger.info("[+] Starting airodump-ng with the following command:")
    logger.info("    " + " ".join(cmd))

    # Start the airodump-ng process
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    try:
        if duration == "infinite":
            # Run indefinitely until we run out of space or user kills the script
            logger.info("[+] Running indefinitely. Will check disk space every "
                        f"{space_check_interval} seconds.")
            while True:
                time.sleep(space_check_interval)
                if not check_disk_space(min_free_space_mb, folder_name):
                    logger.warning("[!] Insufficient disk space. Stopping capture...")
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        logger.warning("[!] Forcing kill on airodump-ng...")
                        process.kill()
                    break
        else:
            # Convert duration to int if user provided it as a string (not 'infinite')
            duration_int = int(duration)
            time.sleep(duration_int)

    except KeyboardInterrupt:
        logger.info("[!] Keyboard interrupt received. Stopping airodump-ng...")

    # Terminate if still running
    if process.poll() is None:
        logger.info(f"[+] Stopping airodump-ng after duration={duration} ...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logger.warning("[!] Forcing kill on airodump-ng...")
            process.kill()

    logger.info("[+] Airodump-ng stopped.")

def main():
    # 1) Load our configuration
    config = load_config('utility_config.json')

    interface = config['interface']
    output_prefix = config['output_prefix']
    channel_hop_time = config['channel_hop_time']
    duration = config['duration']       # can be an integer or 'infinite'
    use_band = config['use_band']
    band = config['band']
    min_free_space_mb = config['min_free_space_mb']
    use_gpsd = config['use_gpsd']
    output_formats = config['output_formats']
    space_check_interval = config['space_check_interval']

    # 2) Create a new folder for each capture run
    folder_name = generate_folder_name("capture_output")
    create_output_folder(folder_name)

    # 2a) Set up logging to a file in that folder (and also console)
    log_file_path = os.path.join(folder_name, "capture.log")
    logger = setup_logging(log_file_path)

    logger.info(f"[+] Capture session starting. Logging to {log_file_path}")
    logger.info(f"[+] Checking disk space requirements ({min_free_space_mb} MB).")

    # 3) Check if there is enough disk space before starting
    if not check_disk_space(min_free_space_mb, folder_name):
        logger.error(f"[!] Not enough disk space. Need at least {min_free_space_mb} MB free.")
        return
    else:
        logger.info(f"[+] There is enough free disk space (>= {min_free_space_mb} MB).")

    # 4) Run airodump-ng with parameters from the config
    run_airodump(
        logger=logger,
        interface=interface,
        output_prefix=output_prefix,
        folder_name=folder_name,
        channel_hop_time=channel_hop_time,
        duration=duration,
        use_band=use_band,
        band=band,
        use_gpsd=use_gpsd,
        output_formats=output_formats,
        min_free_space_mb=min_free_space_mb,
        space_check_interval=space_check_interval
    )

    logger.info(f"[+] Capture complete. Files saved in folder: {folder_name}")

if __name__ == '__main__':
    main()