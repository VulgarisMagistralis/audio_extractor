"""Audio Extractor - Download audio at the highest quality from any URL."""

__version__ = "0.1.0"
from dotenv import load_dotenv
from .cli import create_parser, run_headless
from .gui import run_gui


def main():
    """Entry point for the audio-extractor command."""
    load_dotenv()
    parser = create_parser()
    args = parser.parse_args()

    if args.ui or args.url is None:
        run_gui()
    else:
        run_headless(
            url=args.url,
            output_dir=args.output,
            fmt=args.format,
            quality=args.quality,
            no_playlist=args.no_playlist,
        )

__all__ = ["main", "run_gui", "run_headless", "__version__"]
