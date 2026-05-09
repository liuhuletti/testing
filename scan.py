import sounddevice as sd
import numpy as np

print("Skannaa laitteet - puhu mikrofoniin koko ajan...")
for i in range(40):
    try:
        info = sd.query_devices(i)
        if info['max_input_channels'] > 0:
            d = sd.rec(16000, samplerate=16000, channels=1, device=i, dtype='float32')
            sd.wait()
            level = np.max(np.abs(d))
            if level > 0.001:
                print('Device', i, info['name'][:40], 'TASO:', round(level, 4))
    except Exception as e:
        pass

print('Valmis')
