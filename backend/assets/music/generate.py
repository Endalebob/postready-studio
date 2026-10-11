"""Reproducible original instrumental miniatures; standard library only.

No sampled recordings or third-party melodies. Source and recordings: MIT.
These are synthesized piano/string/guitar styles rather than live performances.
"""
import math
import struct
import wave
from pathlib import Path

RATE, LENGTH = 22050, 16
ROOT = Path(__file__).parent

def note(track, midi, start, length, gain, instrument):
    frequency = 440 * 2 ** ((midi - 69) / 12)
    for i in range(int(length * RATE)):
        index = int(start * RATE) + i
        if index >= len(track):
            break
        t = i / RATE
        release = min(1, (length-t)/0.18)
        if instrument == 'strings':
            envelope = min(1,t/0.18) * release
            tone = sum(math.sin(2*math.pi*frequency*h*t+0.025*math.sin(2*math.pi*5*t))/h**1.8 for h in range(1,6))
            tone += 0.18*math.sin(2*math.pi*frequency*1.003*t)
        else:
            envelope = min(1,t/0.008)*math.exp(-t*(2.6 if instrument=='guitar' else 1.7))*release
            tone = sum(math.sin(2*math.pi*frequency*h*t)/h**(2.2 if instrument=='guitar' else 2) for h in range(1,7))
        track[index] += gain * envelope * tone

def build(name, chords, melody, instrument, step, grand=False):
    track = [0.0] * (RATE * LENGTH)
    for bar, chord in enumerate(chords):
        start = bar*4
        for j,pitch in enumerate(chord):
            note(track,pitch-12,start+j*0.03,3.8,0.11,'strings' if grand else instrument)
        for beat in range(int(4/step)):
            pitch = melody[(bar*int(4/step)+beat)%len(melody)]
            note(track,pitch,start+beat*step,step+0.5,0.2,instrument)
            if grand:
                note(track,pitch-12,start+beat*step,step+0.2,0.08,'piano')
    peak = max(abs(x) for x in track)
    samples=[]
    for i,value in enumerate(track):
        t=i/RATE
        fade=min(1,t/0.12,(LENGTH-t)/0.4)
        samples.append(int(value/max(peak,0.01)*0.65*fade*32767))
    with wave.open(str(ROOT/(name+'.wav')),'wb') as output:
        output.setnchannels(1); output.setsampwidth(2); output.setframerate(RATE)
        output.writeframes(struct.pack('<'+'h'*len(samples),*samples))

if __name__=='__main__':
    major=[[60,64,67],[57,60,64],[53,57,60],[55,59,62]]
    build('elegant-piano',major,[72,76,79,76,74,72,69,72], 'piano',0.5)
    build('bright-strings',[[62,66,69],[59,62,66],[55,59,62],[57,61,64]],[74,78,81,83,81,78,76,74],'strings',0.5)
    build('warm-acoustic',major,[64,67,72,67,60,64,69,64],'guitar',0.5)
    build('grand-showcase',[[55,59,62],[52,55,59],[48,52,55],[50,54,57]],[79,78,74,71,72,74,78,79],'strings',1,True)
    build('calm-classical',[[57,60,64],[53,57,60],[60,64,67],[55,59,62]],[76,72,69,72,74,71,67,71],'piano',1)
