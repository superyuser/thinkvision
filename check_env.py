from pathlib import Path
from dotenv import load_dotenv
import os

def check_env():
    # Get absolute path to .env file
    env_path = Path('d:/Alldata/Desktop/3March_AGI House_Personal AI/thinkvision/.env').resolve()
    print(f"\nChecking environment setup:")
    print(f"1. Current working directory: {os.getcwd()}")
    print(f"2. Looking for .env at: {env_path}")
    print(f"3. File exists: {env_path.exists()}")

    if env_path.exists():
        print("\nEnvironment file contents:")
        env_contents = env_path.read_text()
        for line in env_contents.splitlines():
            if line and not line.startswith('#'):
                key = line.split('=')[0] if '=' in line else line
                print(f"- {key}")

        # Try to load the environment
        print("\nLoading environment variables...")
        load_dotenv(env_path)
        
        # Check for Google API key
        api_key = os.getenv('GOOGLE_API_KEY')
        if api_key:
            print("✓ GOOGLE_API_KEY found")
            print(f"✓ Key starts with: {api_key[:10]}...")
        else:
            print("✗ GOOGLE_API_KEY not found!")
            
        # Print all loaded environment variables
        print("\nAll loaded environment variables:")
        for key in os.environ:
            if key.endswith('_KEY') or key.endswith('_SECRET'):
                value = '[hidden]'
            else:
                value = os.environ[key]
            print(f"- {key}: {value}")

if __name__ == '__main__':
    check_env()
