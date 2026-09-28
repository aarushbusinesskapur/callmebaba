import re

with open('github_scanner.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Remove the force connection message
code = code.replace('send_telegram_alert("I\'M CONNECTED!")\n', '')

# Update timeframes logic
old_tf = '''    # Determine target timeframes
    tfs_to_scan = []
    if 10 <= minute <= 20 or 40 <= minute <= 50: tfs_to_scan.append('15m')
    elif 25 <= minute <= 35: tfs_to_scan.extend(['15m', '30m'])
    elif 55 <= minute <= 59 or 0 <= minute <= 5:
        tfs_to_scan.extend(['15m', '30m', '1h'])
        if hour % 4 == 0: tfs_to_scan.append('4h')
            
    if not tfs_to_scan:
        print(f"Time {now.strftime('%H:%M')} UTC does not align with close. Exiting.")
        sys.exit(0)'''

new_tf = '''    # Determine target timeframes
    tfs_to_scan = ['5m']
    if 10 <= minute <= 22 or 40 <= minute <= 52: tfs_to_scan.append('15m')
    elif 25 <= minute <= 37: tfs_to_scan.extend(['15m', '30m'])
    elif 55 <= minute <= 59 or 0 <= minute <= 7:
        tfs_to_scan.extend(['15m', '30m', '1h'])
        if hour % 4 == 0: tfs_to_scan.append('4h')'''

code = code.replace(old_tf, new_tf)

# Update HTF logic
code = code.replace("htf_df = df_1h if tf in ['15m', '30m'] else df_1d", "htf_df = df_1h if tf in ['5m', '15m', '30m'] else df_1d")
code = code.replace("trend_type = \\"1H\\" if tf in ['15m', '30m'] else \\"1D\\"", "trend_type = \\"1H\\" if tf in ['5m', '15m', '30m'] else \\"1D\\"")

with open('github_scanner.py', 'w', encoding='utf-8') as f:
    f.write(code)

with open('.github/workflows/scanner.yml', 'r', encoding='utf-8') as f:
    yaml_code = f.read()

yaml_code = yaml_code.replace("cron: '*/15 * * * *'", "cron: '*/5 * * * *'")

with open('.github/workflows/scanner.yml', 'w', encoding='utf-8') as f:
    f.write(yaml_code)

print("Modifications done!")
