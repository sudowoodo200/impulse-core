import os
import pathlib

def run_app():

    ## Check for docker runtime
    if os.system("docker --version") != 0:
        raise Exception("Docker runtime not found")
    
    ## download app from npm
    ## TODO

    ## Turn on docker-compose
    script_dir = pathlib.Path(__file__).parent.absolute()
    docker_compose_path = script_dir / "docker-compose.yml"

    os.system(f"docker-compose -f {docker_compose_path} up -d")

if __name__ == "__main__":
    run_app()