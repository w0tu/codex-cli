"""Banner & Visual Identity: 24-bit Truecolor Image-to-ANSI Engine.

Directly renders voxel block banners using ANSI 24-bit truecolor half-block characters (▀ and ▄).
Preprocessor downsamples proportionally to terminal width (80-120 cols) and caches ANSI string
to ~/.config/codex_cli/banner.ansi for sub-5ms instant startup.
"""

import os
import sys
import time
import shutil
from pathlib import Path
from typing import Optional

CONFIG_DIR = Path.home() / ".config" / "codex_cli"
CACHE_FILE = CONFIG_DIR / "banner.ansi"
DEFAULT_IMAGE_PATH = Path(__file__).resolve().parent.parent / "assets" / "voxel_banner.png"


def is_pixel_dark(r: int, g: int, b: int, a: int, threshold: int = 20) -> bool:
    """Check if pixel is transparent or near-black background."""
    if a < 32:
        return True
    return r < threshold and g < threshold and b < threshold


def convert_image_to_ansi(image_path: Path | str, target_width: int = 90) -> str:
    """Downsample image proportionally and map vertical pixel pairs to ANSI 24-bit half-blocks."""
    from PIL import Image

    img_path = Path(image_path)
    if not img_path.exists():
        raise FileNotFoundError(f"Voxel banner image not found at: {img_path}")

    with Image.open(img_path) as img:
        img = img.convert("RGBA")
        aspect = img.height / img.width
        # h must be an even number of vertical pixels since each character represents 2 vertical pixels
        calc_h = max(4, int(target_width * aspect))
        if calc_h % 2 != 0:
            calc_h += 1

        resized = img.resize((target_width, calc_h), Image.Resampling.LANCZOS)

        lines: list[str] = []
        for y in range(0, calc_h, 2):
            parts: list[str] = []
            curr_fg: Optional[tuple[int, int, int]] = None
            curr_bg: Optional[tuple[int, int, int]] = None

            for x in range(target_width):
                r1, g1, b1, a1 = resized.getpixel((x, y))
                r2, g2, b2, a2 = resized.getpixel((x, y + 1))

                dark1 = is_pixel_dark(r1, g1, b1, a1)
                dark2 = is_pixel_dark(r2, g2, b2, a2)

                if dark1 and dark2:
                    if curr_fg is not None or curr_bg is not None:
                        parts.append("\033[0m")
                        curr_fg = None
                        curr_bg = None
                    parts.append(" ")
                elif dark1 and not dark2:
                    # Top is empty, bottom is colored -> lower half block ▄
                    if curr_bg is not None:
                        parts.append("\033[49m")
                        curr_bg = None
                    if curr_fg != (r2, g2, b2):
                        parts.append(f"\033[38;2;{r2};{g2};{b2}m")
                        curr_fg = (r2, g2, b2)
                    parts.append("▄")
                elif not dark1 and dark2:
                    # Top is colored, bottom is empty -> upper half block ▀
                    if curr_bg is not None:
                        parts.append("\033[49m")
                        curr_bg = None
                    if curr_fg != (r1, g1, b1):
                        parts.append(f"\033[38;2;{r1};{g1};{b1}m")
                        curr_fg = (r1, g1, b1)
                    parts.append("▀")
                else:
                    # Both are colored -> upper block ▀ with fg=top, bg=bottom
                    if curr_fg != (r1, g1, b1):
                        parts.append(f"\033[38;2;{r1};{g1};{b1}m")
                        curr_fg = (r1, g1, b1)
                    if curr_bg != (r2, g2, b2):
                        parts.append(f"\033[48;2;{r2};{g2};{b2}m")
                        curr_bg = (r2, g2, b2)
                    parts.append("▀")

            parts.append("\033[0m")
            lines.append("".join(parts))

        return "\n".join(lines)


