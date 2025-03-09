from setuptools import setup, find_packages

setup(
    name="thinkvision",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "python-dotenv",
        "opencv-python",
        "numpy",
        "aiofiles",
        "google-generativeai",
        "pillow"
    ]
)
