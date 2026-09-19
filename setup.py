from setuptools import setup, find_packages

setup(
    name="codex-cli",
    version="1.6.0",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=["rich>=13.0.0", "groq>=0.4.0", "prompt_toolkit>=3.0.0"],
    entry_points={"console_scripts": ["cdx=codex.main:main", "codex=codex.main:main"]},
)
