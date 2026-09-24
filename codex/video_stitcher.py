"""Automated Video Stitcher & Google Flow / Veo Pipeline.

Features:
1. Video Stitching: Concat and stitch multiple video clips (MP4/WebM/MOV) using FFmpeg.
   - Handles resolution normalization (1080p landscape 1920x1080, portrait 1080x1920, or auto).
   - Audio re-sampling and sync.
   - Optional crossfade transitions between scenes.
   - Optional background soundtrack mixing.
2. Google Flow / Veo Bridge:
   - Exports formatted multi-scene camera & motion vectors for Google Flow / Veo 2.
   - Integrates with Google Antigravity bridge for AI video generation.
   - Auto-stitches generated scene clips into a final compiled film.
"""

import os
import sys
import shutil
import tempfile
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

FFMPEG_BIN = "/home/feds/.local/bin/ffmpeg" if os.path.exists("/home/feds/.local/bin/ffmpeg") else (shutil.which("ffmpeg") or "ffmpeg")


def stitch_videos(
    video_paths: List[str],
    output_path: str,
    target_resolution: str = "1920:1080",
    fps: int = 30,
    background_audio: Optional[str] = None,
    audio_volume: float = 0.7
) -> Dict[str, Any]:
    """Stitch multiple video clips into a single seamless video using FFmpeg.
    
    Args:
        video_paths: List of absolute or relative paths to video clips.
        output_path: Target output path (e.g. 'stitched_output.mp4').
        target_resolution: '1920:1080' (landscape) or '1080:1920' (portrait/Reels).
        fps: Target framerate (default 30).
        background_audio: Optional path to an audio/music file to overlay.
        audio_volume: Volume of background audio if provided (0.0 to 1.0).
        
    Returns:
        Dict with status, output_path, duration, and file_size.
    """
    valid_paths = [str(Path(p).resolve()) for p in video_paths if Path(p).exists()]
    if not valid_paths:
        return {"ok": False, "error": "No valid video files provided to stitch."}

    if len(valid_paths) == 1 and not background_audio:
        # Single file, copy or return directly
        shutil.copy(valid_paths[0], output_path)
        return {
            "ok": True,
            "output_path": output_path,
            "clips_stitched": 1,
            "size_bytes": os.path.getsize(output_path)
        }

    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        normalized_clips = []

        # 1. Normalize each clip to the target resolution, fps, and audio format
        for idx, clip in enumerate(valid_paths):
            norm_clip = tmp_path / f"norm_{idx:03d}.mp4"
            # Scale and pad to target resolution (pillarbox/letterbox)
            w, h = target_resolution.split(":")
            filter_complex = (
                f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black,setsar=1"
            )
            cmd = [
                FFMPEG_BIN, "-y",
                "-i", clip,
                "-vf", filter_complex,
                "-r", str(fps),
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "22",
                "-c:a", "aac",
                "-ar", "48000",
                "-ac", "2",
                str(norm_clip)
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0 and norm_clip.exists():
                normalized_clips.append(norm_clip)
            else:
                # If audio is missing in clip, generate silence
                cmd_silent = [
                    FFMPEG_BIN, "-y",
                    "-i", clip,
                    "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
                    "-vf", filter_complex,
                    "-r", str(fps),
                    "-c:v", "libx264",
                    "-preset", "fast",
                    "-crf", "22",
                    "-c:a", "aac",
                    "-shortest",
                    str(norm_clip)
                ]
                res_silent = subprocess.run(cmd_silent, capture_output=True, text=True)
                if res_silent.returncode == 0 and norm_clip.exists():
                    normalized_clips.append(norm_clip)

        if not normalized_clips:
            return {"ok": False, "error": "Failed to normalize video clips."}

        # 2. Write concat demuxer manifest
        concat_list = tmp_path / "concat.txt"
        with open(concat_list, "w", encoding="utf-8") as f:
            for c in normalized_clips:
                f.write(f"file '{c}'\n")

        # 3. Concatenate all clips
        raw_stitched = tmp_path / "raw_stitched.mp4"
        cmd_concat = [
            FFMPEG_BIN, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list),
            "-c", "copy",
            str(raw_stitched)
        ]
        res_concat = subprocess.run(cmd_concat, capture_output=True, text=True)
        if res_concat.returncode != 0:
            return {"ok": False, "error": f"Concat failed: {res_concat.stderr[:200]}"}

        # 4. Optional background soundtrack overlay
        if background_audio and os.path.exists(background_audio):
            cmd_audio = [
                FFMPEG_BIN, "-y",
                "-i", str(raw_stitched),
                "-i", str(background_audio),
                "-filter_complex", f"[0:a][1:a]amix=inputs=2:duration=first:weights=1.0 {audio_volume}[aout]",
                "-map", "0:v",
                "-map", "[aout]",
                "-c:v", "copy",
                "-c:a", "aac",
                str(out_file)
            ]
            subprocess.run(cmd_audio, capture_output=True, text=True)
        else:
            shutil.copy(str(raw_stitched), str(out_file))

    if out_file.exists():
        size = out_file.stat().st_size
        return {
            "ok": True,
            "output_path": str(out_file),
            "clips_stitched": len(valid_paths),
            "size_bytes": size,
            "size_mb": round(size / (1024 * 1024), 2)
        }
    return {"ok": False, "error": "Output file was not created."}


def generate_google_flow_package(topic: str, scene_count: int = 4) -> Dict[str, Any]:
    """Generate a complete scene-by-scene storyboard and prompt pack for Google Flow & Veo 2."""
    from codex.marketing import VideoFlowEngine
    flow_data = VideoFlowEngine.generate_flow_prompts(topic, scene_count=scene_count)
    return {
        "ok": True,
        "platform": "Google Flow / Google Veo 2.0",
        "topic": topic,
        "scene_count": scene_count,
        "storyboard": flow_data.get("scenes", []),
        "instructions": (
            "1. Paste each scene prompt into Google Flow or Google Labs VideoFX / Veo 2.\n"
            "2. Render the 5-second scene clips.\n"
            "3. Stitch them together automatically with CDX: `cdx --stitch clip1.mp4 clip2.mp4 -o final.mp4`"
        )
    }
