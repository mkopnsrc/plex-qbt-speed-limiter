FROM python:3
WORKDIR /usr/local/app

# Install the application dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy in the source code
COPY qbt_rate_limiter.py ./

# Setup an app user so the container doesn't run as the root user
RUN useradd app
USER app

#we are expecting the user to config the environment, no need for .env
CMD ["python", "qbt_rate_limiter.py"]
