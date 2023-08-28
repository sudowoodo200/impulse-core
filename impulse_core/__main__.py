import argparse
import os
import pathlib
import requests

APP_DIR = "~/.impulse_core"
SERVER_DOCKER_COMPOSE_URL = "https://raw.github.com/sudowoodo200/impulse-core/dev/docker-compose.yml"
DOCKER_COMPOSE_FILE_NAME = "docker-compose.yml"

def start():

    ## Check for docker assets
    if os.system("docker --version") != 0:
        raise Exception("Docker runtime not found")
    
    dir = pathlib.Path(APP_DIR).expanduser()
    docker_compose_path = dir / DOCKER_COMPOSE_FILE_NAME
    
    if not docker_compose_path.exists():

        with requests.get(SERVER_DOCKER_COMPOSE_URL, stream=True) as response:
            response.raise_for_status()
            with open(docker_compose_path, 'wb') as output_file:
                for chunk in response.iter_content(chunk_size=8192):
                    output_file.write(chunk)
    
    ## Spin up frontend
    ## TODO

    ## start docker-compose
    os.system(f"docker-compose -f {docker_compose_path} up -d")

def shutdown():

    dir = pathlib.Path(APP_DIR).expanduser()
    docker_compose_path = dir / DOCKER_COMPOSE_FILE_NAME

    if docker_compose_path.exists():
        os.system(f"docker-compose -f {docker_compose_path} down")

def main():
    parser = argparse.ArgumentParser(description='Impulse Server Management')
    parser.add_argument('command', choices=['start', 'shutdown'], help='Command to execute.')

    args = parser.parse_args()

    if args.command == 'start':
        start()
    elif args.command == 'shutdown':
        shutdown()

if __name__ == "__main__":
    main()