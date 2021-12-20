FROM python:latest
RUN mkdir -p /app
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
COPY . .
CMD [ "python", "./main.py" ]
