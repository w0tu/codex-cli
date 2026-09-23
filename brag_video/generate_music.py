import numpy as np
import wave
import struct

sample_rate = 44100
duration = 30.0
total_samples = int(sample_rate * duration)
t = np.linspace(0, duration, total_samples, endpoint=False)

left = np.zeros(total_samples)
right = np.zeros(total_samples)

def add_tone(freq, start, dur, amp=0.2, wave_type='sine'):
    idx_start = int(start * sample_rate)
    idx_end = min(total_samples, int((start + dur) * sample_rate))
    n = idx_end - idx_start
    if n <= 0: return
    local_t = np.linspace(0, dur, n, endpoint=False)
    
    if wave_type == 'sine':
        sig = np.sin(2 * np.pi * freq * local_t)
    elif wave_type == 'saw':
        sig = 2 * (local_t * freq - np.floor(local_t * freq + 0.5))
    elif wave_type == 'square':
        sig = np.sign(np.sin(2 * np.pi * freq * local_t))
    
    # Envelope
    env = np.ones(n)
    attack = min(n // 4, int(0.02 * sample_rate))
    decay = min(n // 2, int(0.08 * sample_rate))
    if attack > 0: env[:attack] = np.linspace(0, 1, attack)
    if decay > 0: env[-decay:] = np.linspace(1, 0, decay)
    sig *= env * amp
    
    left[idx_start:idx_end] += sig
    right[idx_start:idx_end] += sig

def add_noise(start, dur, amp=0.1):
    idx_start = int(start * sample_rate)
    idx_end = min(total_samples, int((start + dur) * sample_rate))
    n = idx_end - idx_start
    if n <= 0: return
    noise = (np.random.rand(n) * 2 - 1) * amp
    env = np.linspace(1, 0, n) ** 2
    left[idx_start:idx_end] += noise * env
    right[idx_start:idx_end] += noise * env

# 1. 0:00 - 0:11 Intro Ambient Drone
intro_mask = t < 11.0
left[intro_mask] += 0.08 * np.sin(2 * np.pi * 65.4 * t[intro_mask]) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.5 * t[intro_mask]))
right[intro_mask] += 0.08 * np.sin(2 * np.pi * 130.8 * t[intro_mask]) * (0.8 + 0.2 * np.cos(2 * np.pi * 0.5 * t[intro_mask]))

# Keyboard clatter during 0:00 - 0:08
np.random.seed(42)
for _ in range(35):
    click_t = np.random.uniform(0.5, 8.5)
    add_noise(click_t, np.random.uniform(0.015, 0.04), amp=np.random.uniform(0.04, 0.08))

# Riser whoosh 0:08.5 - 0:11.0
riser_start = 8.5
riser_dur = 2.5
r_idx_start = int(riser_start * sample_rate)
r_idx_end = int(11.0 * sample_rate)
rn = r_idx_end - r_idx_start
rt = np.linspace(0, 1, rn)
freq_sweep = 120 + 760 * (rt ** 2.2)
riser_sig = 0.12 * np.sin(2 * np.pi * freq_sweep * rt) * (rt ** 1.8)
riser_noise = (np.random.rand(rn) * 2 - 1) * 0.08 * (rt ** 2)
left[r_idx_start:r_idx_end] += (riser_sig + riser_noise) * 0.9
right[r_idx_start:r_idx_end] += (riser_sig + riser_noise) * 1.1

# Bass Drop at 11.0s
drop_start = 11.0
drop_dur = 1.2
d_idx_start = int(drop_start * sample_rate)
d_idx_end = min(total_samples, int((drop_start + drop_dur) * sample_rate))
dn = d_idx_end - d_idx_start
dt = np.linspace(0, drop_dur, dn)
drop_freq = 90 * np.exp(-dt * 3.5) + 38
drop_sig = 0.35 * np.sin(2 * np.pi * drop_freq * dt) * np.exp(-dt * 2.8)
left[d_idx_start:d_idx_end] += drop_sig
right[d_idx_start:d_idx_end] += drop_sig
add_noise(11.0, 0.3, amp=0.18)

# 128 BPM electronic beat from 11.0s to 26.0s
beat_len = 60.0 / 128.0  # ~0.46875s
chords = [
    [220.00, 261.63, 329.63], # Am
    [174.61, 220.00, 261.63], # F
    [130.81, 164.81, 196.00], # C
    [196.00, 246.94, 293.66], # G
]

beat_idx = 0
cur_t = 11.0
while cur_t < 26.0:
    # Kick on beats 0, 2 (downbeats)
    if beat_idx % 2 == 0:
        k_dur = 0.25
        k_idx = int(cur_t * sample_rate)
        kn = min(total_samples - k_idx, int(k_dur * sample_rate))
        if kn > 0:
            kt = np.linspace(0, k_dur, kn)
            k_freq = 130 * np.exp(-kt * 18) + 45
            k_sig = 0.28 * np.sin(2 * np.pi * k_freq * kt) * np.exp(-kt * 12)
            left[k_idx:k_idx+kn] += k_sig
            right[k_idx:k_idx+kn] += k_sig

    # Snare / Clap on beats 1, 3
    if beat_idx % 2 == 1:
        add_noise(cur_t, 0.18, amp=0.15)
        add_tone(220, cur_t, 0.08, amp=0.08, wave_type='sine')

    # Hi-hats every half beat
    add_noise(cur_t, 0.03, amp=0.06)
    add_noise(cur_t + beat_len / 2, 0.025, amp=0.05)

    # Chords
    chord = chords[(beat_idx // 4) % len(chords)]
    for note in chord:
        add_tone(note, cur_t, beat_len * 0.9, amp=0.045, wave_type='saw')
        add_tone(note * 2, cur_t, beat_len * 0.9, amp=0.025, wave_type='sine')

    cur_t += beat_len
    beat_idx += 1

# Ending Chord Resolve 25.5s - 30.0s (C Major add9 sparkling resolve)
end_notes = [261.63, 329.63, 392.00, 493.88, 587.33, 783.99]
for i, n in enumerate(end_notes):
    add_tone(n, 25.8 + i * 0.08, 3.8 - i * 0.08, amp=0.05, wave_type='sine')

# Master Limiter / Normalize
max_val = max(np.max(np.abs(left)), np.max(np.abs(right)), 0.001)
if max_val > 0.9:
    left = (left / max_val) * 0.88
    right = (right / max_val) * 0.88

# Export to WAV
with wave.open('brag_video/bg_music.wav', 'w') as wf:
    wf.setnchannels(2)
    wf.setsampwidth(2)
    wf.setframerate(sample_rate)
    
    interleaved = np.empty((total_samples * 2,), dtype=np.int16)
    interleaved[0::2] = (np.clip(left, -1.0, 1.0) * 32767).astype(np.int16)
    interleaved[1::2] = (np.clip(right, -1.0, 1.0) * 32767).astype(np.int16)
    wf.writeframes(interleaved.tobytes())

print("Successfully generated brag_video/bg_music.wav")
