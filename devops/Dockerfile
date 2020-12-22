FROM python:3.9

# install basic apps & utils, including man; but first need to re-enable man pages installation
RUN sed -i 's:^path-exclude=/usr/share/man:#path-exclude=/usr/share/man:' \
        /etc/dpkg/dpkg.cfg.d/excludes \
 && apt update \
 && apt install -y software-properties-common \
 && add-apt-repository -y ppa:deadsnakes/ppa \
 && DEBIAN_FRONTEND=noninteractive apt install -y \
    man \
    manpages-posix \
    bash-completion \
    ca-certificates \
    curl \
    git \
    jq \
    net-tools \
    python3.9 \
    unzip \
    wget \
    vim \
    zip \
    make

# Terraform 0.14
ARG VER_TERRAFORM4=0.14.2
RUN wget -nv https://releases.hashicorp.com/terraform/${VER_TERRAFORM4}/terraform_${VER_TERRAFORM4}_linux_amd64.zip \
 && unzip terraform_${VER_TERRAFORM4}_linux_amd64.zip \
 && mv terraform /usr/local/bin/terraform014 \
 && chmod +x /usr/local/bin/terraform014 \
 && terraform014 --version \
 && rm terraform_${VER_TERRAFORM4}_linux_amd64.zip

# Sops
ARG VER_SOPS=3.6.1
RUN wget -nv https://github.com/mozilla/sops/releases/download/v${VER_SOPS}/sops_${VER_SOPS}_amd64.deb \
 && dpkg -i sops_${VER_SOPS}_amd64.deb \
 && sops --version \
 && rm sops_${VER_SOPS}_amd64.deb

ARG VER_AWS=2.0.61
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64-${VER_AWS}.zip" -o "awscliv2.zip" \
 && unzip awscliv2.zip \
 && ./aws/install \
 && rm -fr ./aws

# install python3 pip and some packages used by our scripts:
RUN apt update \
 && apt -y install python3.9-distutils \
 && wget https://bootstrap.pypa.io/get-pip.py \
 && python3.9 get-pip.py \
 && rm get-pip.py \
 && pip3 install dictdiffer~=0.8 \
 && pip3 install pyyaml~=5.3 \
 && pip3 install click~=7.1 \
 && pip3 install pytest~=5.3 \
 && pip3 install boto3~=1.16 \
 && pip3 install requests~=2.24 \
 && pip3 install python-magic~=0.4

# install yq for processing yaml files
ARG VER_YQ=3.4.1
RUN wget -nv https://github.com/mikefarah/yq/releases/download/${VER_YQ}/yq_linux_amd64 \
 && chmod a+x yq_linux_amd64 \
 && mv yq_linux_amd64 /usr/local/bin/yq

# terraformer:
ARG TFMER_VERSION=0.8.10
RUN curl -LO https://github.com/GoogleCloudPlatform/terraformer/releases/download/${TFMER_VERSION}/terraformer-aws-linux-amd64 \
 && chmod +x terraformer-aws-linux-amd64 \
 && mv terraformer-aws-linux-amd64 /usr/local/bin/terraformer


# Save shell history so that returning to shell can use last session commands
# Setup env and user
ENV PATH=$TOOL_PATH:$PATH
ENV TERM=xterm-256color
ENV EDITOR=vi
ENV LANG=C.UTF-8

# Create user and other dirs
RUN chmod a+w $TOOL_PATH \
 && useradd -ms /bin/bash tooluser

# ######################################################################################
USER tooluser

RUN mkdir -p ~/.devopstool/ssh \
 && chmod a+rxw ~/.devopstool/ssh \
 && chmod go-rxw ~/.devopstool/ssh \
 && ln -s ~/.devopstool/ssh ~/.ssh


# ######################################################################################
USER root

# Deployment tool
COPY image ./

RUN cp bashrc /root/.bashrc \
 && cp bashrc /home/tooluser/.bashrc \
 && chown tooluser /home/tooluser/.bashrc \
 && chgrp tooluser /home/tooluser/.bashrc \
 && cp -r templates/aws /home/tooluser/.devopstool/aws \
 && chown -R tooluser /home/tooluser/.devopstool/aws

RUN cd /deployment-tool/templates \
 && terraform init \
 && mkdir -p ~tooluser/.terraform.d/plugins \
 && cp -r .terraform/providers/registry.terraform.io/hashicorp/aws/*/linux_amd64 ~tooluser/.terraform.d/plugins/linux_amd64 \
 && chown -R tooluser ~tooluser/.terraform.d \
 && rm -r .terraform*

# ######################################################################################
# Run everything else as regular user
USER tooluser

ENV HISTFILE=/home/tooluser/.devopstool/bash_history
ENV AWS_CONFIG_FILE=/home/tooluser/.devopstool/aws/config
ENV AWS_SHARED_CREDENTIALS_FILE=/home/tooluser/.devopstool/aws/credentials

# these have to be defined at end for some reason, otherwise layers after them get rebuilt every time!
ARG DEVOPS_TOOL_IMAGE_TAG=unknown_version
ARG DEVOPS_TOOL_BUILD_DATE=unknown_build_date
ENV DEVOPS_TOOL_IMAGE_TAG=${DEVOPS_TOOL_IMAGE_TAG}
ENV DEVOPS_TOOL_BUILD_DATE=${DEVOPS_TOOL_BUILD_DATE}

