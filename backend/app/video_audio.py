"""Bounded local audio decoding and music/voice composition."""
import json
import math
import tempfile
import wave
from pathlib import Path
from fastapi import HTTPException
from .video_render import command

MAX_AUDIO_BYTES = 20 * 1024 * 1024
PRESETS = {
    'elegant-piano': ('Elegant Piano', 'Gentle arpeggios for a polished product showcase.'),
    'bright-strings': ('Bright Strings', 'Light, lively strings for an upbeat advertisement.'),
    'warm-acoustic': ('Warm Acoustic', 'Soft classical guitar for a friendly feel.'),
    'grand-showcase': ('Grand Showcase', 'Full chords and strings for a confident reveal.'),
    'calm-classical': ('Calm Classical', 'Slow, delicate notes for a relaxed presentation.'),
}
MUSIC_ROOT = Path(__file__).parent.parent / 'assets/music'

def normalize(data, label, max_seconds):
    if not data or len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(422, f'{label}: choose an audio file smaller than 20 MB.')
    # Force a real audio-container demuxer; never accept playlists or URLs as uploads.
    container = ('wav' if data[:4]==b'RIFF' and data[8:12]==b'WAVE' else
                 'mp3' if data[:3]==b'ID3' or len(data)>1 and data[0]==255 and data[1]&224==224 else
                 'mov' if data[4:8]==b'ftyp' else 'ogg' if data[:4]==b'OggS' else
                 'matroska' if data[:4]==b'\x1aE\xdf\xa3' else None)
    if not container:
        raise HTTPException(422, f'{label}: choose MP3, WAV, M4A, OGG or WebM audio.')
    with tempfile.TemporaryDirectory(prefix='postready-audio-') as directory:
        source = Path(directory) / 'upload'
        output = Path(directory) / 'audio.wav'
        source.write_bytes(data)
        try:
            info = json.loads(command(['ffprobe', '-v', 'error', '-f', container, '-protocol_whitelist', 'file,pipe',
                                      '-show_streams', '-show_format', '-of', 'json', str(source)], 20))
            audio = [s for s in info['streams'] if s['codec_type'] == 'audio']
            duration = float(info['format']['duration'])
            if not audio or not math.isfinite(duration) or duration < 0.1:
                raise ValueError()
            if duration > max_seconds + 0.05:
                message = ('Choose a longer video or upload a shorter voice clip.' if label == 'Voice'
                           else 'Choose music up to 60 seconds long.')
                raise HTTPException(422, f'{label} is too long. {message}')
            command(['ffmpeg', '-v', 'error', '-y', '-f', container, '-protocol_whitelist', 'file,pipe', '-i', str(source),
                     '-map', '0:a:0', '-vn', '-t', str(max_seconds + 0.1), '-ac', '1', '-ar', '32000',
                     '-af', 'loudnorm=I=-18:TP=-2:LRA=7', '-c:a', 'pcm_s16le', str(output)], 30)
            with wave.open(str(output),'rb') as decoded:
                actual=decoded.getnframes()/decoded.getframerate()
            if actual<0.1 or actual>max_seconds+0.05:
                raise HTTPException(422, f'{label} does not fit. Choose a shorter audio clip or a longer video.')
            return output.read_bytes()
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(422, f'{label}: could not read this audio. Choose MP3, WAV, M4A, OGG or WebM.')

def compose(video, duration, directory, music=None, voice=None):
    if not music and not voice:
        return video
    root = Path(directory)
    source = root / 'silent.mp4'
    source.write_bytes(video)
    args = ['ffmpeg', '-v', 'error', '-y', '-threads', '1', '-filter_complex_threads', '1', '-i', str(source)]
    filters = []
    next_input = 1
    if music:
        path = root / 'music.wav'; path.write_bytes(music)
        args += ['-stream_loop', '-1', '-i', str(path)]
        filters.append(f'[{next_input}:a]atrim=duration={duration},asetpts=PTS-STARTPTS,volume=0.45,afade=t=in:d=0.2,afade=t=out:st={duration-0.5}:d=0.5[music]')
        next_input += 1
    if voice:
        path = root / 'voice.wav'; path.write_bytes(voice)
        args += ['-i', str(path)]
        filters.append(f'[{next_input}:a]apad,atrim=duration={duration},asetpts=PTS-STARTPTS[voice]')
    if music and voice:
        filters += ['[voice]asplit=2[speech][trigger]',
                    '[music][trigger]sidechaincompress=threshold=0.015:ratio=10:attack=20:release=300[ducked]',
                    '[ducked][speech]amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.95:level=0[audio]']
    else:
        filters.append(f'[{"music" if music else "voice"}]alimiter=limit=0.95:level=0[audio]')
    output = root / 'with-audio.mp4'
    args += ['-filter_complex', ';'.join(filters), '-map', '0:v:0', '-map', '[audio]', '-c:v', 'copy',
             '-c:a', 'aac', '-b:a', '128k', '-ar', '48000', '-t', str(duration), '-movflags', '+faststart', str(output)]
    command(args)
    info = json.loads(command(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(output)], 20))
    if not any(s['codec_type'] == 'audio' and s['codec_name'] == 'aac' for s in info['streams']) or abs(float(info['format']['duration'])-duration)>0.15:
        raise RuntimeError('Audio output validation failed.')
    return output.read_bytes()
