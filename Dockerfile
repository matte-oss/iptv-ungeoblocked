FROM python:3.10-slim-bullseye

WORKDIR /app

RUN apt-get update && apt-get install -y git

RUN git clone https://github.com/matte-oss/Ahrrr.git .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 7860
CMD ["uvicorn", "run:main_app", "--host", "0.0.0.0", "--port", "7860", "--workers", "4"]
