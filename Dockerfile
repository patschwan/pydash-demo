FROM python:3.8-slim
LABEL maintainer="info@pschwan.de"

# working dir in the container
WORKDIR /code
# copy dependencies to workdir
COPY requirements.txt /
RUN pip install -r /requirements.txt

# copy local src dir to the workdir
COPY src/ ./

EXPOSE 8050

# command run on container start
CMD ["python", "./app.py"]

# recommended Django setup for security reasons
# RUN adduser -D user
# USER user