def get_cached_banner(
    image_path: Optional[Path | str] = None,
    width: Optional[int] = None,
    force_rebuild: bool = False,
) -> tuple[str, float]:
    """Retrieve pre-rendered ANSI banner from cache with sub-5ms latency.
    
    Returns:
        (ansi_string, load_time_ms)
    """
    t0 = time.perf_counter()
    img_path = Path(image_path) if image_path else DEFAULT_IMAGE_PATH
    
    term_width = width or shutil.get_terminal_size((120, 24)).columns
    target_width = max(90, min(140, term_width - 2))

    cache_file = CONFIG_DIR / f"banner_{target_width}.ansi"
    cache_meta_file = CONFIG_DIR / f"banner_{target_width}.meta"
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    cache_valid = False
    if not force_rebuild and cache_file.exists() and cache_meta_file.exists():
        try:
            cached_mtime = float(cache_meta_file.read_text(encoding="utf-8").strip())
            img_mtime = img_path.stat().st_mtime if img_path.exists() else 0.0
            if abs(cached_mtime - img_mtime) < 0.01:
                cache_valid = True
        except Exception:
            cache_valid = False

    if cache_valid:
        try:
            content = cache_file.read_text(encoding="utf-8")
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return content, elapsed_ms
        except Exception:
            pass

    # Check nearby cached widths before rebuilding
    if not force_rebuild:
        for nearby in [target_width, 140, 130, 120, 110, 100]:
            nearby_file = CONFIG_DIR / f"banner_{nearby}.ansi"
            if nearby_file.exists() and abs(nearby - target_width) <= 6:
                try:
                    content = nearby_file.read_text(encoding="utf-8")
                    elapsed_ms = (time.perf_counter() - t0) * 1000.0
                    return content, elapsed_ms
                except Exception:
                    pass
                    pass

    # Build cache
    try:
        ansi_output = convert_image_to_ansi(img_path, target_width=target_width)
        cache_file.write_text(ansi_output, encoding="utf-8")
        # Also maintain default CACHE_FILE
        CACHE_FILE.write_text(ansi_output, encoding="utf-8")
        img_mtime = img_path.stat().st_mtime if img_path.exists() else time.time()
        cache_meta_file.write_text(f"{img_mtime}", encoding="utf-8")
    except Exception as e:
        ansi_output = f"[Banner Renderer Warning: {e}]"

    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return ansi_output, elapsed_ms


def render_borderless_block_frame(
    model_label: str = "qwen2.5-coder:1.5b",
    status_text: str = "ONLINE | ZERO-LATENCY PINNED",
    cwd: Optional[str] = None,
) -> str:
    """Render a minimal, borderless block-styled layout using █, ▀, ▄, ▌, ░, ▒, ▓ including live system telemetry."""
    workspace = cwd or os.getcwd()
    user = os.environ.get("USER", "engineer")
    
    # Live System Telemetry
    cpu_str = "N/A"
    ram_str = "N/A"
    try:
        import psutil
        cpu = psutil.cpu_percent(None)
        v = psutil.virtual_memory()
        cpu_str = f"{cpu:.1f}%"
        ram_str = f"{round(v.used / (1024**2))}MB / {round(v.total / (1024**2))}MB ({v.percent:.0f}%)"
    except Exception:
        pass

    import platform
    os_info = f"{platform.system()} {platform.release()}"[:28]

    lines = [
        f"\033[38;2;120;120;130m▌ \033[1;37mCODEX-CLI\033[0m \033[38;2;100;100;110m░▒▓\033[0m \033[38;2;140;140;150mAutonomous Systems Architecture\033[0m",
        f"\033[38;2;120;120;130m▌\033[0m \033[38;2;80;160;255mENGINE:\033[0m {model_label}  \033[38;2;80;200;120mSTATUS:\033[0m {status_text}",
        f"\033[38;2;120;120;130m▌\033[0m \033[38;2;160;160;170mWORKSPACE:\033[0m {workspace}  \033[38;2;160;160;170mUSER:\033[0m {user}",
        f"\033[38;2;120;120;130m▌\033[0m \033[38;2;255;180;50mSYSTEM:\033[0m CPU: {cpu_str} │ RAM: {ram_str} │ OS: {os_info}",
        f"\033[38;2;120;120;130m▌\033[0m \033[38;2;0;243;255mGROQ CONSOLE:\033[0m https://console.groq.com/home (500+ tok/s accelerated)",
        f"\033[38;2;90;90;100m▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀\033[0m",
    ]
    return "\n".join(lines)


def display_welcome_banner(
    model_label: str = "qwen2.5-coder:1.5b",
    status_text: str = "ONLINE | ZERO-LATENCY PINNED",
    cwd: Optional[str] = None,
    clear_screen: bool = True,
) -> float:
    """Clear terminal, then print the colored block banner followed by the system telemetry block layout."""
    if clear_screen:
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()
    banner, load_ms = get_cached_banner()
    sys.stdout.write("\n" + banner + "\n\n")
    sys.stdout.write(render_borderless_block_frame(model_label=model_label, status_text=status_text, cwd=cwd) + "\n\n")
    sys.stdout.flush()
    return load_ms


if __name__ == "__main__":
    banner, ms = get_cached_banner(force_rebuild=True)
    print(f"Cache generated. Rebuild time: {ms:.2f} ms")
    banner_cached, ms2 = get_cached_banner()
    print(banner_cached)
    print(f"Cached load time: {ms2:.3f} ms (Target: < 5.000 ms)")
