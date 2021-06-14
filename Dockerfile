# Start with python image
FROM python:3.8
MAINTAINER alefeld@alumni.nd.edu

# Add this crontab file
COPY crontab_snackonomy /etc/cron.d/crontab_snackonomy
RUN chmod 0644 /etc/cron.d/crontab_snackonomy

# Install Cron
RUN apt-get update
RUN apt-get -y install cron

# Get the python code runnable
WORKDIR /code
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY ./*.py .

# Run Cron
CMD cron
