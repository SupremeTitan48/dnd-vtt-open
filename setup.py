from setuptools import find_packages, setup


setup(
    name="dnd-vtt",
    version="0.1.0",
    description="Open-source modular 2D DND virtual tabletop MVP",
    packages=find_packages(
        include=["api_contracts*", "content*", "desktop*", "engine*", "net*"]
    ),
    install_requires=["pydantic>=2.6", "fastapi>=0.115", "uvicorn>=0.34"],
    extras_require={
        "dev": ["pytest>=8.2", "pytest-cov>=5.0", "ruff>=0.8", "httpx>=0.27"],
    },
    python_requires=">=3.9",
)
