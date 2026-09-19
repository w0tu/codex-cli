"""Top-level banner renderer interface importing from codex.banner_renderer."""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from codex.banner_renderer import (
    convert_image_to_ansi,
    get_cached_banner,
    render_borderless_block_frame,
    display_welcome_banner,
    CONFIG_DIR,
    CACHE_FILE,
    DEFAULT_IMAGE_PATH,
)

if __name__ == "__main__":
    banner, ms = get_cached_banner(force_rebuild=True)
    print(f"Generated cache in {ms:.2f} ms")
    banner_cached, ms2 = get_cached_banner()
    print(banner_cached)
    print(f"Cached load time: {ms2:.3f} ms")
