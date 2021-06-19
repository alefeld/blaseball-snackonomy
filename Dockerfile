# Start with python image
FROM python:3.8
MAINTAINER alefeld@alumni.nd.edu

# Add this crontab file
COPY crontab_snackonomy /etc/cron.d/crontab_snackonomy
RUN chmod 0644 /etc/cron.d/crontab_snackonomy
RUN touch /var/log/cron.log

# Install Cron
RUN apt-get update
RUN apt-get -y install cron

# Get the python code runnable
WORKDIR /code
COPY requirements.txt .
RUN pip3 install -r requirements.txt
COPY ./*.py .
COPY ./run_all.sh .
COPY ./run_waiter.sh .
RUN chmod 0744 run_all.sh
RUN chmod 0744 run_waiter.sh

# Run Cron
CMD cron && tail -f /var/log/cron.log

# Run waiter
CMD ["root","/code/run_waiter.sh"]
