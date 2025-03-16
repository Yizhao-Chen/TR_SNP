# 使用官方的 Miniconda 基础镜像
FROM continuumio/miniconda3

# 设置工作目录
WORKDIR /app

# 复制环境文件和脚本到工作目录
COPY environment.yml /app/environment.yml
COPY . /app

# 使用国内源加速 APT 包安装
RUN sed -i 's|http://archive.ubuntu.com/ubuntu/|http://mirrors.aliyun.com/ubuntu/|g' /etc/apt/sources.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends && \
    apt-get install -y vim \
    build-essential \
    wget \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 创建 Conda 环境并激活
RUN conda env create -f environment.yml
RUN echo "source activate tr_env" > ~/.bashrc
ENV PATH /opt/conda/envs/tr_env/bin:$PATH


# 运行脚本
CMD ["python", "TR_SNP.py"]
