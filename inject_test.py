import sys

with open('github_scanner.py', 'r', encoding='utf-8') as f:
    code = f.read()

old_block = '''    state = load_state()
    
    # ONE-TIME PING IF STATE IS COMPLETELY EMPTY (First Run)'''

new_block = '''    state = load_state()
    
    if not state.get("TEST_SIGNAL_SENT_PEPE"):
        test_msg = "<b>?? TIER A (5m) SIGNAL [TEST RUN] ??</b>\\n\\n"
        test_msg += "<b>Asset:</b> PEPE/USD\\n<b>Direction:</b> LONG\\n<b>Entry:</b> $0.00001050\\n"
        test_msg += "<b>SL:</b> $0.00000980\\n<b>TP1-4:</b> $0.00001100 | $0.00001150 | $0.00001200 | $0.00001250\\n\\n"
        test_msg += "<b>Motive:</b> 5m Squeeze Breakout with 1H Trend Alignment\\n"
        test_msg += "<b>Live Chart Conf:</b> 1H > $0.00000900 | ADX: 35.2\\n\\n"
        test_msg += "<i>[Untested Asset]: No historical backtest data for PEPE/USD. Trade with caution.</i>"
        send_telegram_alert(test_msg)
        state["TEST_SIGNAL_SENT_PEPE"] = True
        save_state(state)
        
    # ONE-TIME PING IF STATE IS COMPLETELY EMPTY (First Run)'''

code = code.replace(old_block, new_block)

with open('github_scanner.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Test signal injected!")
