# OpenPodcraft

OpenPodcraft is an open-source project that enables users to create podcasts from their textual content. With OpenPodcraft, you can either clone your own voice or use voices from different individuals to generate professional-sounding podcasts.

## Features

- Clone your own voice
- Use voices from other speakers
- Generate transcript using different LLM APIs
- Cross compatible with different OS

## Installation

1. **Install Docker:** 
    - Make sure you have Docker installed on your system (Linux, Windows, or Mac).
    - Linux: https://docs.docker.com/engine/install/ubuntu/
    - Windows: https://docs.docker.com/desktop/setup/install/windows-install/
    - Mac: https://docs.docker.com/desktop/setup/install/mac-install/

2. **Install and run the app** 

    ```sh
    # Clone the repository
    git clone https://github.com/vaishanth-rmrj/open-podcraft.git

    # Navigate to the project directory
    cd open-podcraft

    # Start the Docker container
    docker-compose up -d 

    # Run the application inside the container
    docker exec -it cont-open-podcraft python app.py

## Contribution

Contributions are welcome! Feel free to fork the repository and create pull requests.

## License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details.

