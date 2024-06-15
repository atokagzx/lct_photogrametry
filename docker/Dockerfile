FROM ubuntu:22.04

# Timezone Configuration
ENV TZ=Europe/Moscow
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
ENV DEBIAN_FRONTEND=noninteractive

RUN apt update && apt install -y    apt-utils \
                                    lsb-release \
                                    mesa-utils \
                                    gnupg2 \
                                    net-tools \
                                    iputils-ping \
                                    build-essential \
                                    wget \
                                    unzip \
                                    curl \
                                    git \
                                    nano \
                                    ffmpeg \
                                    x11-apps \
                                    libassimp5 \
                                    python3-pip \
                                    python3-dev \
                                    freeglut3-dev && \
    apt clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip3 install --upgrade setuptools pip --no-cache-dir
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt --no-cache-dir
RUN pip3 install --no-cache-dir --no-deps embreex==2.17.7.post4 "pyglet<2" \
    pyembree==0.1.12 

# Install Cesium 3D Tiles Tools
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.1/install.sh | bash && \
    export NVM_DIR="$HOME/.nvm" && \
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh" && \
    [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion" && \
    nvm install 18.17.0 && \
    nvm use 18.17.0 && \
    npm install -g npm@10.8.1 
ENV PATH="${PATH}:/root/.nvm/versions/node/v18.17.0/bin"
RUN npm install -g 3d-tiles-tools

# Add workspace to PYTHONPATH to load lct_solution module
ENV PYTHONPATH "${PYTHONPATH}:/root/workspace"
WORKDIR /root/workspace
ENTRYPOINT ["pipeline/entrypoint.py"]
