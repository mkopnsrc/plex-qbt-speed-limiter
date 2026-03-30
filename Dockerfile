FROM python:3
WORKDIR /usr/local/app

# Install the application dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy in the source code
COPY plex-qbt-speed-limiter.py ./

#let the program know we are in a container
ENV AM_I_IN_A_CONTAINER=yes

#we are expecting the user to config the environment, no need for .env
CMD ["python", "plex-qbt-speed-limiter.py"]
