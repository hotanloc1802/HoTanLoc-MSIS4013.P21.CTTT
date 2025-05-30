# fastapi_model_service/Dockerfile

FROM python:3.11-slim
WORKDIR /code

# Cài đặt các gói hệ thống cần thiết (tùy chọn, nếu một số thư viện Python yêu cầu)
# RUN apt-get update && apt-get install -y --no-install-recommends gcc build-essential && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip

# Bước 1: Cài đặt NumPy phiên bản 1.x trước
# Copy requirements.txt để pip có thể đọc và giải quyết phiên bản numpy nếu nó được ghim ở đó
COPY ./requirements.txt /code/requirements.txt 
RUN pip install --no-cache-dir "numpy~=1.26.4"

# Bước 2: Cài đặt Torch CPU một cách riêng biệt và kiểm tra ngay
# Đảm bảo trong requirements.txt của bạn có torch==2.2.1 (hoặc phiên bản bạn muốn)
# Hoặc bạn có thể ghim trực tiếp ở đây:
RUN pip install --no-cache-dir torch==2.3.0 --extra-index-url https://download.pytorch.org/whl/cpu && \
    python -c "import torch; print(f'Torch version installed during Docker build: {torch.__version__}'); assert hasattr(torch, 'get_default_device'), 'CRITICAL ERROR: Torch installation is missing get_default_device attribute even after explicit install!'"
# Bước 3: Cài đặt các thư viện còn lại từ requirements.txt
# File requirements.txt sẽ được sử dụng lại ở đây. 
# Pip sẽ bỏ qua numpy và torch nếu chúng đã được cài đặt đúng phiên bản ở các bước trên.
RUN pip install \
    --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    --retries 5 \
    --timeout 600 \
    -r /code/requirements.txt

COPY ./app /code/app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
